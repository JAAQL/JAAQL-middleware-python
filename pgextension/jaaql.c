#include "postgres.h"
#include "access/xact.h"
#include "catalog/pg_authid.h"
#include "miscadmin.h"
#include "tcop/utility.h"
#include "utils/builtins.h"
#include "utils/syscache.h"
#include "utils/memutils.h"
#include "utils/guc.h"
#include "utils/guc_tables.h"

PG_MODULE_MAGIC;

void _PG_init(void);
void _PG_fini(void);

static ProcessUtility_hook_type prev_utility_hook = NULL;

static struct config_string *session_authorization_guc = NULL;
static GucStringCheckHook prev_session_authorization_check_hook = NULL;
static GucStringAssignHook prev_session_authorization_assign_hook = NULL;

static char *reset_session_uuid = NULL;
static char *super_user_name = "postgres";
static char *cur_username = NULL;

static bool
restrict_session_authorization_check(char **newval, void **extra, GucSource source)
{
    if (reset_session_uuid != NULL)
    {
        GUC_check_errcode(ERRCODE_INSUFFICIENT_PRIVILEGE);
        GUC_check_errmsg("\"session_authorization\" blocked by jaaql plugin");
        GUC_check_errhint("You are not allowed to change the session authorization in this state. Please call jaaql__reset_session_authorization with the correct password to reset!");
        return false;
    }
    if (prev_session_authorization_check_hook) {
        return (*prev_session_authorization_check_hook) (newval, extra, source);
    }
    return true;
}

static void
restrict_session_authorization_assign(const char *newval, void *extra)
{
    if (reset_session_uuid != NULL) {
        return;
    }
    if (prev_session_authorization_assign_hook) {
        (*prev_session_authorization_assign_hook) (newval, extra);
    }
}

static void
restore_locked_user_on_abort(XactEvent event, void *arg)
{
    Oid current_user_id;
    int sec_context;

    if (event != XACT_EVENT_ABORT || reset_session_uuid == NULL) {
        return;
    }
    GetUserIdAndSecContext(&current_user_id, &sec_context);
    SetUserIdAndSecContext(GetOuterUserId(), sec_context);
}

static void restrict_commands(PlannedStmt *pstmt,
                                       const char *queryString, bool readOnlyTree,
                                       ProcessUtilityContext context,
                                       ParamListInfo params,
                                       QueryEnvironment *queryEnv,
                                       DestReceiver *dest, QueryCompletion *qc);


static void
restrict_commands(PlannedStmt *pstmt,
                           const char *queryString,
                           bool readOnlyTree,
                           ProcessUtilityContext context,
                           ParamListInfo params,
                           QueryEnvironment *queryEnv,
                           DestReceiver *dest,
                           QueryCompletion *qc)
{
    MemoryContext prevContext = NULL;
    prevContext = MemoryContextSwitchTo(TopMemoryContext);

    switch (nodeTag(((Node *) pstmt->utilityStmt)))
    {
        case T_VariableSetStmt:
        {
            if (!((VariableSetStmt *) ((Node *) pstmt->utilityStmt))->name) {
                break;
            }
            if (strcmp(((VariableSetStmt *) ((Node *) pstmt->utilityStmt))->name, "session_authorization") == 0 && reset_session_uuid != NULL)
            {
                MemoryContextSwitchTo(prevContext);
                ereport(ERROR,
                        (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                         errmsg("\"SET/RESET SESSION AUTHORIZATION\" blocked by jaaql plugin"),
                         errhint("You are not allowed to use this command in this state. Please call jaaql__reset_session_authorization with the correct password to reset!")));
            }
            break;
        }
        case T_DiscardStmt:
        {
            if (((DiscardStmt *) ((Node *) pstmt->utilityStmt))->target == DISCARD_ALL && reset_session_uuid != NULL)
            {
                MemoryContextSwitchTo(prevContext);
                ereport(ERROR,
                        (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                         errmsg("\"DISCARD ALL\" blocked by jaaql plugin"),
                         errhint("You are not allowed to use this command in this state. Please call jaaql__reset_session_authorization with the correct password to reset!")));
            }
            break;
        }
        case T_CreateExtensionStmt:
        {
            if (cur_username != NULL && strcmp(cur_username, super_user_name) != 0) {
                MemoryContextSwitchTo(prevContext);
                ereport(ERROR,
                        (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                         errmsg("Extension management blocked by jaaql plugin"),
                         errhint("You are not allowed to use this command!")));
            }
            break;
        }
        case T_AlterExtensionStmt:
        {
            if (cur_username != NULL && strcmp(cur_username, super_user_name) != 0) {
                MemoryContextSwitchTo(prevContext);
                ereport(ERROR,
                        (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                         errmsg("Extension management blocked by jaaql plugin"),
                         errhint("You are not allowed to use this command!")));
            }
            break;
        }
        case T_AlterExtensionContentsStmt:
        {
            if (cur_username != NULL && strcmp(cur_username, super_user_name) != 0) {
                MemoryContextSwitchTo(prevContext);
                ereport(ERROR,
                        (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                         errmsg("Extension management blocked by jaaql plugin"),
                         errhint("You are not allowed to use this command!")));
            }
            break;
        }
        case T_DropStmt:
        {
            if (((DropStmt *) (((Node *) pstmt->utilityStmt)))->removeType == OBJECT_EXTENSION) {
                if (cur_username != NULL && strcmp(cur_username, super_user_name) != 0) {
                    MemoryContextSwitchTo(prevContext);
                    ereport(ERROR,
                            (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                             errmsg("Extension management blocked by jaaql plugin"),
                             errhint("You are not allowed to use this command!")));
                }
            }
            break;
        }
        default:
            break;
    }

    MemoryContextSwitchTo(prevContext);
    if (prev_utility_hook) {
        (*prev_utility_hook) (pstmt, queryString, readOnlyTree, context, params, queryEnv, dest, qc);
    } else {
        standard_ProcessUtility(pstmt, queryString, readOnlyTree, context, params, queryEnv, dest, qc);
    }
}

PG_FUNCTION_INFO_V1(jaaql__reset_session_authorization);
Datum
jaaql__reset_session_authorization(PG_FUNCTION_ARGS)
{
    int do_error = 0;
    MemoryContext prevContext = NULL;
    char *supplied_reset_session_uuid;

    prevContext = MemoryContextSwitchTo(TopMemoryContext);
    if (reset_session_uuid == NULL)
    {
        MemoryContextSwitchTo(prevContext);
        ereport(ERROR,
                (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                 errmsg("Invalid state when calling jaaql__reset_session_authorization"),
                 errhint("You are not allowed to use this function when state is not set!")));
    }

    supplied_reset_session_uuid = text_to_cstring(PG_GETARG_TEXT_PP(0));
    if (strcmp(reset_session_uuid, supplied_reset_session_uuid) != 0) {
        elog(NOTICE, "Did not match escape password");
        do_error = 1;
    }

    if (do_error) {
        MemoryContextSwitchTo(prevContext);
        ereport(ERROR,
                (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                 errmsg("Invalid reset code"),
                 errhint("You have not supplied the valid reset code!")));
    }
    pfree(reset_session_uuid);
    reset_session_uuid = NULL;
    pfree(cur_username);
    cur_username = NULL;
    MemoryContextSwitchTo(prevContext);

    SetSessionAuthorization(GetAuthenticatedUserId(), false);

    PG_RETURN_TEXT_P(cstring_to_text("OK"));
}

PG_FUNCTION_INFO_V1(jaaql__set_session_authorization);
Datum
jaaql__set_session_authorization(PG_FUNCTION_ARGS)
{
    HeapTuple roleTup;
    Form_pg_authid rform;
    MemoryContext prevContext = NULL;
    char *newRole;

    if (reset_session_uuid != NULL)
    {
        ereport(ERROR,
                (errcode(ERRCODE_INSUFFICIENT_PRIVILEGE),
                 errmsg("Invalid state when calling jaaql__set_session_authorization"),
                 errhint("You are not allowed to use this function when state is already set!")));
    }
    newRole = text_to_cstring(PG_GETARG_TEXT_PP(0));

    roleTup = SearchSysCache1(AUTHNAME, PointerGetDatum(newRole));
    if (!HeapTupleIsValid(roleTup)) {
        elog(ERROR, "role \"%s\" does not exist", newRole);
    }

    rform = (Form_pg_authid) GETSTRUCT(roleTup);
    SetSessionAuthorization(rform->oid, true);
    prevContext = MemoryContextSwitchTo(TopMemoryContext);
    reset_session_uuid = pstrdup(text_to_cstring(PG_GETARG_TEXT_PP(1)));
    cur_username = pstrdup(newRole);
    MemoryContextSwitchTo(prevContext);
    ReleaseSysCache(roleTup);

    PG_RETURN_TEXT_P(cstring_to_text("OK"));
}

void
_PG_init(void)
{
    prev_utility_hook = ProcessUtility_hook;
    ProcessUtility_hook = restrict_commands;

    session_authorization_guc = (struct config_string *) find_option("session_authorization", false, false, ERROR);
    if (session_authorization_guc->gen.vartype != PGC_STRING) {
        elog(ERROR, "jaaql plugin expected \"session_authorization\" to be a string parameter");
    }
    prev_session_authorization_check_hook = session_authorization_guc->check_hook;
    prev_session_authorization_assign_hook = session_authorization_guc->assign_hook;
    session_authorization_guc->check_hook = restrict_session_authorization_check;
    session_authorization_guc->assign_hook = restrict_session_authorization_assign;

    RegisterXactCallback(restore_locked_user_on_abort, NULL);
}

void
_PG_fini(void)
{
    ProcessUtility_hook = prev_utility_hook;
    if (session_authorization_guc != NULL) {
        session_authorization_guc->check_hook = prev_session_authorization_check_hook;
        session_authorization_guc->assign_hook = prev_session_authorization_assign_hook;
    }
    UnregisterXactCallback(restore_locked_user_on_abort, NULL);
}

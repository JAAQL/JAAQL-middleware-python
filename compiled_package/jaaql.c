#include "postgres.h"
#include "catalog/pg_authid.h"
#include "miscadmin.h"
#include "tcop/utility.h"
#include "utils/builtins.h"
#include "utils/syscache.h"
#include "utils/memutils.h"

PG_MODULE_MAGIC;

void _PG_init(void);
void _PG_fini(void);

static ProcessUtility_hook_type prev_utility_hook = NULL;

static char *reset_session_uuid = NULL;
static char *super_user_name = "postgres";
static char *cur_username = NULL;

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
}

void
_PG_fini(void)
{
    ProcessUtility_hook = prev_utility_hook;
}

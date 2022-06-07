import * as JEQL from "../../../../../JEQL/JEQL.js"

let APPLICATION_NAME = "manager";
let ID_CONF_APP = "configuration-table";
let ID_PARAMETER_APP = "parameter-table";
let ID_APPLICATION_LIST = "application-list";
let ID_NODE_LIST = "node-list";
let ID_EMAIL_ACCOUNT_LIST = "email-account-list";
let ID_ADD_NODE = "add-node";
let ID_ADD_EMAIL_ACCOUNT = "add-email-account";
let ID_ADD_NODE_NAME = "add-node-name";
let ID_ADD_NODE_ADDRESS = "add-node-address";
let ID_ADD_NODE_PORT = "add-node-port";
let ID_ADD_NODE_DESCRIPTION = "add-node-description";
let ID_ADD_APP_CONFIG = "add-app-config";
let ID_ADD_APP_CONFIG_APP = "add-app-config-app";
let ID_ADD_APP_CONFIG_NAME = "add-app-config-name";
let ID_ADD_APP_CONFIG_DESCRIPTION = "add-app-config-description";
let ID_ADD_APP_PARAMETER = "add-app-parameter";
let ID_ADD_APP_PARAMETER_APP = "add-app-parameter-app";
let ID_ADD_APP_PARAMETER_NAME = "add-app-parameter-name";
let ID_ADD_APP_PARAMETER_DESCRIPTION = "add-app-parameter-description";
let ID_ADD_APP = "add-application";
let ID_ADD_APP_NAME = "add-application-name";
let ID_ADD_APP_DESCRIPTION = "add-application-description";
let ID_ADD_APP_URL = "add-application-url";
let ID_ADD_PUBLIC_USERNAME = "add-application-public-username";
let ID_TABLE_ASSIGNED_DATABASES = "assigned-databases";
let ID_TABLE_AUTHS = "conf-auths";
let ID_TABLE_DATABASES = "node-databases";
let ID_TABLE_EMAIL_TEMPLATES = "email-templates";
let ID_TABLE_NODE_AUTHS = "node-auths";
let ID_ADD_NODE_DATABASE = "add-node-database";
let ID_ADD_EMAIL_TEMPLATE = "add-email-template";
let ID_ADD_NODE_DATABASE_NODE = "add-node-database-node";
let ID_ADD_NODE_DATABASE_NAME = "add-node-database-name";
let ID_ADD_NODE_DATABASE_CREATE = "add-node-database-create";
let ID_ADD_NODE_AUTH = "add-node-auth";
let ID_ADD_NODE_AUTH_NODE = "add-node-auth-node";
let ID_ADD_NODE_AUTH_ROLE = "add-node-auth-role";
let ID_ADD_NODE_AUTH_PRECEDENCE = "add-node-auth-precedence";
let ID_ADD_NODE_AUTH_USERNAME = "add-node-auth-username";
let ID_ADD_NODE_AUTH_PASSWORD = "add-node-auth-password";
let ID_ADD_ARG = "add-arg";
let ID_ADD_ARG_APP = "add-app-arg";
let ID_ADD_ARG_CONF = "add-app-conf";
let ID_ADD_ARG_PARAM = "add-app-param";
let ID_ADD_ARG_NODE = "add-app-node";
let ID_ADD_ARG_DATABASE = "add-app-database";
let ID_ADD_AUTH = "add-auth";
let ID_ADD_AUTH_APP = "add-auth-app";
let ID_ADD_AUTH_CONF = "add-auth-conf";
let ID_ADD_AUTH_ROLE = "add-auth-role";
let ID_ADD_EMAIL_TEMPLATE_NAME = "add-email-template-name";
let ID_ADD_EMAIL_TEMPLATE_ACCOUNT = "add-email-template-account";
let ID_ADD_EMAIL_TEMPLATE_DESCRIPTION = "add-email-template-description";
let ID_ADD_EMAIL_TEMPLATE_APP_RELATIVE_PATH = "add-email-template-app-relative-path";
let ID_ADD_EMAIL_TEMPLATE_SUBJECT = "add-email-template-subject";
let ID_ADD_EMAIL_TEMPLATE_ALLOW_SIGNUP = "add-email-template-allow-signup";
let ID_ADD_EMAIL_TEMPLATE_ALLOW_ALREADY_EXISTS = "add-email-template-allow-already-exists";
let ID_ADD_EMAIL_TEMPLATE_DATA_VALIDATION_TABLE = "add-email-template-data-validation-table";
let ID_ADD_EMAIL_TEMPLATE_DATA_VALIDATION_VIEW = "add-email-template-data-validation-view";
let ID_ADD_EMAIL_TEMPLATE_RECIPIENT_VALIDATION_VIEW = "add-email-template-recipient-validation-view";
let ID_ADD_EMAIL_ACCOUNT_NAME = "add-email-account-name";
let ID_ADD_EMAIL_ACCOUNT_SEND_NAME = "add-email-account-send-name";
let ID_ADD_EMAIL_ACCOUNT_HOST = "add-email-account-host";
let ID_ADD_EMAIL_ACCOUNT_PORT = "add-email-account-port";
let ID_ADD_EMAIL_ACCOUNT_USERNAME = "add-email-account-username";
let ID_ADD_EMAIL_ACCOUNT_PASSWORD = "add-email-account-password";

function renderAddAuth(modal, appName, config) {
    modal.buildHTML(`
        <h1>Add Config Auth</h1>
        <label>Application: <input id="${ID_ADD_AUTH_APP}" disabled/></label><br>
        <label>Configuration: <input id="${ID_ADD_AUTH_CONF}" disabled/></label><br>
        <label>Role: <input id="${ID_ADD_AUTH_ROLE}"/></label><br>
    `).buildChild("button").buildText("Add Auth").buildEventListener("click", function() {
        let data = {};
        data[JEQL.KEY_APPLICATION] = document.getElementById(ID_ADD_AUTH_APP).value;
        data[JEQL.KEY_CONFIGURATION] = document.getElementById(ID_ADD_AUTH_CONF).value;
        data[JEQL.KEY_ROLE] = document.getElementById(ID_ADD_AUTH_ROLE).value;
        JEQL.requests.makeJson(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_CONFIG_AUTH_ADD, function() {
            JEQL.renderModalOk("Successfully added configuration authorization", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_AUTHS).click();
            });
        }, data);
    });
    document.getElementById(ID_ADD_AUTH_APP).value = appName;
    document.getElementById(ID_ADD_AUTH_CONF).value = config;
}

function renderAssignDatabase(modal, appName, config) {
    modal.buildHTML(`
        <h1>Assign Database</h1>
        <label>Application: <input id="${ID_ADD_ARG_APP}" disabled/></label><br>
        <label>Configuration: <input id="${ID_ADD_ARG_CONF}" disabled/></label><br>
        <label>Dataset: <input id="${ID_ADD_ARG_PARAM}"/></label><br>
        <label>Node: <input id="${ID_ADD_ARG_NODE}"/></label><br>
        <label>Database: <input id="${ID_ADD_ARG_DATABASE}"/></label><br>
    `).buildChild("button").buildText("Perform Assignment").buildEventListener("click", function() {
        let data = {};
        data[JEQL.KEY_APPLICATION] = document.getElementById(ID_ADD_ARG_APP).value;
        data[JEQL.KEY_CONFIGURATION] = document.getElementById(ID_ADD_ARG_CONF).value;
        data[JEQL.KEY_DATASET] = document.getElementById(ID_ADD_ARG_PARAM).value;
        data[JEQL.KEY_NODE] = document.getElementById(ID_ADD_ARG_NODE).value;
        data[JEQL.KEY_DATABASE] = document.getElementById(ID_ADD_ARG_DATABASE).value;
        JEQL.requests.makeBody(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_ASSIGNED_DATABASE_ADD, function() {
            JEQL.renderModalOk("Successfully assigned database to configuration", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_ASSIGNED_DATABASES).click();
            });
        }, data);
    });
    document.getElementById(ID_ADD_ARG_APP).value = appName;
    document.getElementById(ID_ADD_ARG_CONF).value = config;
}

function assignedDatabaseTableRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);

    let deleteFunc = function() {
        let delData = {};
        delData[JEQL.KEY_APPLICATION] = rowObj[JEQL.KEY_APPLICATION];
        delData[JEQL.KEY_DATASET] = rowObj[JEQL.KEY_DATASET];
        delData[JEQL.KEY_CONFIGURATION] = rowObj[JEQL.KEY_CONFIGURATION];
        JEQL.doConfirmDelete(window.JEQL_CONFIG, delData, JEQL.ACTION_INTERNAL_ASSIGNED_DATABASE_DEL,
            JEQL.ACTION_INTERNAL_ASSIGNED_DATABASE_DELCONF,
            function() { JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_ASSIGNED_DATABASES).click(); }
        );
    };

    rowElem.buildChild("td").buildChild("button").buildText("Delete").buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to unassign the database?", function() { deleteFunc(false); });
    });
}

function refreshAssignedDatabaseTable(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_ASSIGNED_DATABASES,
        function(data) {
            let table = document.getElementById(ID_TABLE_ASSIGNED_DATABASES);
            JEQL.pagedTableUpdate(table, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), table, assignedDatabaseTableRowRenderer);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function configAuthsTableRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);

    let deleteFunc = function() {
        let delData = {};
        delData[JEQL.KEY_APPLICATION] = rowObj[JEQL.KEY_APPLICATION];
        delData[JEQL.KEY_CONFIGURATION] = rowObj[JEQL.KEY_CONFIGURATION];
        delData[JEQL.KEY_ROLE] = rowObj[JEQL.KEY_ROLE];
        JEQL.doConfirmDelete(window.JEQL_CONFIG, delData, JEQL.ACTION_INTERNAL_CONFIG_AUTH_DEL,
            JEQL.ACTION_INTERNAL_CONFIG_AUTH_DELCONF,
            function() { JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_AUTHS).click(); }
        );
    };

    rowElem.buildChild("td").buildChild("button").buildText("Delete").buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete the authorization?", function() { deleteFunc(false); });
    });
}

function refreshConfigAuthsTable(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_CONFIG_AUTH,
        function(data) {
            let table = document.getElementById(ID_TABLE_AUTHS);
            JEQL.pagedTableUpdate(table, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), table, configAuthsTableRowRenderer);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function renderConfigModal(modal, appName, config) {
    modal.buildHTML(`
        <h1>Assigned Databases</h1>
        <table id="${ID_TABLE_ASSIGNED_DATABASES}">
            
        </table>
        <button id="${ID_ADD_ARG}">Add Assignment</button>
        <h1>Authorizations</h1>
        <table id="${ID_TABLE_AUTHS}">
            
        </table>
        <button id="${ID_ADD_AUTH}">Add Authorization</button>
    `);
    document.getElementById(ID_ADD_ARG).addEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderAssignDatabase(modal, appName, config); });
    });
    document.getElementById(ID_ADD_AUTH).addEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderAddAuth(modal, appName, config); });
    });

    let searchFunc = function(searchText, searchList) {
        let preSearch = JEQL.KEY_APPLICATION + "='" + appName + "' AND " + JEQL.KEY_CONFIGURATION + "='" + config + "'";
        let search = JEQL.simpleSearchTransformer(searchList)(searchText);
        if (search !== '') {
            preSearch += " AND " + search;
        }
        return preSearch;
    };
    JEQL.pagedSearchingTable(document.getElementById(ID_TABLE_ASSIGNED_DATABASES), refreshAssignedDatabaseTable,
        function(searchText) { return searchFunc(searchText, [JEQL.KEY_DATASET, JEQL.KEY_DATABASE, JEQL.KEY_NODE]); }
    );
    JEQL.pagedSearchingTable(document.getElementById(ID_TABLE_AUTHS), refreshConfigAuthsTable,
        function(searchText) { return searchFunc(searchText, [JEQL.KEY_ROLE]); });
}

function appConfigRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);
    rowElem.buildChild("td").buildChild("button").buildText("Select").buildEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderConfigModal(modal, rowObj[JEQL.KEY_APPLICATION],
            rowObj[JEQL.KEY_NAME]); }, true, JEQL.CLS_MODAL_AUTO);
    }).getParent().buildSibling("td").buildChild("button").buildText("Delete").buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete the configuration", function() {
            let data = {};
            data[JEQL.KEY_APPLICATION] = rowObj[JEQL.KEY_APPLICATION];
            data[JEQL.KEY_NAME] = rowObj[JEQL.KEY_NAME];
            JEQL.doConfirmDelete(window.JEQL_CONFIG, data, JEQL.ACTION_INTERNAL_CONFIG_DEL,
                JEQL.ACTION_INTERNAL_CONFIG_DELCONF,
                function() { JEQL.getPagedSearchingTableRefreshButton(ID_CONF_APP).click(); }
            );
        });
    });
}

function appParameterRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);
    rowElem.buildChild("td").buildChild("button").buildText("Delete").buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete the dataset", function() {
            let data = {};
            data[JEQL.KEY_APPLICATION] = rowObj[JEQL.KEY_APPLICATION];
            data[JEQL.KEY_NAME] = rowObj[JEQL.KEY_NAME];
            JEQL.doConfirmDelete(window.JEQL_CONFIG, data, JEQL.ACTION_INTERNAL_DATASETS_DEL,
                JEQL.ACTION_INTERNAL_DATASETS_DELCONF,
                function() { JEQL.getPagedSearchingTableRefreshButton(ID_PARAMETER_APP).click(); }
            );
        });
    });
}

function onLoadParameters(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_DATASETS,
        function(data) {
            let parameterTable = document.getElementById(ID_PARAMETER_APP);
            JEQL.pagedTableUpdate(parameterTable, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), parameterTable, appParameterRowRenderer);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function onLoadConfigurations(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_CONFIG,
        function(data) {
            let confTable = document.getElementById(ID_CONF_APP);
            JEQL.pagedTableUpdate(confTable, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), confTable, appConfigRowRenderer);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function renderAddConfigModal(modal, app) {
    modal.buildHTML(`
        <h1>Add a Config</h1>
        <label>Application: <input id="${ID_ADD_APP_CONFIG_APP}" disabled/></label><br>
        <label>Name: <input id="${ID_ADD_APP_CONFIG_NAME}"/></label><br>
        <label>Description: <input id="${ID_ADD_APP_CONFIG_DESCRIPTION}"/></label><br>
    `).buildChild("button").buildText("Add").buildEventListener("click", function() {
        let submitObj = {};
        submitObj[JEQL.KEY_APPLICATION] = document.getElementById(ID_ADD_APP_CONFIG_APP).value;
        submitObj[JEQL.KEY_NAME] = document.getElementById(ID_ADD_APP_CONFIG_NAME).value;
        submitObj[JEQL.KEY_DESCRIPTION] = document.getElementById(ID_ADD_APP_CONFIG_DESCRIPTION).value;

        JEQL.requests.makeBody(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_CONFIG_ADD, function() {
            JEQL.renderModalOk("Successfully added application config", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_CONF_APP).click();
            });
        }, submitObj);
    });
    document.getElementById(ID_ADD_APP_CONFIG_APP).value = app;
}

function renderAddParameterModal(modal, app) {
    modal.buildHTML(`
        <h1>Add a Dataset</h1>
        <label>Application: <input id="${ID_ADD_APP_PARAMETER_APP}" disabled/></label><br>
        <label>Name: <input id="${ID_ADD_APP_PARAMETER_NAME}"/></label><br>
        <label>Description: <input id="${ID_ADD_APP_PARAMETER_DESCRIPTION}"/></label><br>
    `).buildChild("button").buildText("Add").buildEventListener("click", function() {
        let submitObj = {};
        submitObj[JEQL.KEY_APPLICATION] = document.getElementById(ID_ADD_APP_PARAMETER_APP).value;
        submitObj[JEQL.KEY_NAME] = document.getElementById(ID_ADD_APP_PARAMETER_NAME).value;
        submitObj[JEQL.KEY_DESCRIPTION] = document.getElementById(ID_ADD_APP_PARAMETER_DESCRIPTION).value;

        JEQL.requests.makeBody(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_DATASETS_ADD, function() {
            JEQL.renderModalOk("Successfully added dataset", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_PARAMETER_APP).click();
            });
        }, submitObj);
    });
    document.getElementById(ID_ADD_APP_PARAMETER_APP).value = app;
}

function renderAppModal(modal, appName) {
    modal.buildHTML(`
        <h1>Datasets</h1>
        <table id=${ID_PARAMETER_APP}>
            
        </table>
        <button id=${ID_ADD_APP_PARAMETER}>
            Add Parameter
        </button>
        <h1>Configurations</h1>
        <table id=${ID_CONF_APP}>
            
        </table>
        <button id=${ID_ADD_APP_CONFIG}>
            Add Config
        </button>
        <br>
    `);
    document.getElementById(ID_ADD_APP_CONFIG).addEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderAddConfigModal(modal, appName); });
    });
    document.getElementById(ID_ADD_APP_PARAMETER).addEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderAddParameterModal(modal, appName); });
    });
    let appSearchFunc = function(searchText) {
        let preSearch = JEQL.KEY_APPLICATION + "='" + appName + "'";
        let search = JEQL.simpleSearchTransformer(
            [JEQL.KEY_NAME, JEQL.KEY_DESCRIPTION])(searchText);
        if (search !== '') {
            preSearch += " AND " + search;
        }
        return preSearch;
    };
    JEQL.pagedSearchingTable(document.getElementById(ID_CONF_APP), onLoadConfigurations, appSearchFunc);
    JEQL.pagedSearchingTable(document.getElementById(ID_PARAMETER_APP), onLoadParameters, appSearchFunc);
}

function rowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);

    rowElem.buildChild("td").buildChild("button").buildText("Select").buildEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderAppModal(modal, rowObj[JEQL.KEY_NAME]); }, true, JEQL.CLS_MODAL_WIDE);
    }).getParent().buildSibling("td").buildChild("button").buildText("Delete").buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete the application", function() {
            let delData = {};
            delData[JEQL.KEY_NAME] = rowObj[JEQL.KEY_NAME];
            JEQL.doConfirmDelete(window.JEQL_CONFIG, delData, JEQL.ACTION_INTERNAL_APPLICATIONS_DEL,
                JEQL.ACTION_INTERNAL_APPLICATIONS_DELCONF,
                function() { JEQL.getPagedSearchingTableRefreshButton(ID_APPLICATION_LIST).click(); }
            );
        });
    });
}

function renderAddEmailTemplate(modal, emailAccount) {
    modal.buildHTML(`
        <h1>Add a Email Template</h1><br>
        <label>Name: <input id="${ID_ADD_EMAIL_TEMPLATE_NAME}"/></label><br>
        <label>Account: <input id="${ID_ADD_EMAIL_TEMPLATE_ACCOUNT}" disabled/></label><br>
        <label>Description: <input id="${ID_ADD_EMAIL_TEMPLATE_DESCRIPTION}"/></label><br>
        <label>App Relative Path: <input id="${ID_ADD_EMAIL_TEMPLATE_APP_RELATIVE_PATH}"/></label><br>
        <label>Subject: <input id="${ID_ADD_EMAIL_TEMPLATE_SUBJECT}"/></label><br>
        <label>Allow Signup: <input id="${ID_ADD_EMAIL_TEMPLATE_ALLOW_SIGNUP}" type="checkbox"/></label><br>
        <label>Allow Already Exists: <input id="${ID_ADD_EMAIL_TEMPLATE_ALLOW_ALREADY_EXISTS}" type="checkbox"/></label><br>
        <label>Data Validation Table: <input id="${ID_ADD_EMAIL_TEMPLATE_DATA_VALIDATION_TABLE}"/></label><br>
        <label>Data Validation View: <input id="${ID_ADD_EMAIL_TEMPLATE_DATA_VALIDATION_VIEW}"/></label><br>
        <label>Recipient Validation View: <input id="${ID_ADD_EMAIL_TEMPLATE_RECIPIENT_VALIDATION_VIEW}"/></label><br>
    `).buildChild("button").buildText("Add").buildEventListener("click", function() {
        let submitObj = {};
        submitObj[JEQL.KEY_NAME] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_NAME).value;
        submitObj[JEQL.KEY_DESCRIPTION] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_DESCRIPTION).value;
        submitObj[JEQL.KEY_APP_RELATIVE_PATH] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_APP_RELATIVE_PATH).value;
        submitObj[JEQL.KEY_SUBJECT] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_SUBJECT).value;
        submitObj[JEQL.KEY_ACCOUNT] = emailAccount;
        submitObj[JEQL.KEY_ALLOW_SIGNUP] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_ALLOW_SIGNUP).checked;
        submitObj[JEQL.KEY_ALLOW_CONFIRM_SIGNUP_ATTEMPT] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_ALLOW_ALREADY_EXISTS).checked;
        if (document.getElementById(ID_ADD_EMAIL_TEMPLATE_DATA_VALIDATION_TABLE).value) {
            submitObj[JEQL.KEY_DATA_VALIDATION_TABLE] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_DATA_VALIDATION_TABLE).value;
        }
        if (document.getElementById(ID_ADD_EMAIL_TEMPLATE_DATA_VALIDATION_VIEW).value) {
            submitObj[JEQL.KEY_DATA_VALIDATION_VIEW] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_DATA_VALIDATION_VIEW).value;
        }
        if (document.getElementById(ID_ADD_EMAIL_TEMPLATE_RECIPIENT_VALIDATION_VIEW).value) {
            submitObj[JEQL.KEY_RECIPIENT_VALIDATION_VIEW] = document.getElementById(ID_ADD_EMAIL_TEMPLATE_RECIPIENT_VALIDATION_VIEW).value;
        }

        JEQL.requests.makeJson(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_EMAIL_TEMPLATES_ADD, function() {
            JEQL.renderModalOk("Successfully added email template", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_EMAIL_TEMPLATES).click();
            });
        }, submitObj);
    });
    document.getElementById(ID_ADD_EMAIL_TEMPLATE_ACCOUNT).value = emailAccount;
}

function renderAddDatabase(modal, node) {
    modal.buildHTML(`
        <h1>Add a Database</h1><br>
        Submitting the name as '*' allows for the use of a wildcard database<br>
        <label>Node: <input id="${ID_ADD_NODE_DATABASE_NODE}" disabled/></label><br>
        <label>Name: <input id="${ID_ADD_NODE_DATABASE_NAME}"/></label><br>
        <label>Also create database on node: <input id="${ID_ADD_NODE_DATABASE_CREATE}" type="checkbox"/></label><br>
    `).buildChild("button").buildText("Add").buildEventListener("click", function() {
        let submitObj = {};
        submitObj[JEQL.KEY_NODE] = document.getElementById(ID_ADD_NODE_DATABASE_NODE).value;
        submitObj[JEQL.KEY_NAME] = document.getElementById(ID_ADD_NODE_DATABASE_NAME).value;
        submitObj[JEQL.KEY_CREATE] = document.getElementById(ID_ADD_NODE_DATABASE_CREATE).checked;

        JEQL.requests.makeBody(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_DATABASES_ADD, function() {
            JEQL.renderModalOk("Successfully added database", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_DATABASES).click();
            });
        }, submitObj);
    });
    document.getElementById(ID_ADD_NODE_DATABASE_NODE).value = node;
}

function renderAddCredentials(modal, node) {
    modal.buildHTML(`
        <h1>Add Node Credentials</h1><br>
        <label>Node: <input id="${ID_ADD_NODE_AUTH_NODE}" disabled/></label><br>
        <label>Role: <input id="${ID_ADD_NODE_AUTH_ROLE}"/></label><br>
        <label>Precedence: <input id="${ID_ADD_NODE_AUTH_PRECEDENCE}"/></label><br>
        <label>Username: <input id="${ID_ADD_NODE_AUTH_USERNAME}"/></label><br>
        <label>Password: <input id="${ID_ADD_NODE_AUTH_PASSWORD}" type="password"/></label><br>
    `).buildChild("button").buildText("Add").buildEventListener("click", function() {
        let submitObj = {};
        submitObj[JEQL.KEY_NODE] = document.getElementById(ID_ADD_NODE_AUTH_NODE).value;
        submitObj[JEQL.KEY_ROLE] = document.getElementById(ID_ADD_NODE_AUTH_ROLE).value;
        submitObj[JEQL.KEY_PRECEDENCE] = parseInt(document.getElementById(ID_ADD_NODE_AUTH_PRECEDENCE).value);
        submitObj[JEQL.KEY_USERNAME] = document.getElementById(ID_ADD_NODE_AUTH_USERNAME).value;
        submitObj[JEQL.KEY_PASSWORD] = document.getElementById(ID_ADD_NODE_AUTH_PASSWORD).value;

        JEQL.requests.makeJson(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_NODE_AUTHS_ADD, function() {
            JEQL.renderModalOk("Successfully added credentials", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_NODE_AUTHS).click();
            });
        }, submitObj);
    });
    document.getElementById(ID_ADD_NODE_AUTH_NODE).value = node;
}

function databaseTableRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);
    let isDeleted = rowObj[JEQL.KEY_DELETED];

    let deleteFunc = function(doDrop) {
        let delData = {};
        delData[JEQL.KEY_NAME] = rowObj[JEQL.KEY_NAME];
        delData[JEQL.KEY_NODE] = rowObj[JEQL.KEY_NODE];
        delData[JEQL.KEY_DROP] = doDrop;
        JEQL.doConfirmDelete(window.JEQL_CONFIG, delData, JEQL.ACTION_INTERNAL_DATABASES_DEL,
            JEQL.ACTION_INTERNAL_DATABASES_DELCONF,
            function() { JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_DATABASES).click(); }
        );
    };

    rowElem.buildChild("td").buildChild("button").buildBoolean("disabled", isDeleted).buildText("Delete"
    ).buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete the database?", function() { deleteFunc(false); });
    }).getParent().buildSibling("td").buildChild("button").buildBoolean(
        "disabled", isDeleted || rowObj[JEQL.KEY_NAME] === '*').buildText("Delete and Drop").buildEventListener("click",
        function() {
            JEQL.renderModalAreYouSure("Would you like to delete and drop the database?",
                function() { deleteFunc(false); });
        }
    );
}

function credentialsTableRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);

    rowElem.buildChild("td").buildChild("button").buildBoolean("disabled", rowObj[JEQL.KEY_DELETED]).buildText("Delete"
    ).buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete these credentials?", function() {
            let delData = {};
            delData[JEQL.KEY_NODE] = rowObj[JEQL.KEY_NODE];
            delData[JEQL.KEY_ROLE] = rowObj[JEQL.KEY_ROLE];
            JEQL.doConfirmDelete(window.JEQL_CONFIG, delData, JEQL.ACTION_INTERNAL_NODE_AUTHS_DEL,
                JEQL.ACTION_INTERNAL_NODE_AUTHS_DELCONF,
                function() { JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_NODE_AUTHS).click(); }
            );
        });
    });
}

function refreshDatabasesTable(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_DATABASES,
        function(data) {
            let table = document.getElementById(ID_TABLE_DATABASES);
            JEQL.pagedTableUpdate(table, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), table, databaseTableRowRenderer);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function refreshCredentialsTable(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_NODE_AUTHS,
        function(data) {
            let table = document.getElementById(ID_TABLE_NODE_AUTHS);
            JEQL.pagedTableUpdate(table, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), table, credentialsTableRowRenderer);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function emailTemplatesTableTableRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);

    rowElem.buildChild("td").buildChild("button").buildBoolean("disabled", rowObj[JEQL.KEY_DELETED]).buildText("Delete"
    ).buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete this email template?", function() {
            let delData = {};
            delData[JEQL.KEY_NAME] = rowObj[JEQL.KEY_NAME];
            JEQL.doConfirmDelete(window.JEQL_CONFIG, delData, JEQL.ACTION_INTERNAL_EMAIL_TEMPLATES_DEL,
                JEQL.ACTION_INTERNAL_EMAIL_TEMPLATES_DELCONF,
                function() { JEQL.getPagedSearchingTableRefreshButton(ID_TABLE_NODE_AUTHS).click(); }
            );
        });
    });
}

function refreshEmailTemplateTable(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_EMAIL_TEMPLATES,
        function(data) {
            let table = document.getElementById(ID_TABLE_EMAIL_TEMPLATES);
            JEQL.pagedTableUpdate(table, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), table, emailTemplatesTableTableRowRenderer, [JEQL.KEY_ID]);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function renderEmailAccountModal(modal, emailAccount) {
    modal.buildHTML(`
        <h1>Email Account</h1>
        <table id="${ID_TABLE_EMAIL_TEMPLATES}">
            
        </table>
        <button id="${ID_ADD_EMAIL_TEMPLATE}">Add Email Template</button>
    `);
    document.getElementById(ID_ADD_EMAIL_TEMPLATE).addEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderAddEmailTemplate(modal, emailAccount); });
    });

    let emailAccountSearchFunc = function(searchText) {
        let preSearch = JEQL.KEY_ACCOUNT + "='" + emailAccount + "'";
        let searchFields = [JEQL.KEY_NAME, JEQL.KEY_SUBJECT, JEQL.KEY_DESCRIPTION, JEQL.KEY_APP_RELATIVE_PATH, JEQL.KEY_DATA_VALIDATION_TABLE,
            JEQL.KEY_DATA_VALIDATION_VIEW, JEQL.KEY_RECIPIENT_VALIDATION_VIEW];
        let search = JEQL.simpleSearchTransformer(searchFields)(searchText);
        if (search !== '') {
            preSearch += " AND " + search;
        }
        return preSearch;
    };
    JEQL.pagedSearchingTable(document.getElementById(ID_TABLE_EMAIL_TEMPLATES), refreshEmailTemplateTable, emailAccountSearchFunc);
}

function renderNodeModal(modal, node) {
    modal.buildHTML(`
        <h1>Databases</h1>
        <table id="${ID_TABLE_DATABASES}">
            
        </table>
        <button id="${ID_ADD_NODE_DATABASE}">Add Database</button>
        <h1>Credentials</h1>
        <table id="${ID_TABLE_NODE_AUTHS}">
            
        </table>
        <button id="${ID_ADD_NODE_AUTH}">Add Credentials</button>
    `);
    document.getElementById(ID_ADD_NODE_DATABASE).addEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderAddDatabase(modal, node); });
    });
    document.getElementById(ID_ADD_NODE_AUTH).addEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderAddCredentials(modal, node); });
    });
    let databaseSearchFunc = function(searchText) {
        let preSearch = JEQL.KEY_NODE + "='" + node + "'";
        let search = JEQL.simpleSearchTransformer([JEQL.KEY_NAME])(searchText);
        if (search !== '') {
            preSearch += " AND " + search;
        }
        return preSearch;
    };
    let credentialsSearchFunc = function(searchText) {
        let preSearch = JEQL.KEY_NODE + "='" + node + "'";
        let search = JEQL.simpleSearchTransformer([JEQL.KEY_ROLE, JEQL.KEY_PRECEDENCE])(searchText);
        if (search !== '') {
            preSearch += " AND " + search;
        }
        return preSearch;
    };
    JEQL.pagedSearchingTable(document.getElementById(ID_TABLE_DATABASES), refreshDatabasesTable, databaseSearchFunc);
    JEQL.pagedSearchingTable(document.getElementById(ID_TABLE_NODE_AUTHS), refreshCredentialsTable, credentialsSearchFunc);
}

function emailAccountTableRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);

    rowElem.buildChild("td").buildChild("button").buildBoolean("disabled", rowObj[JEQL.KEY_DELETED]).buildText("Select"
    ).buildEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderEmailAccountModal(modal, rowObj[JEQL.KEY_NAME]); }, true, JEQL.CLS_MODAL_WIDEST);
    }).getParent().buildSibling("td").buildChild("button").buildBoolean("disabled", rowObj[JEQL.KEY_DELETED]
    ).buildText("Delete").buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete the email account?", function() {
            let delData = {};
            delData[JEQL.KEY_NAME] = rowObj[JEQL.KEY_NAME];
            JEQL.doConfirmDelete(window.JEQL_CONFIG, delData, JEQL.ACTION_INTERNAL_EMAIL_ACCOUNTS_DEL,
                JEQL.ACTION_INTERNAL_EMAIL_ACCOUNTS_DELCONF,
                function() { JEQL.getPagedSearchingTableRefreshButton(ID_EMAIL_ACCOUNT_LIST).click(); }
            );
        });
    });
}

function nodeTableRowRenderer(rowElem, data, idx, superRowRenderer) {
    superRowRenderer();
    let rowObj = JEQL.tupleToObject(data[JEQL.KEY_ROWS][idx], data[JEQL.KEY_COLUMNS]);

    rowElem.buildChild("td").buildChild("button").buildBoolean("disabled", rowObj[JEQL.KEY_DELETED]).buildText("Select"
    ).buildEventListener("click", function() {
        JEQL.renderModal(function(modal) { renderNodeModal(modal, rowObj[JEQL.KEY_NAME]); }, true, JEQL.CLS_MODAL_WIDE);
    }).getParent().buildSibling("td").buildChild("button").buildBoolean("disabled", rowObj[JEQL.KEY_DELETED]
    ).buildText("Delete").buildEventListener("click", function() {
        JEQL.renderModalAreYouSure("Would you like to delete the node?", function() {
            let delData = {};
            delData[JEQL.KEY_NAME] = rowObj[JEQL.KEY_NAME];
            JEQL.doConfirmDelete(window.JEQL_CONFIG, delData, JEQL.ACTION_INTERNAL_NODES_DEL,
                JEQL.ACTION_INTERNAL_NODES_DELCONF,
                function() { JEQL.getPagedSearchingTableRefreshButton(ID_NODE_LIST).click(); }
            );
        });
    });
}

function addEmailAccountModal(modal) {
    modal.buildHTML(`
        <h1>Add Email Account</h1>
        <label>Name: <input id="${ID_ADD_EMAIL_ACCOUNT_NAME}" /></label><br>
        <label>Send as Name: <input id="${ID_ADD_EMAIL_ACCOUNT_SEND_NAME}" /></label><br>
        <label>Host: <input id="${ID_ADD_EMAIL_ACCOUNT_HOST}" /></label><br>
        <label>Port: <input id="${ID_ADD_EMAIL_ACCOUNT_PORT}" /></label><br>
        <label>Username: <input id="${ID_ADD_EMAIL_ACCOUNT_USERNAME}" /></label><br>
        <label>Password: <input id="${ID_ADD_EMAIL_ACCOUNT_PASSWORD}" /></label><br>
    `).buildChild("button").buildText("Add").buildEventListener("click", function() {
        let data = {};
        data[JEQL.KEY_NAME] = document.getElementById(ID_ADD_EMAIL_ACCOUNT_NAME).value;
        data[JEQL.KEY_SEND_NAME] = document.getElementById(ID_ADD_EMAIL_ACCOUNT_SEND_NAME).value;
        data[JEQL.KEY_HOST] = document.getElementById(ID_ADD_EMAIL_ACCOUNT_HOST).value;
        data[JEQL.KEY_PROTOCOL] = "smtp";
        data[JEQL.KEY_PORT] = document.getElementById(ID_ADD_EMAIL_ACCOUNT_PORT).value;
        data[JEQL.KEY_USERNAME] = document.getElementById(ID_ADD_EMAIL_ACCOUNT_USERNAME).value;
        data[JEQL.KEY_PASSWORD] = document.getElementById(ID_ADD_EMAIL_ACCOUNT_PASSWORD).value;
        JEQL.requests.makeJson(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_EMAIL_ACCOUNTS_ADD, function() {
            JEQL.renderModalOk("Successfully added email account", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_EMAIL_ACCOUNT_LIST).click();
            });
        }, data);
    });
}

function addNodeModal(modal) {
    modal.buildHTML(`
        <h1>Add Node</h1>
        <label>Name: <input id="${ID_ADD_NODE_NAME}" /></label><br>
        <label>Description: <input id="${ID_ADD_NODE_DESCRIPTION}" /></label><br>
        <label>Address: <input id="${ID_ADD_NODE_ADDRESS}" /></label><br>
        <label>Port: <input id="${ID_ADD_NODE_PORT}" /></label><br>
    `).buildChild("button").buildText("Add").buildEventListener("click", function() {
        let data = {};
        data[JEQL.KEY_NAME] = document.getElementById(ID_ADD_NODE_NAME).value;
        data[JEQL.KEY_DESCRIPTION] = document.getElementById(ID_ADD_NODE_DESCRIPTION).value;
        data[JEQL.KEY_ADDRESS] = document.getElementById(ID_ADD_NODE_ADDRESS).value;
        data[JEQL.KEY_PORT] = document.getElementById(ID_ADD_NODE_PORT).value;
        JEQL.requests.makeJson(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_NODES_ADD, function() {
            JEQL.renderModalOk("Successfully added node", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_NODE_LIST).click();
            });
        }, data);
    });
}

function addAppModal(modal) {
    modal.buildHTML(`
        <h1>Add App</h1>
        You can use {{DEFAULT}} in the app url to have it replaced by the JAAQL url e.g. {{DEFAULT}}/console<br>
        <label>Name: <input id="${ID_ADD_APP_NAME}" /></label><br>
        <label>Description: <input id="${ID_ADD_APP_DESCRIPTION}" /></label><br>
        <label>Url: <input id="${ID_ADD_APP_URL}" /></label><br>
        <label>Public Username: <input id="${ID_ADD_PUBLIC_USERNAME}" /></label><br>
    `).buildChild("button").buildText("Add").buildEventListener("click", function() {
        let data = {};
        data[JEQL.KEY_NAME] = document.getElementById(ID_ADD_APP_NAME).value;
        data[JEQL.KEY_DESCRIPTION] = document.getElementById(ID_ADD_APP_DESCRIPTION).value;
        data[JEQL.KEY_URL] = document.getElementById(ID_ADD_APP_URL).value;
        data[JEQL.KEY_PUBLIC_USERNAME] = document.getElementById(ID_ADD_PUBLIC_USERNAME).value;
        if (data[JEQL.KEY_PUBLIC_USERNAME].length === 0) {
            delete data[JEQL.KEY_PUBLIC_USERNAME];
        }
        JEQL.requests.makeJson(window.JEQL_CONFIG, JEQL.ACTION_INTERNAL_APPLICATIONS_ADD, function() {
            JEQL.renderModalOk("Successfully added application", function() {
                modal.closeModal();
                JEQL.getPagedSearchingTableRefreshButton(ID_APPLICATION_LIST).click();
            });
        }, data);
    });
}

function refreshEmailAccountTable(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_EMAIL_ACCOUNTS,
        function(data) {
            let emailAccountTable = document.getElementById(ID_EMAIL_ACCOUNT_LIST);
            JEQL.pagedTableUpdate(emailAccountTable, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), emailAccountTable, emailAccountTableRowRenderer, [JEQL.KEY_ID]);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function refreshNodeTable(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_NODES,
        function(data) {
            let nodeTable = document.getElementById(ID_NODE_LIST);
            JEQL.pagedTableUpdate(nodeTable, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), nodeTable, nodeTableRowRenderer);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

function refreshAppTable(page, size, search, sort) {
    JEQL.requests.makeBody(window.JEQL_CONFIG,
        JEQL.ACTION_INTERNAL_APPLICATIONS,
        function(data) {
            let appTable = document.getElementById(ID_APPLICATION_LIST);
            JEQL.pagedTableUpdate(appTable, data);
            JEQL.tableRenderer(JEQL.objectsToTuples(data[JEQL.KEY_DATA]), appTable, rowRenderer);
        },
        JEQL.getSearchObj(page, size, search, sort)
    );
}

window.onload = function() {
    document.getElementById(ID_ADD_APP).addEventListener("click", function() { JEQL.renderModal(addAppModal); });
    document.getElementById(ID_ADD_NODE).addEventListener("click", function() { JEQL.renderModal(addNodeModal); });
    document.getElementById(ID_ADD_EMAIL_ACCOUNT).addEventListener("click", function() { JEQL.renderModal(addEmailAccountModal); });
    JEQL.init(APPLICATION_NAME, function() {
        JEQL.pagedSearchingTable(document.getElementById(ID_APPLICATION_LIST), refreshAppTable,
            JEQL.simpleSearchTransformer([JEQL.KEY_NAME, JEQL.KEY_URL, JEQL.KEY_DESCRIPTION]));

        JEQL.pagedSearchingTable(document.getElementById(ID_NODE_LIST), refreshNodeTable, JEQL.simpleSearchTransformer(
            [JEQL.KEY_NAME, JEQL.KEY_PORT, JEQL.KEY_ADDRESS, JEQL.KEY_DESCRIPTION]
        ));

        JEQL.pagedSearchingTable(document.getElementById(ID_EMAIL_ACCOUNT_LIST), refreshEmailAccountTable, JEQL.simpleSearchTransformer(
            [JEQL.KEY_NAME, JEQL.KEY_SEND_NAME, JEQL.KEY_HOST, JEQL.KEY_PORT, JEQL.KEY_USERNAME]
        ));
    });
};

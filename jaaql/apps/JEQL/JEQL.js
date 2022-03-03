import "./css_loader.js"  // Will import the CSS
import * as requests from "./requests/requests.js"; export {requests}
let HTTP_STATUS_DEFAULT = requests.HTTP_STATUS_DEFAULT; export {HTTP_STATUS_DEFAULT};

let VERSION = "1.0.0";
console.log("Loaded JEQL library, version " + VERSION);

let HTTP_STATUS_CONNECTION_EXPIRED = 419;
let HTTP_STATUS_OK = 200; export {HTTP_STATUS_OK};

let STORAGE_JAAQL_TOKENS = "JAAQL_TOKENS";
let STORAGE_JAAQL_CONFIGS = "JAAQL_CONFIGS";

let ACTION_LOGIN = "POST /oauth/token";
let ACTION_FETCH_APPLICATIONS = "GET /applications";
let ACTION_REFRESH = "POST /oauth/refresh";
let ACTION_SUBMIT = "POST /submit";
let ACTION_SUBMIT_FILE = "POST /submit-file";
let ACTION_CONFIGURATIONS = "GET /configurations";
let ACTION_CONFIGURATIONS_ARGUMENTS = "GET /configurations/arguments";
let ACTION_FETCH_LOGIN_DETAILS = "GET /login-details";
let ACTION_GET_CONNECTION_DATABASES = "GET /databases";
let ACTION_UPDATE_CONNECTION_DATABASES = "PUT /databases";

let PARAMETER_JAAQL = "jaaql";
let PARAMETER_CONFIGURATION = "configuration";

let JWT_KEY_CONFIG_NAME = "name";

let ERR_WIPING_CONFIG = "Error when loading app config, wiping config";
let ERR_IMPERATIVE_APP_CONFIG_FAILED = "Tried to get app config in an imperative manner yet app config was not set";
let ERR_NO_FOUND_CONFIGURATION_FOR_USER = "No configuration found for user";
let ERR_COULD_NOT_REFRESH_APP_CONFIG = "Could not refresh app config connection token";
let ERR_COULD_NOT_FIND_APPLICATION_WITH_NAME = "Could not find application with name ";

let KEY_QUERY = "query";
let KEY_PARAMETERS = "parameters";
let KEY_FORCE_TRANSACTIONAL = "force_transactional"; export {KEY_FORCE_TRANSACTIONAL};
let KEY_DATABASE = "database";
let KEY_CONNECTION = "connection";
let KEY_USERNAME = "username";
let KEY_PASSWORD = "password";
let KEY_MFA_KEY = "mfa_key";
let KEY_CONFIGURATION = "configuration";
let KEY_APPLICATION = "application";
let KEY_PARAMETER_NAME = "parameter_name";
let KEY_CONNECTIONS = "connections";
let KEY_NAME = "name";
let KEY_DATA = "data";
let KEY_URL = "url";
let KEY_SEARCH = "search";

let PROTOCOL_FILE = "file:";
let LOCAL_DEBUGGING_URL = "http://127.0.0.1:6060";

let CLS_MODAL_OUTER = "jeql-modal-outer";
let CLS_MODAL = "jeql-modal";
let CLS_MODAL_WIDE = "jeql-modal-wide";
let CLS_BUTTON = "jeql-button";
let CLS_MODAL_CLOSE = "jeql-modal-close";
let CLS_CURSOR_POINTER = "jeql-cursor-pointer";
let CLS_CENTER = "jeql-center";
let CLS_INPUT_MFA = "jeql-input-mfa";
let CLS_SELECTED_APP_CONFIG = "jeql-selected-app-config";

let ATTR_JEQL_DATA = "jeql-data";

let ID_LOGIN_MODAL = "jeql-login-modal";
let ID_LOGIN_ERROR = "jeql-login-error";
let ID_USERNAME = "jeql-username";
let ID_PASSWORD = "jeql-password";
let ID_REMEMBER_ME = "jeql-remember-me";
let ID_MFA_0 = "jeql-mfa-0";
let ID_MFA_1 = "jeql-mfa-1";
let ID_MFA_2 = "jeql-mfa-2";
let ID_MFA_3 = "jeql-mfa-3";
let ID_MFA_4 = "jeql-mfa-4";
let ID_MFA_5 = "jeql-mfa-5";
let ID_LOGIN_BUTTON = "jeql-login-button";
let ID_SELECT_APP_CONFIG = "jeql-select-app-config-";

let CLS_INPUT = "jeql-input";

function buildChild(elem, tag) {
    let child = elemBuilder(tag);
    elem.appendChild(child);
    return child;
}

function buildClass(elem, classOrClasses) {
   if (!Array.isArray(classOrClasses)) {
       classOrClasses = [classOrClasses];
   }

   for (let curClass in classOrClasses) {
       elem.classList.add(classOrClasses[curClass]);
   }

   return elem;
}

function buildSibling(elem, tag) {
    let sibling = elemBuilder(tag);
    sibling.parentElement.appendChild(sibling);
    return sibling;
}

function buildAttr(elem, attr, value) {
    elem.setAttribute(attr, value);
    return elem;
}

function buildText(elem, text) {
    elem.innerText = text;
    return elem;
}

function buildHTML(elem, html) {
    elem.innerHTML += html;
    return elem;
}

export function tableRenderer(data) {
    let table = elemBuilder("table");
    document.body.appendChild(table);
    let header = table.buildChild("tr");
    for (let idx in Object.keys(data["columns"])) {
        header.buildChild("th").buildText(formatAsTableHeader(data["columns"][idx]));
    }
    header.buildChild("th");
    for (let idx in data["rows"]) {
        let row = table.buildChild("tr");
        for (let key in data["rows"][idx]) {
            row.buildChild("td").buildText(data["rows"][idx][key]);
        }
    }
}

export function tableBodyRenderer(data, tableBody) {
    makeBuildable(tableBody);
    for (let idx in data["rows"]) {
        let row = tableBody.buildChild("tr");
        for (let key in data["rows"][idx]) {
            row.buildChild("td").buildText(data["rows"][idx][key]);
        }
    }
}

export function makeBuildable(elem) {
    elem.buildClass = function(classOrClasses) { return buildClass(elem, classOrClasses); };
    elem.buildAttr = function(attr, value) { return buildAttr(elem, attr, value); };
    elem.buildText = function(text) { return buildText(elem, text); };
    elem.buildHTML = function(html) { return buildHTML(elem, html); };
    elem.buildChild = function(tag) { return buildChild(elem, tag); };
    elem.buildSibling = function(tag) { return buildSibling(elem, tag); };
}

export function elemBuilder(tag) {
    let ret = document.createElement(tag);
    makeBuildable(ret);
    return ret;
}

export function getConnectionDatabases(config, renderFunc, parameter = null) {
    let data = {};
    data[KEY_CONNECTION] = fetchConnection(config, parameter);
    let renderFuncs = {};
    renderFuncs[HTTP_STATUS_OK] = renderFunc;
    renderFuncs[HTTP_STATUS_CONNECTION_EXPIRED] = expiredConnectionHandler;
    return requests.makeBody(config, ACTION_GET_CONNECTION_DATABASES, renderFuncs, data);
}

export function updateConnectionDatabases(config, renderFunc, parameter = null) {
    let data = {};
    data[KEY_CONNECTION] = fetchConnection(config, parameter);
    let renderFuncs = {};
    if (renderFunc.constructor === Object) {
        renderFuncs = renderFunc;
    } else {
        renderFuncs[HTTP_STATUS_OK] = renderFunc;
    }
    renderFuncs[HTTP_STATUS_CONNECTION_EXPIRED] = expiredConnectionHandler;
    return requests.makeBody(config, ACTION_UPDATE_CONNECTION_DATABASES, renderFuncs, data);
}

function xHttpSetAuth(config, xhttp) {
    xhttp.setRequestHeader("Authentication-Token", config.authToken);
}

function renderModal(modalBodyRender, allowClose = true, modalBaseClass = CLS_MODAL, modalAdditionalClass = null) {
    let outerDiv = document.createElement("div");
    document.body.appendChild(outerDiv);
    outerDiv.setAttribute("class", CLS_MODAL_OUTER);

    let modalDiv = elemBuilder("div");
    outerDiv.appendChild(modalDiv);
    modalDiv.classList.add(modalBaseClass);
    if (modalAdditionalClass !== null) {
        modalDiv.classList.add(modalAdditionalClass);
    }

    if (allowClose) {
        outerDiv.classList.add(CLS_CURSOR_POINTER);
        let modalClose = elemBuilder("span").buildClass(CLS_MODAL_CLOSE).buildHTML("&times;");
        modalDiv.appendChild(modalClose);
        modalClose.addEventListener("click", function(event) {
            document.body.removeChild(outerDiv);
        }, true);
        outerDiv.addEventListener("click", function(event) {
            if (event.target === outerDiv) {
                document.body.removeChild(outerDiv);
            }
        }, false);
    }

    modalDiv.closeModal = function() { outerDiv.parentElement.removeChild(outerDiv); };

	modalBodyRender(modalDiv);
}

export function renderModalError(errMsg, errTitle = "Error!") {

}

export function renderModalAreYouSure(yesFunc, text, title = "Are you sure?", yesButtonText = "Yes",
                                      noButtonText = "No") {

}

function bindButton(eleId, buttonId) {
    document.getElementById(eleId).addEventListener("keyup", function(event) {
        if (event.keyCode === 13) {
            event.preventDefault();
            document.getElementById(buttonId).click();
        }
    });
}

function setMFAKey(curId, nextId, nextFunc = null) {
    if (nextFunc === null) {
        nextFunc = function() { document.getElementById(nextId).focus(); };
    }
    document.getElementById(curId).onkeypress = function(event) {
        if (Number.parseInt(event.key)) {
            document.getElementById(curId).value = event.key;
            nextFunc();
        } else {
            event.preventDefault();
        }
    };
}

function getLoginData(renderMFA) {
    let ret = {};

    ret[KEY_USERNAME] = document.getElementById(ID_USERNAME).value;
    ret[KEY_PASSWORD] = document.getElementById(ID_PASSWORD).value;

    if (renderMFA) {
        ret[KEY_MFA_KEY] = document.getElementById(ID_MFA_0).value + document.getElementById(ID_MFA_1).value +
            document.getElementById(ID_MFA_2).value + document.getElementById(ID_MFA_3).value +
            document.getElementById(ID_MFA_4).value + document.getElementById(ID_MFA_5).value;
    }

    return ret;
}

function rendererLogin(modal, config, callback, errMsg, renderMFA) {
    modal.id = ID_LOGIN_MODAL;
    modal.appendChild(elemBuilder("div").buildClass(CLS_CENTER).buildHTML(`
        <h1>
            Login
        </h1>
    `));

    let mainLoginDiv = elemBuilder("div").buildHTML(`
        <span id=${ID_LOGIN_ERROR} style="color: red"></span>
        <br>
        <label class="jeql-strong">
            Username
            <input class="${CLS_INPUT} jeql-input-full" type="text" placeholder="Enter username" id=${ID_USERNAME}>
        </label>
        <label class="jeql-strong">
            Password 
            <input class="${CLS_INPUT} jeql-input-full" type="password" placeholder="Enter password" id=${ID_PASSWORD}>
        </label>
    `);
    modal.appendChild(mainLoginDiv);
    if (errMsg) {
        document.getElementById(ID_LOGIN_ERROR).innerHTML = errMsg + "<br>";
    }

    if (renderMFA) {
        mainLoginDiv.buildHTML(`
            <label class="jeql-strong">
                2FA
                <br>
                <div style="width: 100%; display: flex; gap: 1%">
                    <input class="${CLS_INPUT} ${CLS_INPUT_MFA}" type="text" id=${ID_MFA_0} maxlength="1" size="1">
                    <input class="${CLS_INPUT} ${CLS_INPUT_MFA}" type="text" id=${ID_MFA_1} maxlength="1" size="1">
                    <input class="${CLS_INPUT} ${CLS_INPUT_MFA}" type="text" id=${ID_MFA_2} maxlength="1" size="1">
                    <input class="${CLS_INPUT} ${CLS_INPUT_MFA}" type="text" id=${ID_MFA_3} maxlength="1" size="1">
                    <input class="${CLS_INPUT} ${CLS_INPUT_MFA}" type="text" id=${ID_MFA_4} maxlength="1" size="1">
                    <input class="${CLS_INPUT} ${CLS_INPUT_MFA}" type="text" id=${ID_MFA_5} maxlength="1" size="1">
                </div>
            </label>
        `);

        setMFAKey(ID_MFA_0, ID_MFA_1);
        setMFAKey(ID_MFA_1, ID_MFA_2);
        setMFAKey(ID_MFA_2, ID_MFA_3);
        setMFAKey(ID_MFA_3, ID_MFA_4);
        setMFAKey(ID_MFA_4, ID_MFA_5);
        setMFAKey(ID_MFA_5, null, function() { document.getElementById(ID_LOGIN_BUTTON).click() });
    }

    let rememberMeBox = modal.buildChild("div").buildHTML(`
        <label for=${ID_REMEMBER_ME}>Remember me</label>
        <input type="checkbox" id=${ID_REMEMBER_ME}>
    `);
    rememberMeBox.checked = config.rememberMe;

    let button = elemBuilder("div")
        .buildChild("button")
        .buildClass(CLS_BUTTON)
        .buildText("Login")
        .buildAttr("id", ID_LOGIN_BUTTON);
    modal.appendChild(button);
    button.addEventListener("click", function() {
        if (document.getElementById(ID_REMEMBER_ME).checked !== config.rememberMe) {
            config.logout(false, true);
            config.rememberMe = document.getElementById(ID_REMEMBER_ME).checked;
        }
        requests.makeJson(config, ACTION_LOGIN, function(loginErrMsg) {
            if (loginErrMsg) {
                document.getElementById(ID_LOGIN_ERROR).innerHTML = loginErrMsg + "<br>";
                let inputs = modal.getElementsByClassName(CLS_INPUT);
                for (let inp in inputs) {
                    if (inputs.hasOwnProperty(inp)) {
                        inputs[inp].style.borderColor = "red";
                    }
                }
                document.getElementById(ID_USERNAME).focus();
            } else {
                modal.closeModal();
                callback();
            }
        }, getLoginData(renderMFA));
    });
    bindButton(ID_USERNAME, ID_LOGIN_BUTTON);
    bindButton(ID_PASSWORD, ID_LOGIN_BUTTON);

    if (renderMFA) {
        bindButton(ID_MFA_5, ID_LOGIN_BUTTON);
    }
}

function showLoginModal(config, callback, errMsg) {
    requests.makeSimple(config, ACTION_FETCH_LOGIN_DETAILS,
        function(details) {
            renderModal(function(modal) { rendererLogin(modal, config, callback, errMsg, KEY_MFA_KEY in details); },
                false);
        }
    );
}

function onRefreshToken(config, callback) {
    requests.makeEmpty(config, config.refreshAction, callback);
}

export function formatAsTableHeader(inStr) {
    let formatted = "";
    let lastChar = "_";
    for (let i = 0; i < inStr.length; i ++) {
        let char = inStr[i];
        formatted += lastChar === "_" ? char.toUpperCase() : char;
        lastChar = char;
    }
    return formatted.replace("_", " ");
}

function findGetParameter(parameterName) {
	let result = null, tmp = [];
	location.search
		.substr(1)
		.split("&")
		.forEach(function (item) {
			tmp = item.split("=");
			if (tmp[0] === parameterName) { result = decodeURIComponent(tmp[1]); }
		});
	return result;
}

function getJaaqlUrl() {
    let jaaqlUrl = findGetParameter(PARAMETER_JAAQL);
    if (jaaqlUrl !== null) { return jaaqlUrl; }

	let callLoc = window.location.protocol;
	if (callLoc === PROTOCOL_FILE) {
		callLoc = LOCAL_DEBUGGING_URL;
	} else {
		callLoc += "/api"
	}

	return callLoc;
}

function decodeJWT(jwt) {
    let asBase64 = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    let json = decodeURIComponent(atob(asBase64).split('').map(function(char) {
        return '%' + ('00' + char.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));

    return JSON.parse(json);
}

function getJsonArrayFromStorage(storage, storageKey) {
    let storageObj = storage.getItem(storageKey);
    if (storageObj === null) {
        storageObj = {};
        storage.setItem(storageKey, JSON.stringify(storageObj));
    } else {
        storageObj = JSON.parse(storageObj);
    }
    return storageObj;
}

function getAppConfig(config, allowFromUrl = false) {
    try {
        let application = config.getApplicationName();
        let appConfig = null;
        if (allowFromUrl) {
            appConfig = findGetParameter(PARAMETER_CONFIGURATION);
        }
        let storedAppConfigs = getJsonArrayFromStorage(config.getStorage(), STORAGE_JAAQL_CONFIGS);

        if (appConfig === null) {
            let appConfigsForConfig = {};
            if (config.base in storedAppConfigs) {
                appConfigsForConfig = storedAppConfigs[config.base];
            } else {
                storedAppConfigs[config.base] = appConfigsForConfig;
            }

            if (application in appConfigsForConfig) {
                appConfig = appConfigsForConfig[application];
            } else {
                appConfigsForConfig[application] = appConfig;
            }
        } else {
            appConfig = appConfig.split(",");  //Stored as multiple JWTs, comma separated
            let configName = appConfig.shift();

            let configMap = (token) => ({[decodeJWT(token)[JWT_KEY_CONFIG_NAME]]: token});
            configMap = Object.assign({}, ...appConfig.map(configMap));
            appConfig = {};
            appConfig[KEY_NAME] = configName;
            appConfig[KEY_CONNECTIONS] = configMap;

            let appConfigsForConfig = {};
            if (config.base in storedAppConfigs) {
                appConfigsForConfig = storedAppConfigs[config.base];
            } else {
                storedAppConfigs[config.base] = appConfigsForConfig;
            }

            appConfigsForConfig[application] = appConfig;
        }
        config.getStorage().setItem(STORAGE_JAAQL_CONFIGS, JSON.stringify(storedAppConfigs));

        return appConfig;
    } catch (err) {
        // Something has gone wrong
        console.error(ERR_WIPING_CONFIG);
        console.error(err);
        console.getStorage().removeItem(STORAGE_JAAQL_CONFIGS);
    }
}

function selectAppConfig(config, callback, chosenConfig) {
    let callData = {};
    callData[KEY_APPLICATION] = config.getApplicationName();
    callData[KEY_CONFIGURATION] = chosenConfig;

    let updateStoredAppConfigs = function(config, callback, chosenConfig, connections) {
        let connectionLookup = {};
        for (let idx in connections) {
            connectionLookup[connections[idx][KEY_PARAMETER_NAME]] = connections[idx][KEY_CONNECTION];
        }

        let configObj = {};
        configObj[KEY_CONNECTIONS] = connectionLookup;
        configObj[KEY_NAME] = chosenConfig;
        let storedAppConfigs = getJsonArrayFromStorage(config.getStorage(), STORAGE_JAAQL_CONFIGS);
        storedAppConfigs[config.base][config.getApplicationName()] = configObj;
        config.getStorage().setItem(STORAGE_JAAQL_CONFIGS, JSON.stringify(storedAppConfigs));

        callback(config);
    };

    requests.makeBody(config, ACTION_CONFIGURATIONS_ARGUMENTS,
        function(connections) { updateStoredAppConfigs(config, callback, chosenConfig, connections); },
        callData);
}

function resetAppConfig(config, afterSelectAppConfig = null) {
    if (afterSelectAppConfig === null) {
        afterSelectAppConfig = function() {
            console.error(ERR_IMPERATIVE_APP_CONFIG_FAILED);
        };
    }

    let data = {};
    data[KEY_APPLICATION] = config.getApplicationName();
    requests.makeBody(config, ACTION_CONFIGURATIONS,
        function (data) {
            renderSelectAppConfig(config, afterSelectAppConfig, data);
        },
        data);
}

export function getOrSelectAppConfig(config, afterSelectAppConfig = null, allowFromUrl = false,
                                     preventRecursion = false) {
    let appConfig = getAppConfig(config, allowFromUrl);

    if (appConfig !== null && appConfig.constructor === Object && KEY_CONNECTIONS in appConfig &&
        KEY_NAME in appConfig) {
        if (afterSelectAppConfig !== null) {
            afterSelectAppConfig(config);
            return;
        } else {
            return appConfig;
        }
    }

    if (!preventRecursion) {
        resetAppConfig(config, afterSelectAppConfig);
    }

    let fallback = {};
    fallback[KEY_CONNECTIONS] = {};
    fallback[KEY_NAME] = null;
    return fallback;
}

function storeJEQLDataToElement(elem, data) {
    elem.setAttribute(ATTR_JEQL_DATA, btoa(JSON.stringify(data)));
}

function extractJEQLDataFromElement(elem) {
    return JSON.parse(atob(elem.getAttribute(ATTR_JEQL_DATA)));
}

function renderSelectAppConfig(config, callback, data) {
    if (data.length === 1) {
        selectAppConfig(config, callback, data[0][KEY_CONFIGURATION])
    } else if (data.length === 0) {
        console.error(ERR_NO_FOUND_CONFIGURATION_FOR_USER);
    } else {
        renderModal(function (modal) {
            let curAppConfig = getOrSelectAppConfig(config, null, false, true)[KEY_NAME];

            modal.appendChild(elemBuilder("h1").buildText("Select Configuration"));
            let table = elemBuilder("table");
            modal.appendChild(table);
            let header = table.buildChild("tr");
            for (let idx in Object.keys(data[0])) {
                header.buildChild("th").buildText(formatAsTableHeader(Object.keys(data[0])[idx]));
            }
            header.buildChild("th");
            for (let idx in data) {
                let row = table.buildChild("tr");
                if (data[idx][KEY_CONFIGURATION] === curAppConfig) {
                    row.buildClass(CLS_SELECTED_APP_CONFIG);
                }
                for (let key in data[idx]) {
                    row.buildChild("td").buildText(data[idx][key]);
                }
                row.buildChild("td").buildHTML(`
                    <button id="${ID_SELECT_APP_CONFIG + idx}" class="${CLS_BUTTON}">Select</button>
                `);
                storeJEQLDataToElement(document.getElementById(ID_SELECT_APP_CONFIG + idx), data[idx]);
                document.getElementById(ID_SELECT_APP_CONFIG + idx).addEventListener("click", function (event) {
                    modal.closeModal();
                    selectAppConfig(config, callback, extractJEQLDataFromElement(event.target)[KEY_CONFIGURATION]);
                });
            }
        }, false, CLS_MODAL_WIDE);
    }
}

function renderAccountBanner(config) {
    // TODO render something that allows you to select configurations and access the account app
}

export function initAsPublic() {
    // TODO initialise with supplied credentials, do not render account banner
}

export function getAppUrl(config, appName) {
    let data = {};
    data[KEY_SEARCH] = `%${KEY_APPLICATION} LIKE '%${appName}'`;
    requests.makeBody(config, ACTION_FETCH_APPLICATIONS,
        function(data) {
            data = data[KEY_DATA];
            for (let idx in data) {
                if (data[idx][KEY_NAME] === appName) {
                    return data[idx][KEY_URL];
                }
            }
            throw ERR_COULD_NOT_FIND_APPLICATION_WITH_NAME + `'${appName}'`;
        },
    );
}

export function init(application, onLoad, doRenderAccountBanner = true, jaaqlUrl = null) {
    if (onLoad === null) { onLoad = function() {  }; }
    if (jaaqlUrl === null) { jaaqlUrl = getJaaqlUrl(); }

    let setAuthTokenFunc = function(storage, authToken) {
        let jaaqlTokens = getJsonArrayFromStorage(storage, STORAGE_JAAQL_TOKENS);
        jaaqlTokens[jaaqlUrl] = authToken;
        storage.setItem(STORAGE_JAAQL_TOKENS, JSON.stringify(jaaqlTokens));
    };
    let logoutFunc = function(storage, doReload, doCopy, invertedStorage) {
        if (doCopy) {
            invertedStorage.setItem(STORAGE_JAAQL_TOKENS, storage.getItem(STORAGE_JAAQL_TOKENS));
            invertedStorage.setItem(STORAGE_JAAQL_CONFIGS, storage.getItem(STORAGE_JAAQL_CONFIGS));
        }
        storage.removeItem(STORAGE_JAAQL_TOKENS);
        storage.removeItem(STORAGE_JAAQL_CONFIGS);
        if (doReload) {
            window.location.reload();
        }
    };
    let config = new requests.RequestConfig(application, jaaqlUrl, ACTION_LOGIN, ACTION_REFRESH, showLoginModal,
        onRefreshToken, xHttpSetAuth, setAuthTokenFunc, logoutFunc);
    config.rememberMe = window.localStorage.getItem(STORAGE_JAAQL_TOKENS) !== null;

    let jaaqlTokens = getJsonArrayFromStorage(config.getStorage(), STORAGE_JAAQL_TOKENS);
    let authToken = null;
    if (config.base in jaaqlTokens) {
        authToken = jaaqlTokens[config.base];
    }
    config.authToken = authToken;

    if (doRenderAccountBanner) {
        renderAccountBanner(config);
    }

    getOrSelectAppConfig(config, onLoad, true);

    return config;
}

function fetchConnection(config, appParameter = null) {
    let appConfig = getOrSelectAppConfig(config)[KEY_CONNECTIONS];

    if (appParameter === null) {
        if (Object.keys(appConfig).length > 1) {
            throw new Error("Must supply parameter as multiple parameters exist");
        } else if (appConfig.length === 0) {
            resetAppConfig(config);
        }
        return appConfig[Object.keys(appConfig)[0]];
    } else {
        if (appParameter in appConfig) {
            return appConfig[appParameter];
        } else {
            throw new Error("Parameter '" + appParameter + " does not exist");
        }
    }
}

function callbackDoNotRefreshConnections(res, config) {
    resetAppConfig(config, function() { console.error(ERR_COULD_NOT_REFRESH_APP_CONFIG); })
}

function expiredConnectionHandler(res, config, action, renderFunc, body, json) {
    let appConfig = getOrSelectAppConfig(config);
    let reverseMap = {};
    for (let idx in appConfig[KEY_CONNECTIONS]) {
        reverseMap[appConfig[KEY_CONNECTIONS][idx]] = idx;
    }

    selectAppConfig(config,
        function() {
            let newAppConfig = getOrSelectAppConfig(config);
            if (json) {
                json = JSON.parse(json);
            } else {
                json = requests.urlEncodedToJson(body);
            }

            let wasArray = true;
            if (!Array.isArray(json)) {
                wasArray = false;
                json = [json];
            }

            for (let idx in json) {
                json[idx][KEY_CONNECTION] = newAppConfig[KEY_CONNECTIONS][reverseMap[json[idx][KEY_CONNECTION]]];
            }

            if (!wasArray) {
                json = json[0];
            }

            if (body) {
                body = requests.jsonToUrlEncoded(json);
                json = undefined;
            }

            let newRenderFuncs = {...renderFunc};
            newRenderFuncs[HTTP_STATUS_CONNECTION_EXPIRED] = callbackDoNotRefreshConnections;

            requests.make(config, action, newRenderFuncs, body, json);
        },
        appConfig[KEY_NAME]);
}

export function formQuery(config, query, queryParameters = null, appParameter = null, database = null) {
    let connection = fetchConnection(config, appParameter);

    if (queryParameters === null) { queryParameters = {}; }

    let formed = {};
    formed[KEY_QUERY] = query;
    formed[KEY_PARAMETERS] = queryParameters;
    formed[KEY_CONNECTION] = connection;
    formed[KEY_DATABASE] = database;
    return formed;
}

export function submit(config, input, renderFunc, doNotRefresh = false, asFile = false) {
    let oldRenderFunc = renderFunc;
    if (renderFunc.constructor !== Object) {
        renderFunc = {};
        renderFunc[HTTP_STATUS_OK] = oldRenderFunc;
    }
    renderFunc[HTTP_STATUS_CONNECTION_EXPIRED] = doNotRefresh ?
        callbackDoNotRefreshConnections :
        expiredConnectionHandler;
    requests.makeJson(config, asFile ? ACTION_SUBMIT_FILE : ACTION_SUBMIT, renderFunc, input);
}

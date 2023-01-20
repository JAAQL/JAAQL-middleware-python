let APPLICATION_NAME = "console";

let COMMAND_START = "/";
let COMMAND_CLEAR = "clear";
let COMMAND_CLEARHIS = "clearhis";
let COMMAND_TOGGLEREAD = "toggleread";
let COMMAND_LOGOUT = "logout";
let COMMAND_SWITCH = "switch";
let COMMAND_FILE = "file";
let COMMAND_HELP = "help";

let ID_CONSOLE_SQL_FILE = "console-sql-file";

let HISTORY_IDX = "idx";
let HISTORY_LIST = "list";
let HISTORY_HAS_TEMP = "has_temp";

let CLS_LINE_TEXT_CONTAINER = "line-text-container";
let CLS_LINE_TEXT_PARENT = "line-text-parent";

let STORAGE_CONSOLE_HISTORY = "APP_CONSOLE_HISTORY";
let STORAGE_CUR_DB = "CUR_DB";

let DEFAULT_DB = "jaaql";

function textAreaAutoResize() {
    this.style.height = "auto";
    this.style.height = (this.scrollHeight) + "px";
}

function renderConsoleLine(newLine, db_name) {
    let lineTextContainer = document.createElement("div");
    newLine.appendChild(lineTextContainer);
    lineTextContainer.setAttribute("class", CLS_LINE_TEXT_CONTAINER);
    lineTextContainer.innerHTML = "<span>" + new Date().toISOString() + "</span> DB=" +
        (db_name == null ? "_" : db_name) + ">&nbsp;";
    let lineInput = document.createElement("textarea");
    newLine.appendChild(lineInput);
    lineInput.setAttribute("class", "line_input");
    lineInput.setAttribute("autofocus", true);
    lineInput.setAttribute("style",  "height:1em;overflow-y:hidden;");
    lineInput.addEventListener("input", textAreaAutoResize, false);
    lineInput.setAttribute("rows", 1);
    window.lineInput = lineInput;
    window.lineTextContainer = lineTextContainer;
    window.newLine = newLine;
    window.lineInput.focus();
    window.wasConsole = null;
    window.lineInput.addEventListener("keyup", function(event) {
        if (event.which === 38 || event.which === 40) { return; }
        window.wasConsole = false;
        let history = getHistory(window.JEQL__REQUEST_HELPER);
        let historyList = history[HISTORY_LIST];
        if (window.curHistoryLine === historyList.length - 1 && history[HISTORY_HAS_TEMP]) {
            let isEmpty = window.lineInput.value.length === 0;
            history[HISTORY_HAS_TEMP] = !isEmpty;
            historyList.pop();
            if (!isEmpty) {
                historyList.push(window.lineInput.value);
            } else {
                window.curHistoryLine -= 1;
            }
            updateHistory(window.JEQL__REQUEST_HELPER, history);
        }
    });
}

function addConsoleLine(config) {
    let existing = document.getElementById("console");
    let newLine = document.createElement("div");
    newLine.classList.add(CLS_LINE_TEXT_PARENT);
    existing.appendChild(newLine);
    renderConsoleLine(newLine, window.curDatabase);
    window.curHistoryLine = getHistory(config)[HISTORY_IDX];
}

function processUpDownKey(history, historyList) {
    if (historyList.length !== 1 || window.lineInput.value === "") {
        if (window.lineInput.value.length !== 0 && !window.wasConsole && !history[HISTORY_HAS_TEMP]) {
            historyList.push(window.lineInput.value);
            history[HISTORY_HAS_TEMP] = true;
            updateHistory(window.JEQL__REQUEST_HELPER, history);
        }
        window.lineInput.value = historyList[window.curHistoryLine];
        window.lineInput.setSelectionRange(window.lineInput.value.length, window.lineInput.value.length);
        window.wasConsole = true;
    }
}

function keyDownBody(e) {
    if (JEQL.modalExists()) { return; }
    window.lineInput.focus();
    if (window.curHistoryLine !== null) {
        let history = getHistory(window.JEQL__REQUEST_HELPER);
        let historyList = history[HISTORY_LIST];
        if (e.which === 38 && (window.curHistoryLine > 0 || historyList.length === 1 ||
            window.lineInput.value === "")) {
            if ((historyList.length !== 1 && window.wasConsole && window.lineInput.value.length !== 0) ||
                (history[HISTORY_HAS_TEMP] && !window.wasConsole)) {
                window.curHistoryLine -= 1;
            }
            processUpDownKey(history, historyList);
        } else if (e.which === 40 && (window.curHistoryLine < historyList.length - 1 || historyList.length === 1 ||
            window.lineInput.value === "")) {
            if (historyList.length !== 1 && window.wasConsole && window.lineInput.value.length !== 0) {
                window.curHistoryLine += 1;
            }
            processUpDownKey(history, historyList);
        }
    }
}

function renderResponse(data, isErr = false) {
    addConsoleLine(window.JEQL__REQUEST_HELPER);
    window.lineInput.value = JSON.stringify(data);
    window.lineInput.style.height = "auto";
    window.lineInput.style.height = (window.lineInput.scrollHeight) + "px";
    if (isErr) {
        window.lineInput.style.color = "red";
    }
    addConsoleLine(window.JEQL__REQUEST_HELPER);
}

function getDefaultResponseHandler() {
    let responseHandlers = {};
    responseHandlers[JEQL_REQUESTS.HTTP_STATUS_DEFAULT] = function(data) { renderResponse(data, true); };
    responseHandlers[JEQL_REQUESTS.HTTP_STATUS_OK] = renderResponse;
    return responseHandlers;
}

function readAndSubmitFile(config, file) {
    let reader = new FileReader();
    config.createSpinner();
    reader.onload = readerEvent => {
        config.destroySpinner();

        let query = {};
        query[JEQL.KEY_QUERY] = readerEvent.target.result;
        if (window.curDatabase !== DEFAULT_DB) {
            query[JEQL.KEY_DATABASE] = window.curDatabase;
        }
        JEQL.submit(
            query,
            getDefaultResponseHandler()
        );
    };
    reader.readAsText(file);
}

function handleFileInput(requestHelper, filePath = null) {
    if (filePath === null) {
        let fileInput = document.getElementById(ID_CONSOLE_SQL_FILE);
        fileInput.value = "";
        fileInput.onchange = f => {
            let file = f.target.files[0];
            fileInput.onchange = function() {};
            readAndSubmitFile(requestHelper, file);
        };
        fileInput.click();
    } else {
        readAndSubmitFile(requestHelper, filePath);
    }
}

function onSendConsole() {
    let consoleInput = window.lineInput.value.trimEnd();
    if (window.lineInput.value === "") { return; }

    let history = getHistory(window.JEQL__REQUEST_HELPER);
    if (history[HISTORY_HAS_TEMP]) {
        history[HISTORY_LIST].pop();
    }
    if (history[HISTORY_LIST].length === 0 ||
        history[HISTORY_LIST][history[HISTORY_LIST].length - 1] !== window.lineInput.value.trim()) {
        history[HISTORY_LIST].push(window.lineInput.value.trim());
    }
    if (window.wasConsole) {
        history[HISTORY_IDX] = window.curHistoryLine;
    } else {
        history[HISTORY_IDX] = history[HISTORY_LIST].length - 1;
    }
    updateHistory(window.JEQL__REQUEST_HELPER, history);

    if (consoleInput.startsWith(COMMAND_START)) {
        if (consoleInput === COMMAND_START + COMMAND_HELP) {
            addConsoleLine(window.JEQL__REQUEST_HELPER);
            window.lineInput.parentElement.innerHTML = document.getElementById("welcomeText").innerHTML;
            window.lineInput.remove();
            addConsoleLine(window.JEQL__REQUEST_HELPER);
        } else if (consoleInput === COMMAND_START + COMMAND_LOGOUT) {
            window.JEQL__REQUEST_HELPER.logout();
        } else if (consoleInput.split(" ")[0] === COMMAND_START + COMMAND_SWITCH) {
            updateCurDb(window.JEQL__REQUEST_HELPER, consoleInput.split(COMMAND_START + COMMAND_SWITCH + " ")[1].trim());
            addConsoleLine(window.JEQL__REQUEST_HELPER);
        } else if (consoleInput === COMMAND_START + COMMAND_CLEAR) {
            let allLines = Array.from(document.getElementsByClassName(CLS_LINE_TEXT_PARENT));
            allLines.forEach(line => {
                line.remove();
            });
            addConsoleLine(window.JEQL__REQUEST_HELPER);
            window.lineInput.value = COMMAND_START + COMMAND_CLEAR;
            addConsoleLine(window.JEQL__REQUEST_HELPER);
        } else if (consoleInput === COMMAND_START + COMMAND_CLEARHIS) {
            addConsoleLine(window.JEQL__REQUEST_HELPER);
            window.lineInput.value = "History cleared";
            window.JEQL__REQUEST_HELPER.getStorage().removeItem(STORAGE_CONSOLE_HISTORY);
            window.wasConsole = null;
            getHistory(window.JEQL__REQUEST_HELPER);
            addConsoleLine(window.JEQL__REQUEST_HELPER);
        } else if (consoleInput === COMMAND_START + COMMAND_TOGGLEREAD) {
            addConsoleLine(window.JEQL__REQUEST_HELPER);
            window.lineInput.value = "Read only is " + (window.READ_ONLY ? "off" : "on");
            addConsoleLine(window.JEQL__REQUEST_HELPER);
            window.READ_ONLY = !window.READ_ONLY;
        } else if (consoleInput.split(" ")[0] === COMMAND_START + COMMAND_FILE) {
            if (consoleInput.trim().split(" ").length === 1) {
                handleFileInput(window.JEQL__REQUEST_HELPER);
            } else {
                let fileName = consoleInput.trim().split(" ").shift();
                handleFileInput(window.JEQL__REQUEST_HELPER, fileName.join(" "));
            }
        } else {
            addConsoleLine(window.JEQL__REQUEST_HELPER);
            window.lineInput.value = "Unknown console command: '" + consoleInput.substr(1) + "'";
            window.lineInput.style.color = "red";
            addConsoleLine(window.JEQL__REQUEST_HELPER);
        }
    } else {
        let query = {};
        query[JEQL.KEY_QUERY] = window.lineInput.value;
        if (window.curDatabase !== DEFAULT_DB) {
            query[JEQL.KEY_DATABASE] = window.curDatabase;
        }
        if (window.READ_ONLY) {
            query[JEQL.KEY_READ_ONLY] = true;
        }
        JEQL.submit(
            query,
            getDefaultResponseHandler()
        );
    }
}

function keyPressBody(e) {
    if (JEQL.modalExists()) { return; }
    if (e.which === 13 && !e.shiftKey) {
        window.newLine.getElementsByTagName("span")[0].innerText = new Date().toISOString();
        window.lineInput.setAttribute("readonly", "readonly");
        onSendConsole();
    }
}

function updateHistory(requestHelper, history) {
    requestHelper.getStorage().setItem(STORAGE_CONSOLE_HISTORY, JSON.stringify(history));
}

function getHistory(requestHelper) {
    let history = requestHelper.getStorage().getItem(STORAGE_CONSOLE_HISTORY);
    if (!history) {
        history = {};
        history[HISTORY_IDX] = null;
        history[HISTORY_LIST] = [];
        history[HISTORY_HAS_TEMP] = false;
        updateHistory(requestHelper, history);
    } else {
        history = JSON.parse(history);
    }
    return history;
}

function updateCurDb(requestHelper, db) {
    requestHelper.getStorage().setItem(STORAGE_CUR_DB, db);
    window.curDatabase = db;
}

function loadCurDb(requestHelper) {
    let curDb = requestHelper.getStorage().getItem(STORAGE_CUR_DB);
    if (!curDb) {
        curDb = DEFAULT_DB;
        updateCurDb(requestHelper, curDb);
    }
    return curDb;
}

function init(requestHelper) {
    loadCurDb(requestHelper);

    if (requestHelper.rememberMe) {
        window.sessionStorage.removeItem(STORAGE_CONSOLE_HISTORY);
    } else {
        window.localStorage.removeItem(STORAGE_CONSOLE_HISTORY);
    }

    document.addEventListener("keydown", keyDownBody, false);
    document.addEventListener("keypress", keyPressBody, false);

    addConsoleLine(requestHelper);
}

window.onload = function() {
    window.READ_ONLY = false;
    JEQL.init(APPLICATION_NAME, null, init);
};

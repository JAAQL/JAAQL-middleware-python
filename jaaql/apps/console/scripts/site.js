import * as JEQL from "../../JEQL/JEQL.js"

let APPLICATION_NAME = "console";

let COMMAND_START = "/";
let COMMAND_CLEAR = "clear";
let COMMAND_CLEARHIS = "clearhis";
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
        let history = getHistory(window.JEQL_CONFIG);
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
            updateHistory(window.JEQL_CONFIG, history);
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
            updateHistory(window.JEQL_CONFIG, history);
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
        let history = getHistory(window.JEQL_CONFIG);
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
    addConsoleLine(window.JEQL_CONFIG);
    window.lineInput.value = JSON.stringify(data);
    window.lineInput.style.height = "auto";
    window.lineInput.style.height = (window.lineInput.scrollHeight) + "px";
    if (isErr) {
        window.lineInput.style.color = "red";
    }
    addConsoleLine(window.JEQL_CONFIG);
}

function getDefaultResponseHandler() {
    let responseHandlers = {};
    responseHandlers[JEQL.HTTP_STATUS_DEFAULT] = function(data) { renderResponse(data, true); };
    responseHandlers[JEQL.HTTP_STATUS_OK] = renderResponse;
    return responseHandlers;
}

function readAndSubmitFile(config, file) {
    let reader = new FileReader();
    config.createSpinner();
    reader.onload = readerEvent => {
        config.destroySpinner();
        let content = readerEvent.target.result;
        let formedQuery = JEQL.formQuery(config, content, null, null, window.curDatabase);
        JEQL.submitFile(
            config,
            formedQuery,
            getDefaultResponseHandler()
        );
    };
    reader.readAsText(file);
}

function handleFileInput(config, filePath = null) {
    if (filePath === null) {
        let fileInput = document.getElementById(ID_CONSOLE_SQL_FILE);
        fileInput.value = "";
        fileInput.onchange = f => {
            let file = f.target.files[0];
            fileInput.onchange = function() {};
            readAndSubmitFile(config, file);
        };
        fileInput.click();
    } else {
        readAndSubmitFile(config, filePath);
    }
}

function onSendConsole() {
    let consoleInput = window.lineInput.value.trimEnd();
    if (window.lineInput.value === "") { return; }

    let history = getHistory(window.JEQL_CONFIG);
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
    updateHistory(window.JEQL_CONFIG, history);

    if (consoleInput.startsWith(COMMAND_START)) {
        if (consoleInput === COMMAND_START + COMMAND_HELP) {
            addConsoleLine(window.JEQL_CONFIG);
            window.lineInput.parentElement.innerHTML = document.getElementById("welcomeText").innerHTML;
            window.lineInput.remove();
            addConsoleLine(window.JEQL_CONFIG);
        } else if (consoleInput === COMMAND_START + COMMAND_LOGOUT) {
            window.JEQL_CONFIG.logout();
        } else if (consoleInput.split(" ")[0] === COMMAND_START + COMMAND_SWITCH) {
            updateCurDb(window.JEQL_CONFIG, consoleInput.split(COMMAND_START + COMMAND_SWITCH + " ")[1].trim());
            addConsoleLine(window.JEQL_CONFIG);
        } else if (consoleInput === COMMAND_START + COMMAND_CLEAR) {
            let allLines = Array.from(document.getElementsByClassName(CLS_LINE_TEXT_PARENT));
            allLines.forEach(line => {
                line.remove();
            });
            addConsoleLine(window.JEQL_CONFIG);
            window.lineInput.value = COMMAND_START + COMMAND_CLEAR;
            addConsoleLine(window.JEQL_CONFIG);
        } else if (consoleInput === COMMAND_START + COMMAND_CLEARHIS) {
            addConsoleLine(window.JEQL_CONFIG);
            window.lineInput.value = "History cleared";
            window.JEQL_CONFIG.getStorage().removeItem(STORAGE_CONSOLE_HISTORY);
            window.wasConsole = null;
            getHistory(window.JEQL_CONFIG);
            addConsoleLine(window.JEQL_CONFIG);
        } else if (consoleInput.split(" ")[0] === COMMAND_START + COMMAND_FILE) {
            if (consoleInput.trim().split(" ").length === 1) {
                handleFileInput(window.JEQL_CONFIG);
            } else {
                let fileName = consoleInput.trim().split(" ").shift();
                handleFileInput(window.JEQL_CONFIG, fileName.join(" "));
            }
        } else {
            addConsoleLine(window.JEQL_CONFIG);
            window.lineInput.value = "Unknown console command: '" + consoleInput.substr(1) + "'";
            window.lineInput.style.color = "red";
            addConsoleLine(window.JEQL_CONFIG);
        }
    } else {
        JEQL.submit(
            window.JEQL_CONFIG,
            JEQL.formQuery(window.JEQL_CONFIG, window.lineInput.value, null, null, window.curDatabase),
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

function updateHistory(config, history) {
    config.getStorage().setItem(STORAGE_CONSOLE_HISTORY, JSON.stringify(history));
}

function getHistory(config) {
    let history = config.getStorage().getItem(STORAGE_CONSOLE_HISTORY);
    if (!history) {
        history = {};
        history[HISTORY_IDX] = null;
        history[HISTORY_LIST] = [];
        history[HISTORY_HAS_TEMP] = false;
        updateHistory(config, history);
    } else {
        history = JSON.parse(history);
    }
    return history;
}

function updateCurDb(config, db) {
    config.getStorage().setItem(STORAGE_CUR_DB, db);
    window.curDatabase = db;
}

function loadCurDb(config) {
    let curDb = config.getStorage().getItem(STORAGE_CUR_DB);
    if (!curDb) {
        curDb = DEFAULT_DB;
        updateCurDb(config, curDb);
    }
    return curDb;
}

function init(config) {
    loadCurDb(config);

    if (config.rememberMe) {
        window.sessionStorage.removeItem(STORAGE_CONSOLE_HISTORY);
    } else {
        window.localStorage.removeItem(STORAGE_CONSOLE_HISTORY);
    }

    document.addEventListener("keydown", keyDownBody, false);
    document.addEventListener("keypress", keyPressBody, false);
    addConsoleLine(config);
}

window.onload = function() {
    JEQL.init(APPLICATION_NAME, init);
};

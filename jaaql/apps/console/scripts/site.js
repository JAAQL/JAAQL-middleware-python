import * as JEQL from "../../JEQL/JEQL.js"

let APPLICATION_NAME = "console";

let COMMAND_START = "/";
let COMMAND_LIST = "list";
let COMMAND_CLEAR = "clear";
let COMMAND_CLEARHIS = "clearhis";
let COMMAND_LOGOUT = "logout";
let COMMAND_SWITCH = "switch";
let COMMAND_REFRESH = "refresh";
let COMMAND_FILE = "file";
let COMMAND_HELP = "help";

let HISTORY_IDX = "idx";
let HISTORY_LIST = "list";
let HISTORY_USED_CONSOLE = "used_console";

let CLS_LINE_TEXT_CONTAINER = "line-text-container";
let CLS_LINE_TEXT_PARENT = "line-text-parent";

let STORAGE_CONSOLE_HISTORY = "APP_CONSOLE_HISTORY";

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
    window.lineInput.addEventListener("change", function() {
        window.wasConsole = false;
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

function keyDownBody(e) {
    window.lineInput.focus();
    if (window.curHistoryLine !== null) {
        let historyList = getHistory(window.jeqlConfig)[HISTORY_LIST];
        if (e.which === 38 && (window.curHistoryLine > 0 || historyList.length === 1 ||
            window.lineInput.value === "")) {
            if (historyList.length !== 1 && window.wasConsole !== null) {
                window.curHistoryLine -= 1;
            }
            if (historyList.length !== 1 || window.lineInput.value === "") {
                window.lineInput.value = historyList[window.curHistoryLine];
                window.wasConsole = true;
            }
        } else if (e.which === 40 && (window.curHistoryLine < historyList.length - 1 || historyList.length === 1 ||
            window.lineInput.value === "")) {
            if (historyList.length !== 1 && window.wasConsole !== null) {
                window.curHistoryLine += 1;
            }
            if (historyList.length !== 1 || window.lineInput.value === "") {
                window.lineInput.value = historyList[window.curHistoryLine];
                window.wasConsole = true;
            }
        }
    }
}

function renderResponse(data, isErr = false) {
    addConsoleLine(window.jeqlConfig);
    window.lineInput.value = JSON.stringify(data);
    window.lineInput.style.height = "auto";
    window.lineInput.style.height = (window.lineInput.scrollHeight) + "px";
    if (isErr) {
        window.lineInput.style.color = "red";
    }
    addConsoleLine(window.jeqlConfig);
}

function onSendConsole() {
    let consoleInput = window.lineInput.value.trimEnd();
    if (window.lineInput.value === "") { return; }

    let history = getHistory(window.jeqlConfig);
    history[HISTORY_LIST].push(window.lineInput.value);
    if (window.wasConsole) {
        history[HISTORY_IDX] = window.curHistoryLine;
        history[HISTORY_USED_CONSOLE] = true;
    } else if (history[HISTORY_USED_CONSOLE] === false) {
        history[HISTORY_IDX] = history[HISTORY_LIST].length - 1;
    }
    updateHistory(window.jeqlConfig, history);

    if (consoleInput.startsWith(COMMAND_START)) {
        if (consoleInput === COMMAND_START + COMMAND_HELP) {
            addConsoleLine(window.jeqlConfig);
            window.lineInput.parentElement.innerHTML = document.getElementById("welcomeText").innerHTML;
            window.lineInput.remove();
            addConsoleLine(window.jeqlConfig);
        } else if (consoleInput === COMMAND_START + COMMAND_LOGOUT) {
            window.jeqlConfig.logout();
        } else if (consoleInput.startsWith(COMMAND_START + COMMAND_SWITCH)) {
            window.curDatabase = consoleInput.split(COMMAND_START + COMMAND_SWITCH + " ")[1].trim();
            addConsoleLine(window.jeqlConfig);
        } else if (consoleInput === COMMAND_START + COMMAND_LIST) {
            JEQL.getConnectionDatabases(window.jeqlConfig, renderResponse);
        } else if (consoleInput === COMMAND_START + COMMAND_CLEAR) {
            let allLines = Array.from(document.getElementsByClassName(CLS_LINE_TEXT_PARENT));
            allLines.forEach(line => {
                line.remove();
            });
            addConsoleLine(window.jeqlConfig);
            window.lineInput.value = COMMAND_START + COMMAND_CLEAR;
            addConsoleLine(window.jeqlConfig);
        } else if (consoleInput === COMMAND_START + COMMAND_CLEARHIS) {
            addConsoleLine(window.jeqlConfig);
            window.lineInput.value = "History cleared";
            window.jeqlConfig.getStorage().removeItem(STORAGE_CONSOLE_HISTORY);
            window.wasConsole = null;
            getHistory(window.jeqlConfig);
            addConsoleLine(window.jeqlConfig);
        } else if (consoleInput === COMMAND_START + COMMAND_REFRESH) {
            let renderFuncs = {};
            renderFuncs[JEQL.HTTP_STATUS_OK] = function() {
                addConsoleLine(window.jeqlConfig);
                window.lineInput.value = "Databases Refreshed";
                addConsoleLine(window.jeqlConfig);
            };
            renderFuncs[JEQL.HTTP_STATUS_DEFAULT] = function(data) { renderResponse(data, true); };
            JEQL.updateConnectionDatabases(window.jeqlConfig, renderFuncs);
        } else if (consoleInput === COMMAND_START + COMMAND_FILE) {
            // TODO
        } else {
            addConsoleLine(window.jeqlConfig);
            window.lineInput.value = "Unknown console command: '" + consoleInput.substr(1) + "'";
            window.lineInput.style.color = "red";
            addConsoleLine(window.jeqlConfig);
        }
    } else {
        let responseHandlers = {};
        responseHandlers[JEQL.HTTP_STATUS_DEFAULT] = function(data) { renderResponse(data, true); };
        responseHandlers[JEQL.HTTP_STATUS_OK] = renderResponse;

        JEQL.submit(
            window.jeqlConfig,
            JEQL.formQuery(window.jeqlConfig, window.lineInput.value, null, null, window.curDatabase),
            responseHandlers
        );
    }
}

function keyPressBody(e) {
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
        history[HISTORY_USED_CONSOLE] = false;
        updateHistory(config, history);
    } else {
        history = JSON.parse(history);
    }
    return history;
}

function init(config) {
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
    window.jeqlConfig = JEQL.init(APPLICATION_NAME, init);
    window.curDatabase = null;
};

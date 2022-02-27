import * as JEQL from "../../JEQL/JEQL.js"

let APPLICATION_NAME = "console";
let COMMAND_START = "/";
let COMMAND_LIST = "list";
let COMMAND_SWITCH = "switch";
let COMMAND_FILE = "file";
let COMMAND_HELP = "help";

function textAreaAutoResize() {
    this.style.height = "auto";
    this.style.height = (this.scrollHeight) + "px";
}

function renderConsoleLine(newLine, db_name) {
    let lineTextContainer = document.createElement("div");
    newLine.appendChild(lineTextContainer);
    lineTextContainer.setAttribute("class", "line-text-container");
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
}

function addConsoleLine() {
    let existing = document.getElementById("console");
    let newLine = document.createElement("div");
    existing.appendChild(newLine);
    renderConsoleLine(newLine, window.cur_database);
}

function keyDownBody(e) {
    window.lineInput.focus();
}

function renderResponse(data) {
    addConsoleLine();
    window.lineInput.value = JSON.stringify(data);
    window.lineInput.style.height = "auto";
    window.lineInput.style.height = (window.lineInput.scrollHeight) + "px";
    addConsoleLine();
}

function onSendConsole() {
    let consoleInput = window.lineInput.value;

    if (consoleInput.startsWith(COMMAND_START + COMMAND_HELP)) {
        // TODO
    } else if (consoleInput.startsWith(COMMAND_START + COMMAND_SWITCH)) {
        window.cur_database = consoleInput.split(COMMAND_START + COMMAND_SWITCH + " ")[1].trim();
        addConsoleLine();
    } else if (consoleInput.startsWith(COMMAND_START + COMMAND_LIST)) {
        JEQL.getConnectionDatabases(window.jeql_config, renderResponse);
    } else if (consoleInput.startsWith(COMMAND_START + COMMAND_FILE)) {
        // TODO
    } else {
        JEQL.submit(
            window.jeql_config,
            JEQL.formQuery(window.jeql_config, window.lineInput.value, null, null, window.cur_database),
            renderResponse
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

function init() {
    document.addEventListener("keydown", keyDownBody, false);
    document.addEventListener("keypress", keyPressBody, false);
    addConsoleLine();
}

window.onload = function() {
    window.jeql_config = JEQL.init(APPLICATION_NAME, init);
    window.cur_database = null;
};

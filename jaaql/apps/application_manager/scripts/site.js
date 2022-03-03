import * as JEQL from "../../JEQL/JEQL.js"

let APPLICATION_NAME = "Application Creator";

function onSubmit(config) {
    let createDatabase = function() {

    };
    JEQL.requests.makeJson(config, "POST /internal/applications", function() {

    });
}

function onload(config) {

}

window.onload = function() {
    window.jeqlConfig = JEQL.init(APPLICATION_NAME, init);
};

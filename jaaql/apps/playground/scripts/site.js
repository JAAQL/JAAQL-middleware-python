import * as JEQL from "../../JEQL/JEQL.js"

let APPLICATION_NAME = "playground";
let QUERY_APPLICATIONS = "SELECT * FROM jaaql__application"

function init() {
    let baseTable = JEQL.makeBuildable(document.getElementById("example-table"));
    
    let introFunc = function(columns) {
        baseTable.buildChild("thead").buildRow().buildForeach(columns, column => `<th>${column}</th>`);
        return baseTable.buildChild("tbody");
    };
    
    JEQL.render(
        JEQL.formQuery(window.JEQL_CONFIG, QUERY_APPLICATIONS),
        {
            introducer: introFunc,
            expression: function(row, body) {
                body.buildRow().buildForeach(row, cell => `<td>${cell}</td>`);
            },
            separator: function(row, body) {
                body.buildRow().buildForeach(row, cell => `<td style="background: grey">&nbsp;</td>`);
            },
            terminator: function(columns, body) {
                body.buildRow().buildForeach(columns, column => `<th style="background: green">${column}</th>`);
            },
            alternative: function(columns) {
                introFunc(columns).buildRow().buildText("There are no applications");
            }
        }
    );
}

window.onload = function() {
    JEQL.init(APPLICATION_NAME, init);
};

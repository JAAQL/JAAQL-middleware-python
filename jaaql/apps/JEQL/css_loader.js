function genStyleSheetEle(href, id) {
    let link = document.createElement("link");
    link.rel = "stylesheet";
    link.type = "text/css";
    link.href = href;
    link.id = id;
    return link;
}

function genFont(href, id) {
    let link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.id = id;
    return link;
}

function appendIfNoExist(parent, toAppend) {
    if (document.getElementById(toAppend.id) === null) {
        parent.appendChild(toAppend);
    }
}

function loadStyleSheets() {
    let baseDir = "";
    if (window.location.protocol === "file:") {
        baseDir = "../JEQL/";
    } else {
        baseDir = "/apps/JEQL/";
    }

    let head = document.getElementsByTagName("head")[0];

    appendIfNoExist(
        head,
        genFont(
            "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap",
            "jeql_css_font"
        )
    );

    appendIfNoExist(head, genStyleSheetEle(baseDir + "JEQL.css", "jeql_css_main"));
    appendIfNoExist(head, genStyleSheetEle(baseDir + "spinner/spinner.css", "jeql_css_spinner"));

}

loadStyleSheets();

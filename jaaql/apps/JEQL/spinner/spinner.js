import "../css_loader.js"  // Will import the CSS

export function createSpinner() {
    let spinner = document.createElement("div");
    spinner.setAttribute("class", "jeql-spinner-outer");
    let subSpinner = document.createElement("div");
    subSpinner.setAttribute("class", "jeql-spinner");
    spinner.appendChild(subSpinner);
    document.body.appendChild(spinner);
}

export function destroySpinner() {
    document.body.removeChild(document.getElementsByClassName("jeql-spinner-outer")[0]);
}

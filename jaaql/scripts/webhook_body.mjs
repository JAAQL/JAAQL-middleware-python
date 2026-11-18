// Preloaded by JAAQL into the node process of every webhook (handle_webhook in jaaql/mvc/model.py: node --import <this file> ...), before the
// webhook's own modules. JAAQL writes the request body to the process's stdin, which has no size limit, instead of putting it on the command
// line, where Linux allows one argument at most 128 KiB, and passes the marker below in the body's place. Here the marker is replaced by the
// body as base64, which is what the body argument has always held, so BATON's cloud runtime (initializeWebhook, process.argv) reads every
// body as it read a small one, without being rebuilt. Without the marker (a command line that holds no body) stdin is left alone
import { readFileSync } from "node:fs";

const MARKER = "jaaql:body-on-stdin";

const at = process.argv.indexOf(MARKER, 2);
if (at !== -1) {
	process.argv[at] = readFileSync(0).toString("base64");
}

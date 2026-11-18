// Preloaded by JAAQL into the node process of every webhook (handle_webhook in jaaql/mvc/model.py: node --import <this file> ...), and of a
// cloud procedure whose args are too large for its command line (handle_procedure, through NODE_OPTIONS), before the process's own modules.
// JAAQL writes the request body, or the args, to the process's stdin, which has no size limit, instead of putting it on the command line,
// where Linux allows one argument at most 128 KiB, and passes the marker below in its place. Here the marker is replaced by what stdin holds,
// as base64, which is what that argument has always held, so BATON's cloud runtime (initializeWebhook, initialize: process.argv) reads it as
// it read a small one, without being rebuilt. Without the marker (a command line that holds what it carries) stdin is left alone
import { readFileSync } from "node:fs";

const MARKER = "jaaql:body-on-stdin";

const at = process.argv.indexOf(MARKER, 2);
if (at !== -1) {
	process.argv[at] = readFileSync(0).toString("base64");
}

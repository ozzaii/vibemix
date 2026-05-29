// SPDX-License-Identifier: Apache-2.0
//
// Entry for the cohesive DesktopShell window (shell.html). Mounts the shell on
// #shell-root. Tokens + shell styles are linked from the HTML page, matching
// the project's other entries.

import { mountDesktopShell } from "./DesktopShell.js";

const host = document.getElementById("shell-root");
if (host) {
  mountDesktopShell(host);
}

/* Blockly Lab frontend: small, clear controls for students.
 *
 * Entry point, loaded as a module after the classic Blockly and Monaco loader
 * scripts. It wires the modules together in the order the page needs and runs
 * the status polling loop. */
import { initAlertModal } from "./alert-modal.js";
import { jsonRequest } from "./api.js";
import { initBlocks } from "./blocks.js";
import { initConnection, renderConnection } from "./connection.js";
import { initDirectory, refreshRobots, updateRobotPingStatuses } from "./directory.js";
import { generatePython, initEditor, loadMonaco } from "./editor.js";
import { initHelp } from "./help.js";
import { initLibrary, refreshLibrary } from "./library.js";
import { ingestEvents, initProgram, initRunControls, updateProgram } from "./program.js";
import { initReference } from "./reference.js";
import { state } from "./state.js";
import { initTeleop } from "./teleop.js";
import { $, setMessage } from "./ui.js";
import { initVideo, renderStats } from "./video.js";

let statusRequestInFlight = false;
let statusFailures = 0;

// Each page load polls with its own id: the polls are the page's heartbeat.
// On pagehide (tab closed, reload, navigation) a beacon tells the server; if
// no poll from a new page follows within a few seconds the server stops the
// program, and later lets go of the robot. A reload polls again at once, so
// it keeps the program running. Hidden tabs keep polling (slowly), so
// switching tabs never counts as closing.
function newPageId() {
  if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}
let pageId = newPageId();

window.addEventListener("pagehide", () => {
  navigator.sendBeacon("/api/page/closing", pageId);
});
window.addEventListener("pageshow", (event) => {
  // Restored from the back/forward cache: the old id was marked closed.
  if (event.persisted) {
    pageId = newPageId();
    pollStatus();
  }
});

async function pollStatus() {
  if (statusRequestInFlight) return;
  statusRequestInFlight = true;
  try {
    const data = await jsonRequest("/api/status?page=" + encodeURIComponent(pageId));
    statusFailures = 0;
    const connection = data.connection || {};
    const program = data.program || {};
    state.programRunning = program.status === "running";
    ingestEvents(data.events);
    renderConnection({
      ...connection,
      state: connection.state || (data.connected ? "connected" : "idle")
    });
    renderStats(state.lastConnection.state, connection, data.telemetry);
    updateProgram(program);
  } catch (_) {
    statusFailures += 1;
    if (statusFailures >= 2) {
      state.programRunning = false;
      renderConnection({state: "app_down"});
      renderStats("app_down", {}, null);
    }
  } finally {
    statusRequestInFlight = false;
  }
}

// Ctrl+S / Cmd+S (with or without Shift) does nothing here: it would only
// open the browser's "Save page" dialog. Capture runs before Monaco and Blockly.
window.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") event.preventDefault();
}, {capture: true});

initBlocks();
initProgram();
initTeleop();
initAlertModal();
initConnection();
initDirectory();
initVideo();
initRunControls();
initLibrary();

setInterval(pollStatus, 250);
pollStatus();
refreshRobots();
setInterval(updateRobotPingStatuses, 30_000);
setInterval(refreshRobots, 5 * 60 * 1000);
refreshLibrary().catch((error) => setMessage("Demo library: " + error.message, true));

initEditor();
initReference();
initHelp();

generatePython().then(loadMonaco);

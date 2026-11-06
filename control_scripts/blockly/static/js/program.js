// Running programs, and the terminal of program output and connection events.
import { jsonRequest } from "./api.js";
import { workspaceData } from "./blocks.js";
import { state } from "./state.js";
import { $, clock, setMessage } from "./ui.js";

// Terminal = program output followed by connection events (bounded).
let programOutputText = "";
let renderedTerminalKey = "";
const eventLog = [];
let lastEventId = 0;
const MAX_EVENT_LINES = 100;

export function updateProgram(program) {
  const status = program.status || "idle";
  const label = status[0].toUpperCase() + status.slice(1);
  const current = program.current ? ": " + program.current : "";
  setMessage(label + current + (program.error ? " — " + program.error : ""), Boolean(program
    .error));

  const vision = program.vision || {};
  if (vision.status) {
    const area = vision.area ? " (" + vision.area + "px²)" : "";
    $("camera-view-label").textContent = (program.camera_view || vision.status) + area;
  }

  programOutputText = program.output || "";
  renderTerminal();
}

function renderTerminal() {
  const key = programOutputText.length + "|" + programOutputText.slice(-64) + "|" +
    (eventLog.length ? eventLog[eventLog.length - 1].id : 0) + "|" + eventLog.length;
  if (key === renderedTerminalKey) return;
  renderedTerminalKey = key;
  const output = $("terminal-output");
  output.replaceChildren(document.createTextNode(programOutputText));
  if (eventLog.length) {
    if (programOutputText && !programOutputText.endsWith("\n")) {
      output.appendChild(document.createTextNode("\n"));
    }
    for (const item of eventLog) {
      const line = document.createElement("span");
      line.className = "term-event level-" + item.level;
      line.textContent = "[" + clock(item.t, true) + "] " + item.text + "\n";
      output.appendChild(line);
    }
  }
  output.scrollTop = output.scrollHeight;
}

export function ingestEvents(events) {
  if (!Array.isArray(events)) return;
  for (const item of events) {
    if (!item || typeof item.id !== "number" || item.id <= lastEventId) continue;
    lastEventId = item.id;
    eventLog.push({
      id: item.id,
      t: item.t,
      level: ["info", "warning", "error"].includes(item.level) ? item.level : "info",
      text: String(item.text || "")
    });
  }
  if (eventLog.length > MAX_EVENT_LINES) eventLog.splice(0, eventLog.length - MAX_EVENT_LINES);
}

export function toggleTerminal(open) {
  const tab = $("terminal-tab");
  const body = $("terminal-body");
  const next = open == null ? tab.getAttribute("aria-expanded") !== "true" : open;
  tab.setAttribute("aria-expanded", String(next));
  body.hidden = !next;
  tab.querySelector("span").textContent = next ? "click to close" : "click to open";
  requestAnimationFrame(() => {
    if (state.mode === "blocks") Blockly.svgResize(state.workspace);
    else if (state.editor) state.editor.layout();
  });
}

function startProgram() {
  if (state.mode === "python") {
    jsonRequest("/api/program/start", {
      method: "POST",
      body: JSON.stringify({
        python: state.editor ? state.editor.getValue() : ""
      })
    }).then(updateProgram).catch((error) => setMessage(error.message, true));
    return;
  }
  const topBlocks = state.workspace.getTopBlocks(true);
  if (topBlocks.length > 1) {
    setMessage("Join the " + topBlocks.length + " separate stacks before Run", true);
    return;
  }
  if (!topBlocks.length) {
    setMessage("Add an action block before Run", true);
    return;
  }
  jsonRequest("/api/program/start", {
    method: "POST",
    body: JSON.stringify({
      program: workspaceData()
    })
  }).then(updateProgram).catch((error) => setMessage(error.message, true));
}

function stopProgram() {
  jsonRequest("/api/program/stop", {
      method: "POST"
    })
    .then(updateProgram)
    .catch((error) => setMessage(error.message, true));
}

export function initProgram() {
  $("terminal-tab").addEventListener("click", () => toggleTerminal());
  $("terminal-clear").addEventListener("click", () => {
    eventLog.length = 0;
    programOutputText = "";
    renderedTerminalKey = "";
    $("terminal-output").textContent = "";
  });
}

export function initRunControls() {
  $("run-button").addEventListener("click", startProgram);
  $("stop-button").addEventListener("click", stopProgram);
  $("reset-lights-button").addEventListener("click", () => {
    jsonRequest("/api/lights/reset", {
        method: "POST"
      })
      .then(() => setMessage("Lights reset"))
      .catch((error) => setMessage(error.message, true));
  });
}

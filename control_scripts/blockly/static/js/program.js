// Running programs, the program status beside Run/Stop, and the terminal of
// program output and connection events.
import { jsonRequest } from "./api.js";
import { workspaceData } from "./blocks.js";
import { renderRunningStep } from "./running.js";
import { state } from "./state.js";
import { stopTeleop } from "./teleop.js";
import { $, clock, problemText, setMessage } from "./ui.js";

// Terminal = print() output and connection events, interleaved by time.
let outputLines = [];
let renderedTerminalKey = "";
const eventLog = [];
let lastEventId = 0;
const MAX_EVENT_LINES = 100;
// Clear hides output printed before it; the server still has those lines.
let clearedAt = 0;

// One short phrase: Ready / Running: <step> / Finished / Stopped: <reason> /
// Problem on line N: <error>.
function programStatusText(program) {
  const status = program.status || "idle";
  const step = program.current_step || {};
  if (status === "running") {
    const label = step.label || program.current;
    return {text: label ? "Running: " + label : "Running…", error: false};
  }
  if (status === "complete") return {text: "Finished", error: false};
  if (status === "stopped") {
    const reason = String(program.error || "").replace(/^Your program was stopped\s*(because\s*)?/i, "")
      .replace(/\.$/, "");
    return {text: reason ? "Stopped: " + reason : "Stopped", error: false};
  }
  if (status === "error") {
    // A Blocks run's line number is in the hidden generated Python: leave it out.
    const raw = step.mode === "blocks" ? String(program.error || "").replace(/^line \d+:\s*/i, "") :
      program.error;
    const text = problemText(raw);
    return {text: text.startsWith("Problem") ? text : "Problem: " + text, error: true};
  }
  return {text: "Ready", error: false};
}

function renderProgramStatus(program) {
  const element = $("program-status");
  const {text, error} = programStatusText(program);
  if (element.textContent !== text) {
    element.textContent = text;
    element.title = text;
  }
  element.classList.toggle("error-text", error);
  element.classList.toggle("is-running", program.status === "running");
}

// The OpenCV label shows only while a running program has used a vision block.
function renderVisionLabel(program) {
  const label = $("vision-label");
  const view = program.camera_view;
  const active = program.status === "running" && view && view !== "Live camera";
  label.hidden = !active;
  if (!active) return;
  const vision = program.vision || {};
  const text = view + (vision.area ? " (" + vision.area + "px²)" : "");
  if (label.textContent !== text) label.textContent = label.title = text;
}

export function updateProgram(program) {
  renderProgramStatus(program);
  renderVisionLabel(program);
  renderRunningStep(program);
  outputLines = Array.isArray(program.output_lines) ? program.output_lines :
    String(program.output || "").split("\n").filter(Boolean).map((text) => ({t: 0, text}));
  renderTerminal();
}

function renderTerminal() {
  const shown = outputLines.filter((line) => !(line.t && line.t <= clearedAt));
  const last = shown[shown.length - 1];
  const key = shown.length + "|" + (last ? last.t + last.text : "") + "|" +
    (eventLog.length ? eventLog[eventLog.length - 1].id : 0) + "|" + eventLog.length;
  if (key === renderedTerminalKey) return;
  renderedTerminalKey = key;
  // Merge two lists that are each already in time order.
  const items = [];
  let i = 0;
  let j = 0;
  while (i < shown.length || j < eventLog.length) {
    const takeOutput = j >= eventLog.length ||
      (i < shown.length && Number(shown[i].t || 0) <= Number(eventLog[j].t || 0));
    items.push(takeOutput ? {output: shown[i++]} : {event: eventLog[j++]});
  }
  const output = $("terminal-output");
  output.replaceChildren();
  for (const item of items) {
    if (item.output) {
      output.appendChild(document.createTextNode(item.output.text + "\n"));
      continue;
    }
    const line = document.createElement("span");
    line.className = "term-event level-" + item.event.level;
    line.textContent = "[" + clock(item.event.t, true) + "] " + item.event.text + "\n";
    output.appendChild(line);
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
    setMessage("Join your " + topBlocks.length + " stacks into one stack before Run", true);
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
  stopTeleop(true);
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
    const last = outputLines[outputLines.length - 1];
    clearedAt = Math.max(Date.now() / 1000, last && last.t ? last.t : 0);
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

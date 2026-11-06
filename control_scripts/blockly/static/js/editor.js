// Python mode: the Monaco editor, kept in sync with the blocks.
import { jsonRequest } from "./api.js";
import { replaceWorkspace, workspaceData } from "./blocks.js";
import { LED_COLOUR_NAMES } from "./config.js";
import { state } from "./state.js";
import { $, setMessage } from "./ui.js";

const MONACO_BASE = window.MONACO_FROM_CDN
  ? "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min"
  // Absolute: the worker is a data: URL with no base, so a bare path can't resolve.
  : new URL("/static/vendor/monaco/min", location.href).href;
const COLOUR_CHOICES = LED_COLOUR_NAMES.join(",");
const PYTHON_API = [
  ["forward", "forward(seconds=${1:2}, power=${2:60})",
    "Drive forward for some seconds at a power from 0 to 100."
  ],
  ["backward", "backward(seconds=${1:2}, power=${2:60})", "Drive backward for some seconds."],
  ["turn_left", "turn_left(seconds=${1:1}, power=${2:60})", "Spin left on the spot."],
  ["turn_right", "turn_right(seconds=${1:1}, power=${2:60})", "Spin right on the spot."],
  ["turn_around", "turn_around(seconds=${1:1.5}, power=${2:60})", "Spin around on the spot."],
  ["drive", "drive(\"${1|forward,backward,left,right|}\", seconds=${2:1}, power=${3:60})",
    "Drive in a direction."
  ],
  ["wait", "wait(${1:1})", "Do nothing for some seconds."],
  ["stop", "stop()", "Stop the motors."],
  ["take_picture", "take_picture()", "Return a BGR NumPy image from the camera."],
  ["show_in_live_camera", "show_in_live_camera(${1:image})",
    "Show a grayscale or BGR OpenCV image in the camera panel."
  ],
  ["scan_robot_qr", "scan_robot_qr()",
    "Return a robot name such as trilo-xx from its Lincoln QR code, or an empty string."
  ],
  ["sees_colour", "sees_colour(\"${1|" + COLOUR_CHOICES +
    "|}\", tolerance=${2:18}, min_area=${3:500})", "Block-friendly OpenCV HSV and contour check."
  ],
  ["distance", "distance()", "Distance sensor reading in cm (nan if it could not be read)."],
  ["button_pressed", "button_pressed(\"${1|A,B,X,Y|}\")",
    "True while a button on the robot is held down."
  ],
  ["wait_until", "wait_until(lambda: ${1:distance() < 20})",
    "Pause until the condition is true."
  ],
  ["set_lights", "set_lights(\"${1|" + COLOUR_CHOICES + "|}\")",
    "Set the underlights to a colour."
  ],
  ["lights_off", "lights_off()", "Turn the underlights off."],
  ["flash_lights", "flash_lights(\"${1|" + COLOUR_CHOICES + "|}\", times=${2:3})",
    "Flash the underlights."
  ],
  ["set_button_light", "set_button_light(\"${1|A,B,X,Y|}\", ${2:1})",
    "Set a button LED brightness from 0 to 1."
  ],
  ["count", "count(${1:1}, ${2:5})",
    "Count from the first number to the last, both included: for i in count(1, 5)."
  ]
];

const blocksPane = $("blockly-workspace");
const pythonPane = $("python-pane");
const tabs = {
  blocks: $("tab-blocks"),
  python: $("tab-python")
};
const syncLabel = $("python-sync");
const ranchModal = $("ranch-modal");

let checkTimer = null;
let switching = false;

function setSync(kind, text) {
  syncLabel.className = "python-sync " + kind;
  syncLabel.textContent = text;
}

function createEditor() {
  state.editor = monaco.editor.create($("python-editor"), {
    value: state.lastBlockPython,
    language: "python",
    automaticLayout: true,
    minimap: {
      enabled: false
    },
    scrollBeyondLastLine: false,
    fontSize: 14,
    tabSize: 4,
    insertSpaces: true
  });
  monaco.languages.registerCompletionItemProvider("python", {
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn
      };
      return {
        suggestions: PYTHON_API.map(([label, insertText, documentation]) => ({
          label,
          insertText,
          documentation,
          range,
          kind: monaco.languages.CompletionItemKind.Function,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
        }))
      };
    }
  });
  state.editor.onDidChangeModelContent(scheduleCheck);
  state.editor.addAction({
    id: "format-document-black",
    label: "Format document (Black)",
    keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyI],
    contextMenuGroupId: "1_modification",
    run: formatDocument
  });
  setSync("ok", "Blocks can show this code");
}

async function formatDocument() {
  if (!state.editor) return;
  try {
    const result = await jsonRequest("/api/python/format", {
      method: "POST",
      body: JSON.stringify({
        code: state.editor.getValue()
      })
    });
    if (result.code !== state.editor.getValue()) state.editor.setValue(result.code);
    setMessage("Formatted document with Black");
  } catch (error) {
    setMessage("Format document: " + error.message, true);
  }
}

export function loadMonaco() {
  window.MonacoEnvironment = {
    getWorkerUrl: () => "data:text/javascript;charset=utf-8," + encodeURIComponent(
      "self.MonacoEnvironment = {baseUrl: '" + MONACO_BASE + "/'};" +
      "importScripts('" + MONACO_BASE + "/vs/base/worker/workerMain.js');"
    )
  };
  window.require.config({
    paths: {
      vs: MONACO_BASE + "/vs"
    }
  });
  window.require(["vs/editor/editor.main"], createEditor,
    () => setSync("error", "The Python editor could not load (it needs internet access)"));
}

export async function generatePython() {
  clearTimeout(state.generateTimer);
  const ticket = ++state.generateTicket;
  try {
    const data = await jsonRequest("/api/python/generate", {
      method: "POST",
      body: JSON.stringify({
        program: workspaceData()
      })
    });
    if (ticket !== state.generateTicket) return;
    state.lastBlockPython = data.code;
    state.lastWorkingPython = data.code;
    setEditorValue(data.code);
    if (state.mode === "python") setSync("ok", "Python and blocks are synced");
  } catch (error) {
    setMessage("Python view: " + error.message, true);
  }
}

export function queueGeneratePython() {
  clearTimeout(state.generateTimer);
  state.generateTimer = setTimeout(generatePython, 200);
}

export function setEditorValue(code) {
  if (!state.editor || state.editor.getValue() === code) return;
  state.syncingEditor = true;
  try {
    state.editor.setValue(code);
  } finally {
    state.syncingEditor = false;
  }
}

function syncWorkspaceFromPython(program, code) {
  clearTimeout(state.generateTimer);
  state.generateTicket++;
  replaceWorkspace(program);
  state.lastBlockPython = code;
  state.lastWorkingPython = code;
  setEditorValue(code);
  setSync("ok", "Python and blocks are synced");
}

function scheduleCheck() {
  clearTimeout(checkTimer);
  if (!state.syncingEditor && state.mode === "python") {
    state.generateTicket++;
    setSync("warn", "Syncing Python to blocks…");
    checkTimer = setTimeout(checkPython, 500);
  }
}

export async function checkPython() {
  if (!state.editor) return;
  const ticket = ++state.checkTicket;
  const model = state.editor.getModel();
  const code = state.editor.getValue();
  let result = {
    ok: true,
    code
  };
  if (code !== state.lastBlockPython) {
    try {
      result = await jsonRequest("/api/python/to_blocks", {
        method: "POST",
        body: JSON.stringify({
          code
        })
      });
    } catch (_) {
      return;
    }
    if (ticket !== state.checkTicket) return;
  }
  if (result.ok) {
    monaco.editor.setModelMarkers(model, "blocks", []);
    const canonical = result.code || code;
    if (result.program && canonical !== state.lastBlockPython) {
      syncWorkspaceFromPython(result.program, canonical);
    } else {
      state.lastWorkingPython = canonical;
      setEditorValue(canonical);
      setSync("ok", "Python and blocks are synced");
    }
    return;
  }
  const line = Math.min(Math.max(result.line || 1, 1), model.getLineCount());
  monaco.editor.setModelMarkers(model, "blocks", [{
    severity: result.syntax ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
    message: result.message,
    startLineNumber: line,
    endLineNumber: line,
    startColumn: 1,
    endColumn: model.getLineMaxColumn(line)
  }]);
  setSync(
    result.syntax ? "error" : "warn",
    result.syntax ? "Problem on line " + line + ": " + result.message :
      "Too advanced for blocks — line " + line + ": " + result.message
  );
}

export function showMode(next) {
  state.mode = next;
  blocksPane.hidden = next !== "blocks";
  pythonPane.hidden = next !== "python";
  for (const [name, button] of Object.entries(tabs)) {
    button.classList.toggle("active", name === next);
    button.setAttribute("aria-selected", String(name === next));
  }
  if (next === "blocks") {
    Blockly.svgResize(state.workspace);
  } else if (state.editor) {
    state.editor.layout();
    state.editor.focus();
    checkPython();
  }
}

function showRanchModal(result) {
  $("ranch-detail").textContent = (result.line ? "Line " + result.line + ": " : "") + (result
    .message || "");
  ranchModal.hidden = false;
  $("ranch-python").focus();
}

function closeRanchModal() {
  ranchModal.hidden = true;
  state.editor.focus();
}

async function leavePython() {
  if (!state.editor) return;
  const code = state.editor.getValue();
  if (code === state.lastBlockPython) {
    showMode("blocks");
    return;
  }
  let result;
  try {
    result = await jsonRequest("/api/python/to_blocks", {
      method: "POST",
      body: JSON.stringify({
        code
      })
    });
  } catch (error) {
    setMessage(error.message, true);
    return;
  }
  if (!result.ok) {
    showRanchModal(result);
    return;
  }
  syncWorkspaceFromPython(result.program, result.code);
  showMode("blocks");
  setMessage("Python and blocks are synced");
}

export async function switchMode(target) {
  if (switching || target === state.mode) return;
  switching = true;
  try {
    if (target === "python") {
      if (!state.editor) {
        setMessage("The Python editor is still loading", true);
        return;
      }
      await generatePython();
      showMode("python");
    } else {
      await leavePython();
    }
  } finally {
    switching = false;
  }
}

export function initEditor() {
  state.workspace.addChangeListener((event) => {
    if (event.isUiEvent || state.syncingWorkspace) return;
    state.checkTicket++;
    if (state.mode === "python") setSync("warn", "Syncing blocks to Python…");
    queueGeneratePython();
  });
  tabs.blocks.addEventListener("click", () => switchMode("blocks"));
  tabs.python.addEventListener("click", () => switchMode("python"));
  $("ranch-python").addEventListener("click", closeRanchModal);
  $("ranch-reset").addEventListener("click", async () => {
    ranchModal.hidden = true;
    setEditorValue(state.lastWorkingPython || state.lastBlockPython);
    await leavePython();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !ranchModal.hidden) closeRanchModal();
  });
}

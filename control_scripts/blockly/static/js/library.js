// Demo library and trait files: load and save programs.
import { jsonRequest } from "./api.js";
import { replaceWorkspace, workspaceData } from "./blocks.js";
import { checkPython, queueGeneratePython, setEditorValue, showMode } from "./editor.js";
import { state } from "./state.js";
import { $, setMessage } from "./ui.js";

const librarySelect = $("library-select");
const fileInput = $("program-file");

function loadWorkspaceData(program, message) {
  replaceWorkspace(program);
  setMessage(message);
  queueGeneratePython();
}

export async function refreshLibrary(selectedName = "") {
  const data = await jsonRequest("/api/library");
  librarySelect.replaceChildren();
  const groups = {
    blocks: document.createElement("optgroup"),
    python: document.createElement("optgroup")
  };
  groups.blocks.label = "Block demos";
  groups.python.label = "Python demos";
  for (const demo of data.demos || []) {
    const option = document.createElement("option");
    option.value = demo.name;
    option.textContent = demo.saved ? demo.name + " (mine)" : demo.name;
    if (!demo.block_compatible && demo.block_error) option.title = demo.block_error;
    groups[demo.kind === "python" ? "python" : "blocks"].appendChild(option);
  }
  for (const group of Object.values(groups)) {
    if (group.children.length) librarySelect.appendChild(group);
  }
  if (selectedName && [...librarySelect.options].some((option) => option.value ===
      selectedName)) {
    librarySelect.value = selectedName;
  }
}

async function loadLibraryDemo() {
  const name = librarySelect.value;
  if (!name) {
    setMessage("The demo library is empty", true);
    return;
  }
  try {
    const program = await jsonRequest("/api/library/" + encodeURIComponent(name));
    if (typeof program.python === "string") {
      if (!state.editor) {
        setMessage("The Python editor is still loading", true);
        return;
      }
      // Drop any pending block-to-Python refresh so it can't overwrite the demo.
      clearTimeout(state.generateTimer);
      state.generateTicket++;
      state.lastBlockPython = "";
      state.lastWorkingPython = "";
      setEditorValue(program.python);
      if (state.mode !== "python") showMode("python");
      else checkPython();
      setMessage("Loaded Python demo: " + name + ". Press Run to try it.");
      return;
    }
    if (state.mode === "python") showMode("blocks");
    loadWorkspaceData(program, "Loaded demo: " + name);
  } catch (error) {
    setMessage("Could not load demo: " + error.message, true);
  }
}

async function saveLibraryDemo() {
  const name = window.prompt("Name this demo:", librarySelect.value || "My robot trait");
  if (!name || !name.trim()) return;
  try {
    const cleanName = name.trim();
    const result = await jsonRequest("/api/library/" + encodeURIComponent(cleanName), {
      method: "POST",
      body: JSON.stringify(state.mode === "python" && state.editor ? {
        python: state.editor.getValue()
      } : workspaceData())
    });
    await refreshLibrary(result.name);
    setMessage("Saved demo: " + result.name);
  } catch (error) {
    setMessage("Could not save demo: " + error.message, true);
  }
}

function downloadProgram() {
  const name = window.prompt("File name:", "trilobot_trait");
  if (name === null) return;
  const fileName = (name.trim().replace(/\.json$/i, "").replace(/[\\/:*?"<>|]/g, "_")) || "trilobot_trait";
  const data = JSON.stringify(workspaceData(), null, 2);
  const blob = new Blob([data], {
    type: "application/json"
  });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = fileName + ".json";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  setMessage("Saved trait file");
}

function loadProgramFile(file) {
  const reader = new FileReader();
  reader.onload = () => {
    try {
      const program = JSON.parse(reader.result);
      loadWorkspaceData(program, "Loaded trait file");
    } catch (error) {
      setMessage("Could not load file: " + error.message, true);
    }
  };
  reader.readAsText(file);
}

export function initLibrary() {
  $("save-button").addEventListener("click", downloadProgram);
  $("load-library-button").addEventListener("click", loadLibraryDemo);
  $("save-library-button").addEventListener("click", saveLibraryDemo);
  $("load-button").addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) loadProgramFile(fileInput.files[0]);
    fileInput.value = "";
  });
  $("clear-button").addEventListener("click", () => {
    if (window.confirm("Clear all blocks?")) state.workspace.clear();
  });
}

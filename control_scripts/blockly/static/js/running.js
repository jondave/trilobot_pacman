// Shows which block (Blocks mode) or line (Python mode) is running, from
// /api/status program.current_step = {mode, line, block, label}. The status is
// polled every 250 ms, so the workspace and editor are only touched when the
// step changes; an unchanged step costs nothing and never flickers.
import { state } from "./state.js";

let shownBlock = null;  // block id highlighted in the workspace
let shownLine = null;   // Monaco line with the running decoration
let lineDecorations = [];

function showBlock(id) {
  const workspace = state.workspace;
  if (!workspace || typeof workspace.highlightBlock !== "function") return;
  // A block deleted (or the program edited) during the run: ignore its id.
  const wanted = id && workspace.getBlockById(id) ? id : null;
  if (wanted === shownBlock) return;
  shownBlock = wanted;
  workspace.highlightBlock(wanted);
}

function showLine(line) {
  const editor = state.editor;
  if (!editor || !window.monaco) return;
  const model = editor.getModel();
  const wanted = model && line && line <= model.getLineCount() ? line : null;
  if (wanted === shownLine) return;
  shownLine = wanted;
  lineDecorations = editor.deltaDecorations(lineDecorations, wanted ? [{
    range: new monaco.Range(wanted, 1, wanted, 1),
    options: {
      isWholeLine: true,
      className: "running-line",
      linesDecorationsClassName: "running-gutter"
    }
  }] : []);
  if (wanted) editor.revealLineInCenterIfOutsideViewport(wanted);
}

export function renderRunningStep(program) {
  const running = program && program.status === "running";
  const step = (running && program.current_step) || {};
  showBlock(step.mode === "blocks" ? step.block : null);
  showLine(step.mode === "python" ? step.line : null);
}

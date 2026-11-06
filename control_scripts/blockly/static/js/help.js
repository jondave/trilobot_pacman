// Quick start guide: one colourful step at a time.
import { switchMode } from "./editor.js";
import { toggleTerminal } from "./program.js";
import { state } from "./state.js";
import { $, setButtonLabel } from "./ui.js";

const HELP_SEEN_KEY = "trilobotBlocklyQuickStartSeen";
const helpModal = $("help-modal");
const helpHighlight = $("help-highlight");
const helpSteps = [{
  icon: "fas fa-plug icon-blue",
  title: "Connect to a robot",
  target: ".connection-controls",
  targetLabel: "Connection bar",
  targetHint: "Choose a robot, then press Connect.",
  body: "Select a robot by name and IP address. If it is not listed, choose <strong>Enter address manually…</strong> and edit the pre-filled address."
}, {
  icon: "fas fa-puzzle-piece icon-purple",
  title: "Choose a block",
  target: ".blocklyToolbox, .blocklyToolboxDiv",
  targetLabel: "Block toolbox",
  targetHint: "Drag a block into the program area.",
  body: "Open a colourful category and drag out an action. The toolbox is your menu of robot, logic, and OpenCV blocks."
}, {
  icon: "fas fa-layer-group icon-orange",
  title: "Build the program",
  target: "#blockly-workspace",
  targetLabel: "Program workspace",
  targetHint: "Snap blocks together from top to bottom.",
  body: "Set the number sockets to values that suit your robot. Keep actions in one connected stack so they run in order."
}, {
  icon: "fas fa-camera icon-pink",
  title: "Watch the camera",
  target: "#camera-card",
  targetLabel: "Camera panel",
  targetHint: "See the live image and OpenCV preview here.",
  body: "The camera panel shows the robot's live view. OpenCV blocks can take pictures, change colour spaces, make masks, and display their result here."
}, {
  icon: "fas fa-play-circle icon-success",
  title: "Run your program",
  target: "#run-button",
  targetLabel: "Run controls",
  targetHint: "Start with Run and stop safely with Stop.",
  body: "Press <strong>Run</strong> when your stack is ready. Use <strong>Stop</strong> if the robot needs to halt immediately."
}, {
  icon: "fab fa-python icon-blue",
  title: "Try Python",
  target: "#tab-python",
  targetLabel: "Python tab",
  targetHint: "See the same program as readable Python.",
  body: "The Python tab shows the same robot API as code. You can type Python, use <code>cv2</code> and <code>numpy</code>, and run it there."
}, {
  icon: "fas fa-book icon-teal",
  title: "Try a demo or the example task",
  target: ".library-footer",
  targetLabel: "Demo library",
  targetHint: "Pick a demo here, then press Load demo.",
  body: "Start with <strong>Example task - Stop at the wall</strong>, or try any starter demo. Demos you save yourself are marked <em>(mine)</em>. Saving with a name that already exists adds (1), (2)… instead of overwriting."
}, {
  icon: "fas fa-terminal icon-slate",
  title: "Read the feedback",
  target: "#terminal-tab",
  targetLabel: "Terminal",
  targetHint: "Open this to see print output and status messages.",
  body: "Use the terminal to understand what your program is doing. It shows <code>print()</code> output, errors, and current robot activity."
}, {
  icon: "fas fa-gamepad icon-purple",
  title: "Move safely with teleop",
  target: "#teleop-card",
  targetLabel: "Teleop controls",
  targetHint: "Enable only when you need to reposition the robot.",
  body: "Turn teleop on before using the direction controls or keyboard shortcuts. Release the key to stop sending movement commands."
}, ];
let helpIndex = 0;

function clearHelpHighlight() {
  helpHighlight.classList.remove("active");
}

function positionHelpHighlight(target) {
  if (!target || helpModal.hidden) {
    clearHelpHighlight();
    return;
  }
  const rect = target.getBoundingClientRect();
  const padding = 6;
  Object.assign(helpHighlight.style, {
    left: `${Math.max(0, rect.left - padding)}px`,
    top: `${Math.max(0, rect.top - padding)}px`,
    width: `${rect.width + padding * 2}px`,
    height: `${rect.height + padding * 2}px`
  });
  helpHighlight.classList.add("active");
}

function currentHelpTarget() {
  return document.querySelector(helpSteps[helpIndex].target);
}

async function renderHelpStep() {
  const step = helpSteps[helpIndex];
  $("help-progress").textContent = `${helpIndex + 1} / ${helpSteps.length}`;
  $("help-target-label").textContent = step.targetLabel;
  $("help-target-hint").textContent = step.targetHint;
  $("help-step").innerHTML =
    `<h3><i class="qsg-icon ${step.icon}" aria-hidden="true"></i> ${step.title}</h3><p>${step.body}</p>`;
  const wantedMode = step.target === "#tab-python" ? "python" : "blocks";
  if (state.mode !== wantedMode) await switchMode(wantedMode);
  toggleTerminal(step.target === "#terminal-tab");
  $("help-prev").disabled = helpIndex === 0;
  const last = helpIndex === helpSteps.length - 1;
  setButtonLabel($("help-next"), last ? "Finish" : "Next");
  $("help-next").querySelector("i").className = "fas btn-trailing-icon " + (last ? "fa-check" : "fa-arrow-right");
  requestAnimationFrame(() => positionHelpHighlight(currentHelpTarget()));
}

function openHelp() {
  helpIndex = 0;
  helpModal.hidden = false;
  renderHelpStep();
  $("help-next").focus();
}

function closeHelp() {
  helpModal.hidden = true;
  clearHelpHighlight();
  try {
    localStorage.setItem(HELP_SEEN_KEY, "1");
  } catch (_) {}
}


// Wires the guide and opens it on a first visit.
export function initHelp() {
  $("help-button").addEventListener("click", openHelp);
  $("help-close").addEventListener("click", closeHelp);
  $("help-prev").addEventListener("click", () => {
    if (helpIndex > 0) {
      helpIndex--;
      renderHelpStep();
    }
  });
  $("help-next").addEventListener("click", () => {
    if (helpIndex === helpSteps.length - 1) closeHelp();
    else {
      helpIndex++;
      renderHelpStep();
    }
  });
  helpModal.addEventListener("click", (event) => {
    if (event.target === helpModal) closeHelp();
  });
  window.addEventListener("resize", () => positionHelpHighlight(currentHelpTarget()));
  window.addEventListener("scroll", () => positionHelpHighlight(currentHelpTarget()), true);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !helpModal.hidden) closeHelp();
    if (event.key === "ArrowRight" && !helpModal.hidden) $("help-next").click();
    if (event.key === "ArrowLeft" && !helpModal.hidden) $("help-prev").click();
  });
  try {
    if (localStorage.getItem(HELP_SEEN_KEY) !== "1") openHelp();
  } catch (_) {
    openHelp();
  }
}

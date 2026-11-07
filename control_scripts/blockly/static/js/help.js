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
  body: "Pick your robot from the list. If it is not there, choose <strong>Enter address manually…</strong> and type the robot address. The dot next to the button shows if you are connected; the same button then says <strong>Disconnect</strong>."
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
  targetHint: "Join your blocks into one stack.",
  body: "Set the numbers to values that suit your robot. Keep your blocks in one stack so they run in order, top to bottom. While it runs, the block that is working glows."
}, {
  icon: "fas fa-camera icon-pink",
  title: "Watch the camera",
  target: "#camera-card",
  targetLabel: "Camera panel",
  targetHint: "See what the robot sees.",
  body: "The camera panel shows the robot's live picture and the distance sensor. OpenCV blocks can show their result here too. Open <strong>Details</strong> for the camera settings."
}, {
  icon: "fas fa-play-circle icon-success",
  title: "Run your program",
  target: ".action-buttons",
  targetLabel: "Run and Stop",
  targetHint: "Start with Run and stop safely with Stop.",
  body: "Press <strong>Run</strong> when your stack is ready. Press <strong>Stop</strong> to stop the robot straight away. The words next to Stop say what your program is doing."
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
  body: "The terminal shows your <code>print()</code> output and connection news, in time order."
}, {
  icon: "fas fa-gamepad icon-purple",
  title: "Teleoperation",
  target: "#teleop-card",
  targetLabel: "Teleoperation",
  targetHint: "Turn on Teleop only when you need to move the robot.",
  body: "Switch <strong>Teleop</strong> on, then hold an arrow button or a key. Let go and the robot stops."
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

/* Blockly Lab frontend: small, clear controls for students. */

Blockly.defineBlocksWithJsonArray([
  {
    type: "robot_forward",
    message0: "move forward for %1 seconds at %2% power",
    args0: [
      {type: "input_value", name: "SECONDS", check: "Number"},
      {type: "input_value", name: "SPEED", check: "Number"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 35,
    tooltip: "Drive straight ahead."
  },
  {
    type: "robot_backward",
    message0: "move backward for %1 seconds at %2% power",
    args0: [
      {type: "input_value", name: "SECONDS", check: "Number"},
      {type: "input_value", name: "SPEED", check: "Number"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 35
  },
  {
    type: "robot_turn_left",
    message0: "turn left for %1 seconds at %2% power",
    args0: [
      {type: "input_value", name: "SECONDS", check: "Number"},
      {type: "input_value", name: "SPEED", check: "Number"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 35
  },
  {
    type: "robot_turn_right",
    message0: "turn right for %1 seconds at %2% power",
    args0: [
      {type: "input_value", name: "SECONDS", check: "Number"},
      {type: "input_value", name: "SPEED", check: "Number"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 35
  },
  {
    type: "robot_turn_around",
    message0: "turn around for %1 seconds at %2% power",
    args0: [
      {type: "input_value", name: "SECONDS", check: "Number"},
      {type: "input_value", name: "SPEED", check: "Number"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 35
  },
  {
    type: "robot_drive_for",
    message0: "drive %1 for %2 seconds at %3% power",
    args0: [
      {type: "field_dropdown", name: "DIRECTION", options: [["forward", "FORWARD"], ["backward", "BACKWARD"], ["left", "LEFT"], ["right", "RIGHT"]]},
      {type: "input_value", name: "SECONDS", check: "Number"},
      {type: "input_value", name: "SPEED", check: "Number"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 35
  },
  {
    type: "robot_take_picture",
    message0: "take a picture",
    previousStatement: null,
    nextStatement: null,
    colour: 285,
    tooltip: "Take a snapshot for the OpenCV blocks."
  },
  {
    type: "opencv_camera_image",
    message0: "camera image",
    output: "Image",
    colour: 285,
    tooltip: "Take a BGR image from the live robot camera."
  },
  {
    type: "opencv_to_hsv",
    message0: "convert %1 %2",
    args0: [
      {type: "input_value", name: "IMAGE", check: "Image"},
      {type: "field_dropdown", name: "CONVERSION", options: [["BGR → HSV", "BGR_TO_HSV"], ["HSV → BGR", "HSV_TO_BGR"]]}
    ],
    output: "Image",
    colour: 285,
    tooltip: "Convert an OpenCV BGR image to HSV."
  },
  {
    type: "opencv_blur",
    message0: "blur %1 with a %2 pixel kernel",
    args0: [
      {type: "input_value", name: "IMAGE", check: "Image"},
      {type: "input_value", name: "KERNEL", check: "Number"}
    ],
    output: "Image",
    colour: 285,
    tooltip: "Smooth an image before making a mask. Use an odd kernel such as 5."
  },
  {
    type: "opencv_box_blur",
    message0: "box blur %1 with a %2 pixel kernel",
    args0: [
      {type: "input_value", name: "IMAGE", check: "Image"},
      {type: "input_value", name: "KERNEL", check: "Number"}
    ],
    output: "Image",
    colour: 285,
    tooltip: "Apply OpenCV's simple box blur. Use an odd kernel such as 5."
  },
  {
    type: "opencv_hsv_value",
    message0: "HSV value: H %1  S %2  V %3",
    args0: [
      {type: "input_value", name: "H", check: "Number"},
      {type: "input_value", name: "S", check: "Number"},
      {type: "input_value", name: "V", check: "Number"}
    ],
    output: "HSV",
    colour: 285,
    tooltip: "One HSV colour bound. H is 0–179; S and V are 0–255."
  },
  {
    type: "opencv_hsv_mask",
    message0: "make HSV mask from %1",
    args0: [{type: "input_value", name: "IMAGE", check: "Image"}],
    message1: "low HSV bound %1",
    args1: [{type: "input_value", name: "LOW", check: "HSV"}],
    message2: "high HSV bound %1",
    args2: [{type: "input_value", name: "HIGH", check: "HSV"}],
    output: "Image",
    colour: 285,
    tooltip: "Keep pixels inside these HSV bounds and make a black-and-white mask."
  },
  {
    type: "opencv_count_nonzero",
    message0: "count white pixels in %1",
    args0: [{type: "input_value", name: "IMAGE", check: "Image"}],
    output: "Number",
    colour: 285,
    tooltip: "Count the white pixels in a mask."
  },
  {
    type: "opencv_mask_or",
    message0: "combine masks %1 and %2",
    args0: [
      {type: "input_value", name: "IMAGE1", check: "Image"},
      {type: "input_value", name: "IMAGE2", check: "Image"}
    ],
    output: "Image",
    colour: 285,
    tooltip: "Combine two black-and-white masks with OpenCV bitwise OR."
  },
  {
    type: "robot_scan_qr",
    message0: "scan robot QR code",
    output: "String",
    colour: 285,
    tooltip: "Return the robot name such as trilo-09 from a Lincoln robot QR code."
  },
  {
    type: "robot_show_live_camera",
    message0: "show %1 in live camera",
    args0: [{type: "input_value", name: "IMAGE", check: "Image"}],
    previousStatement: null,
    nextStatement: null,
    colour: 285,
    tooltip: "Show an image or mask variable in the live camera panel. Leave it empty to show a fresh picture."
  },
  {
    type: "robot_if_color",
    message0: "OpenCV: if the picture contains %1",
    args0: [{type: "field_dropdown", name: "COLOR", options: [["red", "#ff0000"], ["green", "#00ff00"], ["blue", "#0000ff"], ["yellow", "#ffff00"], ["white", "#ffffff"], ["purple", "#ff00ff"]]}],
    message1: "colour tolerance %1 degrees, minimum area %2",
    args1: [
      {type: "input_value", name: "TOLERANCE", check: "Number"},
      {type: "input_value", name: "MIN_AREA", check: "Number"}
    ],
    message2: "then do %1",
    args2: [{type: "input_statement", name: "THEN"}],
    message3: "otherwise do %1",
    args3: [{type: "input_statement", name: "ELSE"}],
    previousStatement: null,
    nextStatement: null,
    colour: 285,
    tooltip: "Uses basic OpenCV HSV colour detection."
  },
  {
    type: "robot_if_distance",
    message0: "if distance is %1 %2 cm",
    args0: [
      {type: "field_dropdown", name: "OPERATOR", options: [["less than", "LESS_THAN"], ["more than", "MORE_THAN"]]},
      {type: "input_value", name: "CENTIMETRES", check: "Number"}
    ],
    message1: "then do %1",
    args1: [{type: "input_statement", name: "THEN"}],
    message2: "otherwise do %1",
    args2: [{type: "input_statement", name: "ELSE"}],
    previousStatement: null,
    nextStatement: null,
    colour: 165,
    tooltip: "Reads the robot's distance sensor."
  },
  {
    type: "robot_underlights_on",
    message0: "turn on underlights",
    previousStatement: null,
    nextStatement: null,
    colour: 315,
    tooltip: "Turn the robot underlights on white."
  },
  {
    type: "robot_underlights_off",
    message0: "turn off underlights",
    previousStatement: null,
    nextStatement: null,
    colour: 315,
    tooltip: "Turn all underlights off."
  },
  {
    type: "robot_lights_red",
    message0: "set lights red",
    previousStatement: null,
    nextStatement: null,
    colour: 0
  },
  {
    type: "robot_lights_green",
    message0: "set lights green",
    previousStatement: null,
    nextStatement: null,
    colour: 120
  },
  {
    type: "robot_lights_blue",
    message0: "set lights blue",
    previousStatement: null,
    nextStatement: null,
    colour: 210
  },
  {
    type: "robot_lights_yellow",
    message0: "set lights yellow",
    previousStatement: null,
    nextStatement: null,
    colour: 60
  },
  {
    type: "robot_lights_white",
    message0: "set lights white",
    previousStatement: null,
    nextStatement: null,
    colour: 45
  },
  {
    type: "robot_lights_purple",
    message0: "set lights purple",
    previousStatement: null,
    nextStatement: null,
    colour: 285
  },
  {
    type: "robot_colour_red",
    message0: "red",
    output: "Colour",
    colour: 0
  },
  {
    type: "robot_colour_green",
    message0: "green",
    output: "Colour",
    colour: 120
  },
  {
    type: "robot_colour_blue",
    message0: "blue",
    output: "Colour",
    colour: 210
  },
  {
    type: "robot_colour_yellow",
    message0: "yellow",
    output: "Colour",
    colour: 60
  },
  {
    type: "robot_colour_white",
    message0: "white",
    output: "Colour",
    colour: 45
  },
  {
    type: "robot_colour_purple",
    message0: "purple",
    output: "Colour",
    colour: 285
  },
  {
    type: "robot_set_lights",
    message0: "set lights to %1",
    args0: [{type: "field_dropdown", name: "COLOR", options: [["red", "#ff0000"], ["green", "#00ff00"], ["blue", "#0000ff"], ["yellow", "#ffff00"], ["white", "#ffffff"], ["purple", "#ff00ff"]]}],
    previousStatement: null,
    nextStatement: null,
    colour: 315
  },
  {
    type: "robot_flash_lights",
    message0: "flash %1 for %2 times",
    args0: [
      {type: "field_dropdown", name: "COLOR", options: [["red", "#ff0000"], ["green", "#00ff00"], ["blue", "#0000ff"], ["yellow", "#ffff00"], ["white", "#ffffff"], ["purple", "#ff00ff"]]},
      {type: "input_value", name: "TIMES", check: "Number"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 315
  },
  {
    type: "robot_button_light",
    message0: "set button %1 brightness to %2",
    args0: [
      {type: "field_dropdown", name: "BUTTON", options: [["A", "A"], ["B", "B"], ["X", "X"], ["Y", "Y"]]},
      {type: "input_value", name: "BRIGHTNESS", check: "Number"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 315
  },
  {
    type: "robot_repeat",
    message0: "repeat %1 times",
    args0: [{type: "input_value", name: "TIMES", check: "Number"}],
    message1: "do %1",
    args1: [{type: "input_statement", name: "DO"}],
    previousStatement: null,
    nextStatement: null,
    colour: 120,
    tooltip: "Repeat the blocks inside this loop."
  },
  {
    type: "robot_wait",
    message0: "wait %1 seconds",
    args0: [{type: "input_value", name: "SECONDS", check: "Number"}],
    previousStatement: null,
    nextStatement: null,
    colour: 35
  },
  {
    type: "robot_stop",
    message0: "stop the robot",
    previousStatement: null,
    nextStatement: null,
    colour: 0
  },
  {
    type: "robot_print",
    message0: "print %1 %2",
    args0: [
      {type: "input_value", name: "VALUE"},
      {type: "input_value", name: "VALUE2"}
    ],
    previousStatement: null,
    nextStatement: null,
    colour: 210,
    tooltip: "Write a value to the terminal."
  },
  {
    type: "robot_wait_until",
    message0: "wait until %1",
    args0: [{type: "input_value", name: "CONDITION", check: "Boolean"}],
    previousStatement: null,
    nextStatement: null,
    colour: 35,
    tooltip: "Pause the program until the condition is true."
  },
  {
    type: "robot_distance_condition",
    message0: "distance is %1 %2 cm",
    args0: [
      {type: "field_dropdown", name: "OPERATOR", options: [["less than", "LESS_THAN"], ["more than", "MORE_THAN"]]},
      {type: "input_value", name: "CENTIMETRES", check: "Number"}
    ],
    output: "Boolean",
    colour: 165,
    tooltip: "True when the distance sensor reading matches."
  },
  {
    type: "robot_distance_value",
    message0: "distance in cm",
    output: "Number",
    colour: 165,
    tooltip: "Read the robot's distance sensor."
  },
  {
    type: "robot_button_pressed",
    message0: "robot button %1 is pressed",
    args0: [{type: "field_dropdown", name: "BUTTON", options: [["A", "A"], ["B", "B"], ["X", "X"], ["Y", "Y"]]}],
    output: "Boolean",
    colour: 165,
    tooltip: "True while the button on the robot is held down."
  }
]);

const workspace = Blockly.inject("blockly-workspace", {
  toolbox: document.getElementById("toolbox"),
  trashcan: true,
  move: {scrollbars: true, drag: true, wheel: true},
  zoom: {controls: true, wheel: true, startScale: 0.85, maxScale: 1.25, minScale: 0.55}
});

workspace.registerButtonCallback("CREATE_VARIABLE", (button) => {
  Blockly.Variables.createVariableButtonHandler(button.getTargetWorkspace());
});
window.addEventListener("resize", () => Blockly.svgResize(workspace));
setTimeout(() => Blockly.svgResize(workspace), 0);

function reflowToolbox() {
  const toolbox = workspace.getToolbox();
  const flyout = toolbox && toolbox.getFlyout();
  if (!flyout || !flyout.isVisible()) return;
  flyout.reflow();
  // Blockly 11 can leave flyout blocks at (0, 0) when the page uses a
  // flexible, resized workspace. Put each top-level flyout block in a real
  // vertical list while preserving Blockly's own model coordinates.
  setTimeout(() => {
    const flyoutWorkspace = flyout.getWorkspace && flyout.getWorkspace();
    if (!flyoutWorkspace) return;
    let y = 8;
    for (const block of flyoutWorkspace.getTopBlocks(false)) {
      const xy = block.getRelativeToSurfaceXY();
      const size = block.getHeightWidth();
      block.moveBy(8 - xy.x, y - xy.y);
      y += Math.max(35, size.height) + 8;
    }
  }, 0);
}
document.querySelector(".blocklyToolboxDiv")?.addEventListener("click", () => {
  setTimeout(reflowToolbox, 0);
});

const $ = (id) => document.getElementById(id);
const urlInput = $("robot-url");
const robotSelect = $("robot-select");
const manualRobotAddress = $("manual-robot-address");
const teleopEnabled = $("teleop-enabled");
const fileInput = $("program-file");
const librarySelect = $("library-select");
const pressedKeys = new Set();
const teleopButtons = new Map(
  [...document.querySelectorAll(".teleop-grid button")].map(
    (button) => [button.dataset.key, button]
  )
);
let statusRequestInFlight = false;
let robotChoices = [];
const MANUAL_ROBOT_VALUE = "__manual__";
const PING_STATUS = {
  green: {icon: "🟢", label: "Seen within 10 minutes"},
  orange: {icon: "🟠", label: "Not seen for more than 10 minutes"},
  red: {icon: "🔴", label: "Not seen for more than 30 minutes"}
};

async function jsonRequest(path, options = {}) {
  const requestOptions = {...options};
  if (requestOptions.body) {
    requestOptions.headers = {
      "Content-Type": "application/json",
      ...(requestOptions.headers || {})
    };
  }
  const response = await fetch(path, requestOptions);
  let data = {};
  try { data = await response.json(); } catch (_) {}
  if (!response.ok) {
    throw new Error(data.error || "Request failed (" + response.status + ")");
  }
  return data;
}

function robotPingState(lastPing) {
  const timestamp = Date.parse(lastPing || "");
  if (!Number.isFinite(timestamp)) return "red";
  const age = Math.max(0, Date.now() - timestamp) / 1000;
  if (age <= 10 * 60) return "green";
  if (age <= 30 * 60) return "orange";
  return "red";
}

function updateManualAddressVisibility(focus = false) {
  const manual = robotSelect.value === MANUAL_ROBOT_VALUE;
  manualRobotAddress.hidden = !manual;
  if (manual && focus) urlInput.focus();
}

function updateRobotPingStatuses() {
  for (const option of robotSelect.options) {
    const robot = robotChoices.find((item) => item.url === option.value);
    if (!robot) continue;
    const state = PING_STATUS[robotPingState(robot.last_ping)];
    option.textContent = state.icon + " " + robot.name + " (" + robot.ip + ")";
    option.title = state.label + (robot.last_ping ? ": " + robot.last_ping : "");
  }
}

function populateRobotChoices(robots) {
  const previous = robotSelect.value;
  robotChoices = robots.filter((robot) => robot && robot.url && robot.ip && robot.name);
  robotSelect.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = robotChoices.length ? "Choose a robot…" : "No robots found";
  robotSelect.appendChild(placeholder);
  for (const robot of robotChoices) {
    const option = document.createElement("option");
    option.value = robot.url;
    option.textContent = robot.name + " (" + robot.ip + ")";
    option.title = robot.url;
    robotSelect.appendChild(option);
  }
  const manualOption = document.createElement("option");
  manualOption.value = MANUAL_ROBOT_VALUE;
  manualOption.textContent = "Enter address manually…";
  robotSelect.appendChild(manualOption);
  if (previous && [...robotSelect.options].some((option) => option.value === previous)) {
    robotSelect.value = previous;
  } else if (robotChoices.length) {
    robotSelect.selectedIndex = 1;
  } else {
    robotSelect.value = MANUAL_ROBOT_VALUE;
  }
  updateManualAddressVisibility();
  updateRobotPingStatuses();
}

async function refreshRobots() {
  try {
    const data = await jsonRequest("/api/robots");
    const robots = Array.isArray(data.robots) ? data.robots : [];
    populateRobotChoices(robots);
  } catch (error) {
    populateRobotChoices([]);
  }
}

function setMessage(message, error = false) {
  const element = $("program-status");
  element.textContent = message;
  element.classList.toggle("error-text", error);
}

function workspaceData() {
  return Blockly.serialization.workspaces.save(workspace);
}

function replaceWorkspace(program) {
  checkTicket++;
  syncingWorkspace = true;
  try {
    workspace.clear();
    Blockly.serialization.workspaces.load(program, workspace);
  } finally {
    syncingWorkspace = false;
  }
}

function loadWorkspaceData(program, message) {
  replaceWorkspace(program);
  setMessage(message);
  queueGeneratePython();
}

async function refreshLibrary(selectedName = "") {
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
    option.textContent = demo.name;
    if (!demo.block_compatible && demo.block_error) option.title = demo.block_error;
    groups[demo.kind === "python" ? "python" : "blocks"].appendChild(option);
  }
  for (const group of Object.values(groups)) {
    if (group.children.length) librarySelect.appendChild(group);
  }
  if (selectedName && [...librarySelect.options].some((option) => option.value === selectedName)) {
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
      if (!editor) {
        setMessage("The Python editor is still loading", true);
        return;
      }
      // Drop any pending block-to-Python refresh so it can't overwrite the demo.
      clearTimeout(generateTimer);
      generateTicket++;
      lastBlockPython = "";
      lastWorkingPython = program.python;
      setEditorValue(program.python);
      if (mode !== "python") showMode("python");
      else checkPython();
      setMessage("Loaded Python demo: " + name + ". Press Run to try it.");
      return;
    }
    if (mode === "python") showMode("blocks");
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
    await jsonRequest("/api/library/" + encodeURIComponent(cleanName), {
      method: "POST",
      body: JSON.stringify(mode === "python" && editor ? {python: editor.getValue()} : workspaceData())
    });
    await refreshLibrary(cleanName);
    setMessage("Saved demo: " + cleanName);
  } catch (error) {
    setMessage("Could not save demo: " + error.message, true);
  }
}

function downloadProgram() {
  const data = JSON.stringify(workspaceData(), null, 2);
  const blob = new Blob([data], {type: "application/json"});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "trilobot_trait.json";
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

function updateProgram(program) {
  const status = program.status || "idle";
  const label = status[0].toUpperCase() + status.slice(1);
  const current = program.current ? ": " + program.current : "";
  setMessage(label + current + (program.error ? " — " + program.error : ""), Boolean(program.error));

  const vision = program.vision || {};
  if (vision.status) {
    const area = vision.area ? " (" + vision.area + "px²)" : "";
    $("camera-view-label").textContent = (program.camera_view || vision.status) + area;
  }

  const output = $("terminal-output");
  const text = program.output || "";
  if (output.textContent !== text) {
    output.textContent = text;
    output.scrollTop = output.scrollHeight;
  }
}

function toggleTerminal(open) {
  const tab = $("terminal-tab");
  const body = $("terminal-body");
  const next = open == null ? tab.getAttribute("aria-expanded") !== "true" : open;
  tab.setAttribute("aria-expanded", String(next));
  body.hidden = !next;
  tab.querySelector("span").textContent = next ? "click to close" : "click to open";
  requestAnimationFrame(() => {
    if (mode === "blocks") Blockly.svgResize(workspace);
    else if (editor) editor.layout();
  });
}

$("terminal-tab").addEventListener("click", () => toggleTerminal());
$("terminal-clear").addEventListener("click", () => { $("terminal-output").textContent = ""; });

function videoSettings() {
  const selected = $("video-size").selectedOptions[0];
  return {
    width: Number(selected.dataset.width),
    height: Number(selected.dataset.height),
    fps: Number($("video-fps").value),
    jpeg_quality: Number($("video-quality").value)
  };
}

function setVideoSettings(video) {
  if (!video) return;
  const size = video.width + "x" + video.height;
  const sizeOption = [...$("video-size").options].find((option) => option.value === size);
  if (sizeOption) $("video-size").value = size;
  $("video-fps").value = String(video.fps);
  $("video-quality").value = String(video.jpeg_quality);
}

async function connectRobot() {
  const address = robotSelect.value === MANUAL_ROBOT_VALUE
    ? urlInput.value.trim()
    : robotSelect.value;
  if (!address) {
    setMessage("Choose a robot or enter a manual WebSocket address", true);
    return;
  }
  try {
    const data = await jsonRequest("/api/connect", {
      method: "POST",
      body: JSON.stringify({url: address, video: videoSettings()})
    });
    setVideoSettings(data.video);
    setMessage("Connecting…");
    $("target-label").textContent = data.url || address;
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function disconnectRobot() {
  try {
    await jsonRequest("/api/disconnect", {method: "POST"});
    teleopEnabled.checked = false;
    updateTeleopState();
    stopTeleop(true);
    setMessage("Disconnected");
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function applyVideoSettings() {
  try {
    const data = await jsonRequest("/api/video/config", {
      method: "POST",
      body: JSON.stringify(videoSettings())
    });
    setVideoSettings(data.video);
    setMessage("Camera settings applied");
  } catch (error) {
    setMessage(error.message, true);
  }
}

function startProgram() {
  if (mode === "python") {
    jsonRequest("/api/program/start", {
      method: "POST",
      body: JSON.stringify({python: editor ? editor.getValue() : ""})
    }).then(updateProgram).catch((error) => setMessage(error.message, true));
    return;
  }
  const topBlocks = workspace.getTopBlocks(true);
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
    body: JSON.stringify({program: workspaceData()})
  }).then(updateProgram).catch((error) => setMessage(error.message, true));
}

function stopProgram() {
  jsonRequest("/api/program/stop", {method: "POST"})
    .then(updateProgram)
    .catch((error) => setMessage(error.message, true));
}

function postTeleop(payload) {
  fetch("/api/teleop", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  }).catch((error) => setMessage("Teleop: " + error.message, true));
}

let teleopTimer = null;
let activeTeleopButton = null;

function sendTeleop(button) {
  if (!teleopEnabled.checked || !button) return;
  const payload = button.dataset.stop === "true"
    ? {stop: true}
    : {left: Number(button.dataset.left), right: Number(button.dataset.right)};
  postTeleop(payload);
}

function startTeleop(button) {
  if (!teleopEnabled.checked || !button) return;
  if (activeTeleopButton && activeTeleopButton !== button) stopTeleop();
  activeTeleopButton = button;
  button.classList.add("active");
  sendTeleop(button);
  clearInterval(teleopTimer);
  // Refresh faster than the robot's 0.6 second watchdog while held.
  teleopTimer = setInterval(() => {
    if (activeTeleopButton && teleopEnabled.checked) sendTeleop(activeTeleopButton);
  }, 150);
}

function stopTeleop(force = false) {
  if (!force && !teleopEnabled.checked) return;
  clearInterval(teleopTimer);
  teleopTimer = null;
  activeTeleopButton = null;
  document.querySelectorAll(".teleop-grid button.active")
    .forEach((button) => button.classList.remove("active"));
  postTeleop({stop: true});
}

function updateTeleopState() {
  const enabled = teleopEnabled.checked;
  const card = $("teleop-card");
  card.classList.toggle("teleop-enabled", enabled);
  $("teleop-state").textContent = enabled ? "ENABLED" : "DISABLED";
  $("teleop-state").className = "teleop-state " + (enabled ? "enabled" : "disabled");
}

function keyForEvent(event) {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName)) return null;
  const key = event.key.toLowerCase();
  return teleopButtons.has(key) ? key : null;
}

document.querySelectorAll(".teleop-grid button").forEach((button) => {
  const start = (event) => {
    event.preventDefault();
    startTeleop(button);
  };
  const end = (event) => {
    event.preventDefault();
    stopTeleop();
  };
  button.addEventListener("pointerdown", start);
  button.addEventListener("pointerup", end);
  button.addEventListener("pointercancel", end);
  button.addEventListener("pointerleave", (event) => {
    if (event.buttons) end(event);
  });
});

window.addEventListener("keydown", (event) => {
  const key = keyForEvent(event);
  if (!key || !teleopEnabled.checked || pressedKeys.has(key)) return;
  event.preventDefault();
  pressedKeys.add(key);
  startTeleop(teleopButtons.get(key));
});

window.addEventListener("keyup", (event) => {
  const key = keyForEvent(event);
  if (!key) return;
  pressedKeys.delete(key);
  stopTeleop();
});

window.addEventListener("blur", () => {
  pressedKeys.clear();
  stopTeleop();
});
teleopEnabled.addEventListener("change", () => {
  updateTeleopState();
  if (!teleopEnabled.checked) stopTeleop(true);
});
updateTeleopState();

$("connect-button").addEventListener("click", connectRobot);
$("disconnect-button").addEventListener("click", disconnectRobot);
$("refresh-robots").addEventListener("click", refreshRobots);
robotSelect.addEventListener("change", () => {
  updateManualAddressVisibility(true);
  updateRobotPingStatuses();
});
$("apply-video").addEventListener("click", applyVideoSettings);
$("run-button").addEventListener("click", startProgram);
$("stop-button").addEventListener("click", stopProgram);
$("reset-lights-button").addEventListener("click", () => {
  jsonRequest("/api/lights/reset", {method: "POST"})
    .then(() => setMessage("Lights reset"))
    .catch((error) => setMessage(error.message, true));
});
$("save-button").addEventListener("click", downloadProgram);
$("load-library-button").addEventListener("click", loadLibraryDemo);
$("save-library-button").addEventListener("click", saveLibraryDemo);
$("load-button").addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) loadProgramFile(fileInput.files[0]);
  fileInput.value = "";
});
$("clear-button").addEventListener("click", () => {
  if (window.confirm("Clear all blocks?")) workspace.clear();
});

async function pollStatus() {
  if (statusRequestInFlight) return;
  statusRequestInFlight = true;
  try {
    const data = await jsonRequest("/api/status");
    const connection = data.connection || {};
    const lamp = $("quality-lamp");
    lamp.className = "quality-lamp " + (connection.health || "red");
    lamp.title = connection.health_text || "Offline";
    $("quality-text").textContent = connection.health_text || "Offline";
    $("connection-status").textContent = data.connected ? "Connected" : "Disconnected";
    $("connection-status").className = "status-pill " + (data.connected ? "connected" : "");
    $("target-label").textContent = data.url || "not connected";
    $("video-rate").textContent = (connection.video_hz || 0) + " fps";
    $("telemetry-rate").textContent = (connection.telemetry_hz || 0) + " msgs/s";
    $("command-latency").textContent = connection.last_command_ms == null
      ? "cmd —"
      : "cmd " + connection.last_command_ms + " ms";
    $("telemetry").textContent = data.telemetry && data.telemetry.distance_cm !== undefined
      ? "dist " + data.telemetry.distance_cm + " cm"
      : "dist —";
    updateProgram(data.program || {});
  } catch (_) {
    const lamp = $("quality-lamp");
    lamp.className = "quality-lamp red";
    $("quality-text").textContent = "App offline";
  } finally {
    statusRequestInFlight = false;
  }
}

setInterval(pollStatus, 250);
pollStatus();
refreshRobots();
setInterval(updateRobotPingStatuses, 30_000);
setInterval(refreshRobots, 5 * 60 * 1000);
refreshLibrary().catch((error) => setMessage("Demo library: " + error.message, true));

// ---- Python mode: Monaco editor kept in sync with the blocks ----
const MONACO_BASE = "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min";
const COLOUR_CHOICES = "red,green,blue,yellow,white,purple";
const PYTHON_API = [
  ["forward", "forward(seconds=${1:2}, power=${2:60})", "Drive forward for some seconds at a power from 0 to 100."],
  ["backward", "backward(seconds=${1:2}, power=${2:60})", "Drive backward for some seconds."],
  ["turn_left", "turn_left(seconds=${1:1}, power=${2:60})", "Spin left on the spot."],
  ["turn_right", "turn_right(seconds=${1:1}, power=${2:60})", "Spin right on the spot."],
  ["turn_around", "turn_around(seconds=${1:1.5}, power=${2:60})", "Spin around on the spot."],
  ["drive", "drive(\"${1|forward,backward,left,right|}\", seconds=${2:1}, power=${3:60})", "Drive in a direction."],
  ["wait", "wait(${1:1})", "Do nothing for some seconds."],
  ["stop", "stop()", "Stop the motors."],
  ["take_picture", "take_picture()", "Return a BGR NumPy image from the camera."],
  ["show_in_live_camera", "show_in_live_camera(${1:image})", "Show a grayscale or BGR OpenCV image in the camera panel."],
  ["scan_robot_qr", "scan_robot_qr()", "Return a robot name such as trilo-09 from its Lincoln QR code, or an empty string."],
  ["sees_colour", "sees_colour(\"${1|" + COLOUR_CHOICES + "|}\", tolerance=${2:18}, min_area=${3:500})", "Block-friendly OpenCV HSV and contour check."],
  ["distance", "distance()", "Distance sensor reading in cm (nan if it could not be read)."],
  ["button_pressed", "button_pressed(\"${1|A,B,X,Y|}\")", "True while a button on the robot is held down."],
  ["wait_until", "wait_until(lambda: ${1:distance() < 20})", "Pause until the condition is true."],
  ["set_lights", "set_lights(\"${1|" + COLOUR_CHOICES + "|}\")", "Set the underlights to a colour."],
  ["lights_off", "lights_off()", "Turn the underlights off."],
  ["flash_lights", "flash_lights(\"${1|" + COLOUR_CHOICES + "|}\", times=${2:3})", "Flash the underlights."],
  ["set_button_light", "set_button_light(\"${1|A,B,X,Y|}\", ${2:1})", "Set a button LED brightness from 0 to 1."],
  ["count", "count(${1:1}, ${2:5})", "Count from the first number to the last, both included: for i in count(1, 5)."]
];

const blocksPane = $("blockly-workspace");
const pythonPane = $("python-pane");
const tabs = {blocks: $("tab-blocks"), python: $("tab-python")};
const syncLabel = $("python-sync");
const ranchModal = $("ranch-modal");

let mode = "blocks";
let editor = null;
let lastBlockPython = "";
let lastWorkingPython = "";
let generateTimer = null;
let generateTicket = 0;
let checkTimer = null;
let checkTicket = 0;
let switching = false;
let syncingWorkspace = false;
let syncingEditor = false;

function setSync(kind, text) {
  syncLabel.className = "python-sync " + kind;
  syncLabel.textContent = text;
}

function createEditor() {
  editor = monaco.editor.create($("python-editor"), {
    value: lastBlockPython,
    language: "python",
    automaticLayout: true,
    minimap: {enabled: false},
    scrollBeyondLastLine: false,
    fontSize: 14,
    tabSize: 4,
    insertSpaces: true
  });
  monaco.languages.registerCompletionItemProvider("python", {
    provideCompletionItems(model, position) {
      const word = model.getWordUntilPosition(position);
      const range = {
        startLineNumber: position.lineNumber, endLineNumber: position.lineNumber,
        startColumn: word.startColumn, endColumn: word.endColumn
      };
      return {
        suggestions: PYTHON_API.map(([label, insertText, documentation]) => ({
          label, insertText, documentation, range,
          kind: monaco.languages.CompletionItemKind.Function,
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet
        }))
      };
    }
  });
  editor.onDidChangeModelContent(scheduleCheck);
  editor.addAction({
    id: "format-document-black",
    label: "Format document (Black)",
    keybindings: [monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyI],
    contextMenuGroupId: "1_modification",
    run: formatDocument
  });
  setSync("ok", "Blocks can show this code");
}

async function formatDocument() {
  if (!editor) return;
  try {
    const result = await jsonRequest("/api/python/format", {
      method: "POST",
      body: JSON.stringify({code: editor.getValue()})
    });
    if (result.code !== editor.getValue()) editor.setValue(result.code);
    setMessage("Formatted document with Black");
  } catch (error) {
    setMessage("Format document: " + error.message, true);
  }
}

function loadMonaco() {
  window.MonacoEnvironment = {
    getWorkerUrl: () => "data:text/javascript;charset=utf-8," + encodeURIComponent(
      "self.MonacoEnvironment = {baseUrl: '" + MONACO_BASE + "/'};" +
      "importScripts('" + MONACO_BASE + "/vs/base/worker/workerMain.js');"
    )
  };
  require.config({paths: {vs: MONACO_BASE + "/vs"}});
  require(["vs/editor/editor.main"], createEditor,
    () => setSync("error", "The Python editor could not load (it needs internet access)"));
}

async function generatePython() {
  clearTimeout(generateTimer);
  const ticket = ++generateTicket;
  try {
    const data = await jsonRequest("/api/python/generate", {
      method: "POST",
      body: JSON.stringify({program: workspaceData()})
    });
    if (ticket !== generateTicket) return;
    lastBlockPython = data.code;
    lastWorkingPython = data.code;
    setEditorValue(data.code);
    if (mode === "python") setSync("ok", "Python and blocks are synced");
  } catch (error) {
    setMessage("Python view: " + error.message, true);
  }
}

function queueGeneratePython() {
  clearTimeout(generateTimer);
  generateTimer = setTimeout(generatePython, 200);
}

function setEditorValue(code) {
  if (!editor || editor.getValue() === code) return;
  syncingEditor = true;
  try {
    editor.setValue(code);
  } finally {
    syncingEditor = false;
  }
}

function syncWorkspaceFromPython(program, code) {
  clearTimeout(generateTimer);
  generateTicket++;
  replaceWorkspace(program);
  lastBlockPython = code;
  lastWorkingPython = code;
  setEditorValue(code);
  setSync("ok", "Python and blocks are synced");
}

workspace.addChangeListener((event) => {
  if (event.isUiEvent || syncingWorkspace) return;
  checkTicket++;
  if (mode === "python") setSync("warn", "Syncing blocks to Python…");
  queueGeneratePython();
});

function scheduleCheck() {
  clearTimeout(checkTimer);
  if (!syncingEditor && mode === "python") {
    generateTicket++;
    setSync("warn", "Syncing Python to blocks…");
    checkTimer = setTimeout(checkPython, 500);
  }
}

async function checkPython() {
  if (!editor) return;
  const ticket = ++checkTicket;
  const model = editor.getModel();
  const code = editor.getValue();
  let result = {ok: true, code};
  if (code !== lastBlockPython) {
    try {
      result = await jsonRequest("/api/python/to_blocks", {method: "POST", body: JSON.stringify({code})});
    } catch (_) {
      return;
    }
    if (ticket !== checkTicket) return;
  }
  if (result.ok) {
    monaco.editor.setModelMarkers(model, "blocks", []);
    const canonical = result.code || code;
    if (result.program && canonical !== lastBlockPython) {
      syncWorkspaceFromPython(result.program, canonical);
    } else {
      lastWorkingPython = canonical;
      setEditorValue(canonical);
      setSync("ok", "Python and blocks are synced");
    }
    return;
  }
  const line = Math.min(Math.max(result.line || 1, 1), model.getLineCount());
  monaco.editor.setModelMarkers(model, "blocks", [{
    severity: result.syntax ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
    message: result.message,
    startLineNumber: line, endLineNumber: line,
    startColumn: 1, endColumn: model.getLineMaxColumn(line)
  }]);
  setSync(
    result.syntax ? "error" : "warn",
    (result.syntax ? "" : "Too advanced for blocks — ") + "line " + line + ": " + result.message
  );
}

function showMode(next) {
  mode = next;
  blocksPane.hidden = next !== "blocks";
  pythonPane.hidden = next !== "python";
  for (const [name, button] of Object.entries(tabs)) {
    button.classList.toggle("active", name === next);
    button.setAttribute("aria-selected", String(name === next));
  }
  if (next === "blocks") {
    Blockly.svgResize(workspace);
  } else if (editor) {
    editor.layout();
    editor.focus();
    checkPython();
  }
}

function showRanchModal(result) {
  $("ranch-detail").textContent = (result.line ? "Line " + result.line + ": " : "") + (result.message || "");
  ranchModal.hidden = false;
  $("ranch-python").focus();
}

function closeRanchModal() {
  ranchModal.hidden = true;
  editor.focus();
}

async function leavePython() {
  if (!editor) return;
  const code = editor.getValue();
  if (code === lastBlockPython) {
    showMode("blocks");
    return;
  }
  let result;
  try {
    result = await jsonRequest("/api/python/to_blocks", {method: "POST", body: JSON.stringify({code})});
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

async function switchMode(target) {
  if (switching || target === mode) return;
  switching = true;
  try {
    if (target === "python") {
      if (!editor) {
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

tabs.blocks.addEventListener("click", () => switchMode("blocks"));
tabs.python.addEventListener("click", () => switchMode("python"));
$("ranch-python").addEventListener("click", closeRanchModal);
$("ranch-reset").addEventListener("click", async () => {
  ranchModal.hidden = true;
  setEditorValue(lastWorkingPython || lastBlockPython);
  await leavePython();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !ranchModal.hidden) closeRanchModal();
});

// ---- Quick start guide: one colourful step at a time ----
const HELP_SEEN_KEY = "trilobotBlocklyQuickStartSeen";
const helpModal = $("help-modal");
const helpSteps = [
  {emoji: "🔌", title: "Connect your robot", target: "#connect-button", body: "Type the robot address, then press <strong>Connect</strong>. The status dot tells you when the robot and camera are ready."},
  {emoji: "🧩", title: "Pick a block", target: ".blocklyToolboxDiv", body: "Open a colourful category on the left and drag out an action. Snap blocks together from top to bottom."},
  {emoji: "🔢", title: "Make it yours", target: "#run-button", body: "Edit the number sockets, then press <strong>Run</strong>. Keep one connected stack so the robot knows the order."},
  {emoji: "🐍", title: "Learn real Python", target: "#tab-python", body: "The Python tab shows the same robot API as code. You can type, use <code>cv2</code> and <code>numpy</code>, and run your program there."},
  {emoji: "🖥️", title: "Watch the terminal", target: "#terminal-tab", body: "Open the terminal in either tab to see <code>print()</code> output and status messages. It stays in the same place when you switch modes."},
  {emoji: "🎮", title: "Reset safely", target: "#teleop-enabled", body: "Only enable teleop when you need to reposition the robot. Hold a direction button or use <kbd>u i o</kbd> / <kbd>j k l</kbd> / <kbd>m , .</kbd>."},
];
let helpIndex = 0;

function renderHelpStep() {
  const step = helpSteps[helpIndex];
  $("help-progress").textContent = `${helpIndex + 1} / ${helpSteps.length}`;
  $("help-step").innerHTML = `<h3><span class="qsg-emoji" aria-hidden="true">${step.emoji}</span> ${step.title}</h3><p>${step.body}</p>`;
  $("help-arrow").textContent = "↓";
  $("help-prev").disabled = helpIndex === 0;
  $("help-next").textContent = helpIndex === helpSteps.length - 1 ? "Finish" : "Next →";
  document.querySelectorAll(".qsg-target").forEach((element) => element.classList.remove("qsg-target"));
  const target = document.querySelector(step.target);
  if (target) target.classList.add("qsg-target");
}

function openHelp() {
  helpIndex = 0;
  helpModal.hidden = false;
  renderHelpStep();
  $("help-next").focus();
}

function closeHelp() {
  helpModal.hidden = true;
  document.querySelectorAll(".qsg-target").forEach((element) => element.classList.remove("qsg-target"));
  try { localStorage.setItem(HELP_SEEN_KEY, "1"); } catch (_) {}
}

$("help-button").addEventListener("click", openHelp);
$("help-close").addEventListener("click", closeHelp);
$("help-prev").addEventListener("click", () => { if (helpIndex > 0) { helpIndex--; renderHelpStep(); } });
$("help-next").addEventListener("click", () => {
  if (helpIndex === helpSteps.length - 1) closeHelp();
  else { helpIndex++; renderHelpStep(); }
});
helpModal.addEventListener("click", (event) => {
  if (event.target === helpModal) closeHelp();
});
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

generatePython().then(loadMonaco);

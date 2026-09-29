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

function setMessage(message, error = false) {
  const element = $("program-status");
  element.textContent = message;
  element.classList.toggle("error-text", error);
}

function workspaceData() {
  return Blockly.serialization.workspaces.save(workspace);
}

function loadWorkspaceData(program, message) {
  workspace.clear();
  Blockly.serialization.workspaces.load(program, workspace);
  setMessage(message);
}

async function refreshLibrary(selectedName = "") {
  const data = await jsonRequest("/api/library");
  librarySelect.replaceChildren();
  for (const demo of data.demos || []) {
    const option = document.createElement("option");
    option.value = demo.name;
    option.textContent = demo.name;
    librarySelect.appendChild(option);
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
      body: JSON.stringify(workspaceData())
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
    $("vision-status").textContent = vision.status + area;
  }
}

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
  try {
    const data = await jsonRequest("/api/connect", {
      method: "POST",
      body: JSON.stringify({url: urlInput.value, video: videoSettings()})
    });
    setVideoSettings(data.video);
    setMessage("Connecting…");
    $("target-label").textContent = data.url || urlInput.value;
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
  $("teleop-state").textContent = enabled ? "ENABLED — sending" : "DISABLED";
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
    $("video-rate").textContent = (connection.video_hz || 0) + " fps video";
    $("telemetry-rate").textContent = (connection.telemetry_hz || 0) + " messages/s";
    $("command-latency").textContent = connection.last_command_ms == null
      ? "command —"
      : "command " + connection.last_command_ms + " ms";
    $("telemetry").textContent = data.telemetry && data.telemetry.distance_cm !== undefined
      ? "Distance " + data.telemetry.distance_cm + " cm"
      : "Distance —";
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
refreshLibrary().catch((error) => setMessage("Demo library: " + error.message, true));

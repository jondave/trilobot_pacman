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
    args0: [{type: "input_value", name: "COLOR", check: "Colour"}],
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
    type: "robot_set_lights",
    message0: "set underlights to %1",
    args0: [{type: "input_value", name: "COLOR", check: "Colour"}],
    previousStatement: null,
    nextStatement: null,
    colour: 315
  },
  {
    type: "robot_flash_lights",
    message0: "flash %1 lights %2 times",
    args0: [
      {type: "input_value", name: "COLOR", check: "Colour"},
      {type: "input_value", name: "TIMES", check: "Number"}
    ],
    message1: "on %1 seconds, off %2 seconds",
    args1: [
      {type: "input_value", name: "ON_SECONDS", check: "Number"},
      {type: "input_value", name: "OFF_SECONDS", check: "Number"}
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

const $ = (id) => document.getElementById(id);
const urlInput = $("robot-url");
const teleopEnabled = $("teleop-enabled");
const fileInput = $("program-file");
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
      workspace.clear();
      Blockly.serialization.workspaces.load(program, workspace);
      setMessage("Loaded trait file");
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

function sendTeleop(button) {
  if (!teleopEnabled.checked || !button) return;
  const payload = button.dataset.stop === "true"
    ? {stop: true}
    : {left: Number(button.dataset.left), right: Number(button.dataset.right)};
  postTeleop(payload);
}

function stopTeleop(force = false) {
  if (!force && !teleopEnabled.checked) return;
  postTeleop({stop: true});
  document.querySelectorAll(".teleop-grid button.active")
    .forEach((button) => button.classList.remove("active"));
}

function keyForEvent(event) {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName)) return null;
  const key = event.key.toLowerCase();
  return teleopButtons.has(key) ? key : null;
}

document.querySelectorAll(".teleop-grid button").forEach((button) => {
  const start = (event) => {
    event.preventDefault();
    button.classList.add("active");
    sendTeleop(button);
  };
  const end = (event) => {
    event.preventDefault();
    button.classList.remove("active");
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
  const button = teleopButtons.get(key);
  button.classList.add("active");
  sendTeleop(button);
});

window.addEventListener("keyup", (event) => {
  const key = keyForEvent(event);
  if (!key) return;
  pressedKeys.delete(key);
  teleopButtons.get(key).classList.remove("active");
  stopTeleop();
});

window.addEventListener("blur", () => {
  pressedKeys.clear();
  stopTeleop();
});
teleopEnabled.addEventListener("change", () => {
  if (!teleopEnabled.checked) stopTeleop(true);
});

$("connect-button").addEventListener("click", connectRobot);
$("disconnect-button").addEventListener("click", disconnectRobot);
$("apply-video").addEventListener("click", applyVideoSettings);
$("run-button").addEventListener("click", startProgram);
$("stop-button").addEventListener("click", stopProgram);
$("save-button").addEventListener("click", downloadProgram);
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

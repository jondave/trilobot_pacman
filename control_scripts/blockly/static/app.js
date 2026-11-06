/* Blockly Lab frontend: small, clear controls for students. */

Blockly.defineBlocksWithJsonArray([{
  type: "robot_forward",
  message0: "move forward for %1 seconds at %2% power",
  args0: [{
    type: "input_value",
    name: "SECONDS",
    check: "Number"
  }, {
    type: "input_value",
    name: "SPEED",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "robot_blocks",
  tooltip: "Drive straight ahead."
}, {
  type: "robot_backward",
  message0: "move backward for %1 seconds at %2% power",
  args0: [{
    type: "input_value",
    name: "SECONDS",
    check: "Number"
  }, {
    type: "input_value",
    name: "SPEED",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "robot_blocks"
}, {
  type: "robot_turn_left",
  message0: "turn left for %1 seconds at %2% power",
  args0: [{
    type: "input_value",
    name: "SECONDS",
    check: "Number"
  }, {
    type: "input_value",
    name: "SPEED",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "robot_blocks"
}, {
  type: "robot_turn_right",
  message0: "turn right for %1 seconds at %2% power",
  args0: [{
    type: "input_value",
    name: "SECONDS",
    check: "Number"
  }, {
    type: "input_value",
    name: "SPEED",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "robot_blocks"
}, {
  type: "robot_turn_around",
  message0: "turn around for %1 seconds at %2% power",
  args0: [{
    type: "input_value",
    name: "SECONDS",
    check: "Number"
  }, {
    type: "input_value",
    name: "SPEED",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "robot_blocks"
}, {
  type: "robot_drive_for",
  message0: "drive %1 for %2 seconds at %3% power",
  args0: [{
    type: "field_dropdown",
    name: "DIRECTION",
    options: [
      ["forward", "FORWARD"],
      ["backward", "BACKWARD"],
      ["left", "LEFT"],
      ["right", "RIGHT"]
    ]
  }, {
    type: "input_value",
    name: "SECONDS",
    check: "Number"
  }, {
    type: "input_value",
    name: "SPEED",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "robot_blocks"
}, {
  type: "robot_take_picture",
  message0: "take a picture",
  previousStatement: null,
  nextStatement: null,
  style: "opencv_blocks",
  tooltip: "Take a snapshot for the OpenCV blocks."
}, {
  type: "opencv_camera_image",
  message0: "camera image",
  output: "Image",
  style: "opencv_blocks",
  tooltip: "Take a BGR image from the live robot camera."
}, {
  type: "opencv_to_hsv",
  message0: "convert %1 %2",
  args0: [{
    type: "input_value",
    name: "IMAGE",
    check: "Image"
  }, {
    type: "field_dropdown",
    name: "CONVERSION",
    options: [
      ["BGR → HSV", "BGR_TO_HSV"],
      ["HSV → BGR", "HSV_TO_BGR"]
    ]
  }],
  output: "Image",
  style: "opencv_blocks",
  tooltip: "Convert an OpenCV BGR image to HSV."
}, {
  type: "opencv_blur",
  message0: "blur %1 with a %2 pixel kernel",
  args0: [{
    type: "input_value",
    name: "IMAGE",
    check: "Image"
  }, {
    type: "input_value",
    name: "KERNEL",
    check: "Number"
  }],
  output: "Image",
  style: "opencv_blocks",
  tooltip: "Smooth an image before making a mask. Use an odd kernel such as 5."
}, {
  type: "opencv_box_blur",
  message0: "box blur %1 with a %2 pixel kernel",
  args0: [{
    type: "input_value",
    name: "IMAGE",
    check: "Image"
  }, {
    type: "input_value",
    name: "KERNEL",
    check: "Number"
  }],
  output: "Image",
  style: "opencv_blocks",
  tooltip: "Apply OpenCV's simple box blur. Use an odd kernel such as 5."
}, {
  type: "opencv_hsv_value",
  message0: "HSV value: H %1  S %2  V %3",
  args0: [{
    type: "input_value",
    name: "H",
    check: "Number"
  }, {
    type: "input_value",
    name: "S",
    check: "Number"
  }, {
    type: "input_value",
    name: "V",
    check: "Number"
  }],
  output: "HSV",
  style: "opencv_blocks",
  tooltip: "One HSV colour bound. H is 0–179; S and V are 0–255."
}, {
  type: "opencv_hsv_mask",
  message0: "make HSV mask from %1",
  args0: [{
    type: "input_value",
    name: "IMAGE",
    check: "Image"
  }],
  message1: "low HSV bound %1",
  args1: [{
    type: "input_value",
    name: "LOW",
    check: "HSV"
  }],
  message2: "high HSV bound %1",
  args2: [{
    type: "input_value",
    name: "HIGH",
    check: "HSV"
  }],
  output: "Image",
  style: "opencv_blocks",
  tooltip: "Keep pixels inside these HSV bounds and make a black-and-white mask."
}, {
  type: "opencv_count_nonzero",
  message0: "count white pixels in %1",
  args0: [{
    type: "input_value",
    name: "IMAGE",
    check: "Image"
  }],
  output: "Number",
  style: "opencv_blocks",
  tooltip: "Count the white pixels in a mask."
}, {
  type: "opencv_mask_or",
  message0: "combine masks %1 and %2",
  args0: [{
    type: "input_value",
    name: "IMAGE1",
    check: "Image"
  }, {
    type: "input_value",
    name: "IMAGE2",
    check: "Image"
  }],
  output: "Image",
  style: "opencv_blocks",
  tooltip: "Combine two black-and-white masks with OpenCV bitwise OR."
}, {
  type: "robot_scan_qr",
  message0: "scan robot QR code",
  output: "String",
  style: "opencv_blocks",
  tooltip: "Return the robot name such as trilo-xx from a Lincoln robot QR code."
}, {
  type: "robot_show_live_camera",
  message0: "show %1 in live camera",
  args0: [{
    type: "input_value",
    name: "IMAGE",
    check: "Image"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "opencv_blocks",
  tooltip: "Show an image or mask variable in the live camera panel. Leave it empty to show a fresh picture."
}, {
  type: "robot_if_color",
  message0: "OpenCV: if the picture contains %1",
  args0: [{
    type: "field_dropdown",
    name: "COLOR",
    options: [
      ["red", "#ff0000"],
      ["green", "#00ff00"],
      ["blue", "#0000ff"],
      ["yellow", "#ffff00"],
      ["white", "#ffffff"],
      ["purple", "#ff00ff"]
    ]
  }],
  message1: "colour tolerance %1 degrees, minimum area %2",
  args1: [{
    type: "input_value",
    name: "TOLERANCE",
    check: "Number"
  }, {
    type: "input_value",
    name: "MIN_AREA",
    check: "Number"
  }],
  message2: "then do %1",
  args2: [{
    type: "input_statement",
    name: "THEN"
  }],
  message3: "otherwise do %1",
  args3: [{
    type: "input_statement",
    name: "ELSE"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "opencv_blocks",
  tooltip: "Uses basic OpenCV HSV colour detection."
}, {
  type: "robot_if_distance",
  message0: "if distance is %1 %2 cm",
  args0: [{
    type: "field_dropdown",
    name: "OPERATOR",
    options: [
      ["less than", "LESS_THAN"],
      ["more than", "MORE_THAN"]
    ]
  }, {
    type: "input_value",
    name: "CENTIMETRES",
    check: "Number"
  }],
  message1: "then do %1",
  args1: [{
    type: "input_statement",
    name: "THEN"
  }],
  message2: "otherwise do %1",
  args2: [{
    type: "input_statement",
    name: "ELSE"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "sensor_blocks",
  tooltip: "Reads the robot's distance sensor."
}, {
  type: "robot_underlights_on",
  message0: "turn on underlights",
  previousStatement: null,
  nextStatement: null,
  style: "light_blocks",
  tooltip: "Turn the robot underlights on white."
}, {
  type: "robot_underlights_off",
  message0: "turn off underlights",
  previousStatement: null,
  nextStatement: null,
  style: "light_blocks",
  tooltip: "Turn all underlights off."
}, {
  type: "robot_lights_red",
  message0: "set lights red",
  previousStatement: null,
  nextStatement: null,
  style: "colour_red_blocks"
}, {
  type: "robot_lights_green",
  message0: "set lights green",
  previousStatement: null,
  nextStatement: null,
  style: "colour_green_blocks"
}, {
  type: "robot_lights_blue",
  message0: "set lights blue",
  previousStatement: null,
  nextStatement: null,
  style: "colour_blue_blocks"
}, {
  type: "robot_lights_yellow",
  message0: "set lights yellow",
  previousStatement: null,
  nextStatement: null,
  style: "colour_yellow_blocks"
}, {
  type: "robot_lights_white",
  message0: "set lights white",
  previousStatement: null,
  nextStatement: null,
  style: "colour_white_blocks"
}, {
  type: "robot_lights_purple",
  message0: "set lights purple",
  previousStatement: null,
  nextStatement: null,
  style: "colour_purple_blocks"
}, {
  type: "robot_colour_red",
  message0: "red",
  output: "Colour",
  style: "colour_red_blocks"
}, {
  type: "robot_colour_green",
  message0: "green",
  output: "Colour",
  style: "colour_green_blocks"
}, {
  type: "robot_colour_blue",
  message0: "blue",
  output: "Colour",
  style: "colour_blue_blocks"
}, {
  type: "robot_colour_yellow",
  message0: "yellow",
  output: "Colour",
  style: "colour_yellow_blocks"
}, {
  type: "robot_colour_white",
  message0: "white",
  output: "Colour",
  style: "colour_white_blocks"
}, {
  type: "robot_colour_purple",
  message0: "purple",
  output: "Colour",
  style: "colour_purple_blocks"
}, {
  type: "robot_set_lights",
  message0: "set lights to %1",
  args0: [{
    type: "field_dropdown",
    name: "COLOR",
    options: [
      ["red", "#ff0000"],
      ["green", "#00ff00"],
      ["blue", "#0000ff"],
      ["yellow", "#ffff00"],
      ["white", "#ffffff"],
      ["purple", "#ff00ff"]
    ]
  }],
  previousStatement: null,
  nextStatement: null,
  style: "light_blocks"
}, {
  type: "robot_flash_lights",
  message0: "flash %1 for %2 times",
  args0: [{
    type: "field_dropdown",
    name: "COLOR",
    options: [
      ["red", "#ff0000"],
      ["green", "#00ff00"],
      ["blue", "#0000ff"],
      ["yellow", "#ffff00"],
      ["white", "#ffffff"],
      ["purple", "#ff00ff"]
    ]
  }, {
    type: "input_value",
    name: "TIMES",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "light_blocks"
}, {
  type: "robot_button_light",
  message0: "set button %1 brightness to %2",
  args0: [{
    type: "field_dropdown",
    name: "BUTTON",
    options: [
      ["A", "A"],
      ["B", "B"],
      ["X", "X"],
      ["Y", "Y"]
    ]
  }, {
    type: "input_value",
    name: "BRIGHTNESS",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "light_blocks"
}, {
  type: "robot_repeat",
  message0: "repeat %1 times",
  args0: [{
    type: "input_value",
    name: "TIMES",
    check: "Number"
  }],
  message1: "do %1",
  args1: [{
    type: "input_statement",
    name: "DO"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "loop_blocks",
  tooltip: "Repeat the blocks inside this loop."
}, {
  type: "robot_wait",
  message0: "wait %1 seconds",
  args0: [{
    type: "input_value",
    name: "SECONDS",
    check: "Number"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "robot_blocks"
}, {
  type: "robot_stop",
  message0: "stop the robot",
  previousStatement: null,
  nextStatement: null,
  style: "stop_blocks"
}, {
  type: "robot_print",
  message0: "print %1 %2",
  args0: [{
    type: "input_value",
    name: "VALUE"
  }, {
    type: "input_value",
    name: "VALUE2"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "debug_blocks",
  tooltip: "Write a value to the terminal."
}, {
  type: "robot_wait_until",
  message0: "wait until %1",
  args0: [{
    type: "input_value",
    name: "CONDITION",
    check: "Boolean"
  }],
  previousStatement: null,
  nextStatement: null,
  style: "robot_blocks",
  tooltip: "Pause the program until the condition is true."
}, {
  type: "robot_distance_condition",
  message0: "distance is %1 %2 cm",
  args0: [{
    type: "field_dropdown",
    name: "OPERATOR",
    options: [
      ["less than", "LESS_THAN"],
      ["more than", "MORE_THAN"]
    ]
  }, {
    type: "input_value",
    name: "CENTIMETRES",
    check: "Number"
  }],
  output: "Boolean",
  style: "sensor_blocks",
  tooltip: "True when the distance sensor reading matches."
}, {
  type: "robot_distance_value",
  message0: "distance in cm",
  output: "Number",
  style: "sensor_blocks",
  tooltip: "Read the robot's distance sensor."
}, {
  type: "robot_button_pressed",
  message0: "robot button %1 is pressed",
  args0: [{
    type: "field_dropdown",
    name: "BUTTON",
    options: [
      ["A", "A"],
      ["B", "B"],
      ["X", "X"],
      ["Y", "Y"]
    ]
  }],
  output: "Boolean",
  style: "sensor_blocks",
  tooltip: "True while the button on the robot is held down."
}]);

const hex = {
  orange: "#e49a32", green: "#2fb477", blue: "#3478f6", purple: "#9b62d7",
  pink: "#d957a7", red: "#e75a5a", teal: "#36a890", slate: "#5c81a6", yellow: "#d9b21f", grey: "#8f9bb0"
};
const blockStyle = colour => ({ colourPrimary: colour });
const labTheme = Blockly.Theme.defineTheme("trilobot_lab", {
  name: "trilobot_lab",
  base: Blockly.Themes.Classic,
  blockStyles: {
    robot_blocks: blockStyle(hex.orange),
    loop_blocks: blockStyle(hex.green),
    stop_blocks: blockStyle(hex.red),
    debug_blocks: blockStyle(hex.blue),
    opencv_blocks: blockStyle(hex.purple),
    sensor_blocks: blockStyle(hex.teal),
    light_blocks: blockStyle(hex.pink),
    colour_red_blocks: blockStyle(hex.red),
    colour_green_blocks: blockStyle(hex.green),
    colour_blue_blocks: blockStyle(hex.blue),
    colour_yellow_blocks: blockStyle(hex.yellow),
    colour_white_blocks: blockStyle(hex.grey),
    colour_purple_blocks: blockStyle(hex.purple),
    logic_blocks: blockStyle(hex.slate),
    math_blocks: blockStyle(hex.green),
    variable_blocks: blockStyle(hex.orange)
  },
  categoryStyles: {
    robot_category: { colour: hex.orange },
    loop_category: { colour: hex.green },
    logic_category: { colour: hex.slate },
    opencv_category: { colour: hex.purple },
    sensor_category: { colour: hex.teal },
    debug_category: { colour: hex.blue },
    light_category: { colour: hex.pink },
    math_category: { colour: hex.green },
    variable_category: { colour: hex.orange }
  }
});

const workspace = Blockly.inject("blockly-workspace", {
  ...(window.BLOCKLY_FROM_CDN ? {} : {media: "/static/vendor/blockly/media/"}),
  toolbox: document.getElementById("toolbox"),
  theme: labTheme,
  trashcan: true,
  move: {
    scrollbars: true,
    drag: true,
    wheel: true
  },
  zoom: {
    controls: true,
    wheel: true,
    startScale: 0.85,
    maxScale: 1.25,
    minScale: 0.55
  }
});

// The flyout owns this setting; setting it in Blockly.inject is ignored by
// Blockly 11's category toolbox.
workspace.getToolbox()?.getFlyout()?.setAutoClose(false);

const blockDrawerCloseButton = document.getElementById("close-block-drawer");
function getBlockDrawerBounds(flyout) {
  const editorArea = document.querySelector(".editor-area");
  if (!editorArea) return null;

  const editorBounds = editorArea.getBoundingClientRect();
  const flyoutElement = document.querySelector("#blockly-workspace .blocklyFlyout");
  const renderedBounds = flyoutElement?.getBoundingClientRect();
  if (renderedBounds?.width > 0 && renderedBounds?.height > 0) {
    return {
      left: renderedBounds.left,
      right: renderedBounds.right,
      top: renderedBounds.top,
      bottom: renderedBounds.bottom,
      editorBounds
    };
  }

  // Keep the controls usable if Blockly changes the flyout SVG class name.
  const toolboxBounds = document.querySelector(".blocklyToolboxDiv")?.getBoundingClientRect();
  const width = flyout.getWidth() || 260;
  const left = toolboxBounds?.right ?? editorBounds.left;
  return {
    left,
    right: left + width,
    top: editorBounds.top,
    bottom: editorBounds.bottom,
    editorBounds
  };
}

function syncBlockDrawerCloseButton() {
  const flyout = workspace.getToolbox()?.getFlyout();
  const bounds = flyout && getBlockDrawerBounds(flyout);
  if (!flyout?.isVisible() || !bounds) {
    blockDrawerCloseButton.hidden = true;
    return;
  }

  blockDrawerCloseButton.hidden = false;
  const drawerRight = bounds.right - bounds.editorBounds.left;
  const drawerLeft = bounds.left - bounds.editorBounds.left;
  const buttonWidth = blockDrawerCloseButton.offsetWidth;
  const editorWidth = bounds.editorBounds.width;
  const useLeftEdge = drawerRight + buttonWidth > editorWidth;
  const buttonLeft = useLeftEdge
    ? Math.max(0, drawerLeft - buttonWidth + 1)
    : drawerRight - 1;
  blockDrawerCloseButton.classList.toggle("left-edge", useLeftEdge);
  blockDrawerCloseButton.style.left = `${buttonLeft}px`;
  blockDrawerCloseButton.style.top = `${bounds.top - bounds.editorBounds.top + 8}px`;
}

blockDrawerCloseButton.addEventListener("click", (event) => {
  event.preventDefault();
  event.stopPropagation();
  const toolbox = workspace.getToolbox();
  toolbox?.setSelectedItem(null);
  toolbox?.getFlyout()?.hide();
  blockDrawerCloseButton.hidden = true;
});

workspace.addChangeListener((event) => {
  if (event.type === Blockly.Events.TOOLBOX_ITEM_SELECT) {
    setTimeout(syncBlockDrawerCloseButton, 0);
  }
});

workspace.registerButtonCallback("CREATE_VARIABLE", (button) => {
  Blockly.Variables.createVariableButtonHandler(button.getTargetWorkspace());
});
window.addEventListener("resize", () => {
  Blockly.svgResize(workspace);
  requestAnimationFrame(syncBlockDrawerCloseButton);
});
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
  setTimeout(() => {
    reflowToolbox();
    syncBlockDrawerCloseButton();
  }, 0);
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
  green: {
    icon: "🟢",
    label: "Seen within 10 minutes"
  },
  orange: {
    icon: "🟠",
    label: "Not seen for more than 10 minutes"
  },
  red: {
    icon: "🔴",
    label: "Not seen for more than 30 minutes"
  }
};

async function jsonRequest(path, options = {}) {
  const requestOptions = {
    ...options
  };
  if (requestOptions.body) {
    requestOptions.headers = {
      "Content-Type": "application/json",
      ...(requestOptions.headers || {})
    };
  }
  const response = await fetch(path, requestOptions);
  let data = {};
  try {
    data = await response.json();
  } catch (_) {}
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
    const result = await jsonRequest("/api/library/" + encodeURIComponent(cleanName), {
      method: "POST",
      body: JSON.stringify(mode === "python" && editor ? {
        python: editor.getValue()
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

function updateProgram(program) {
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

// Terminal = program output followed by connection events (bounded).
let programOutputText = "";
let renderedTerminalKey = "";
const eventLog = [];
let lastEventId = 0;
const MAX_EVENT_LINES = 100;

function clock(epochSeconds, withSeconds = false) {
  if (!Number.isFinite(Number(epochSeconds)) || epochSeconds === null) return "";
  const date = new Date(Number(epochSeconds) * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return pad(date.getHours()) + ":" + pad(date.getMinutes()) +
    (withSeconds ? ":" + pad(date.getSeconds()) : "");
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

function ingestEvents(events) {
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
$("terminal-clear").addEventListener("click", () => {
  eventLog.length = 0;
  programOutputText = "";
  renderedTerminalKey = "";
  $("terminal-output").textContent = "";
});

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

const cameraImage = document.querySelector("#camera-card .stage img");

function reloadCameraFeed() {
  if (!cameraImage) return;
  const base = cameraImage.src.split("?")[0];
  cameraImage.src = base + "?t=" + Date.now();
}

// Remembered robot-given identities, kept so a refresh or Wi-Fi drop resumes
// the same session. Shape: {<url>: {session, resume, robot}}.
const SESSIONS_KEY = "trilobot.sessions";

function loadSessions() {
  try {
    const parsed = JSON.parse(localStorage.getItem(SESSIONS_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (_) {
    return {};
  }
}

function rememberSession(conn) {
  if (!conn || !conn.resume || !conn.url) return;
  try {
    const sessions = loadSessions();
    const current = sessions[conn.url] || {};
    if (current.resume === conn.resume && current.session === conn.session) return;
    sessions[conn.url] = {
      session: conn.session || current.session || null,
      resume: conn.resume,
      robot: conn.robot || current.robot || null
    };
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions));
  } catch (_) {}
}

function selectedAddress() {
  return robotSelect.value === MANUAL_ROBOT_VALUE ? urlInput.value.trim() : robotSelect.value;
}

async function connectRobot(force = false, urlOverride = "") {
  const address = urlOverride || selectedAddress();
  if (!address) {
    setMessage("Choose a robot or enter a manual WebSocket address", true);
    return;
  }
  const stored = loadSessions()[address] || {};
  const choice = robotChoices.find((robot) => robot.url === address);
  const robotName = (choice && choice.name) || stored.robot || (lastConnection && lastConnection.robot);
  const body = {
    url: address,
    video: videoSettings(),
    force: force === true
  };
  if (stored.resume) body.resume = stored.resume;
  if (robotName) body.robot_name = robotName;
  try {
    const data = await jsonRequest("/api/connect", {
      method: "POST",
      body: JSON.stringify(body)
    });
    setVideoSettings(data.video);
    setMessage("Connecting…");
  } catch (error) {
    setMessage(error.message, true);
  }
}

async function disconnectRobot() {
  try {
    await jsonRequest("/api/disconnect", {
      method: "POST"
    });
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
      body: JSON.stringify({
        python: editor ? editor.getValue() : ""
      })
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

function postTeleop(payload) {
  fetch("/api/teleop", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  }).catch((error) => setMessage("Teleop: " + error.message, true));
}

let teleopTimer = null;
let activeTeleopButton = null;

function sendTeleop(button) {
  if (!teleopEnabled.checked || !button) return;
  const payload = button.dataset.stop === "true" ? {
    stop: true
  } : {
    left: Number(button.dataset.left),
    right: Number(button.dataset.right)
  };
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
  postTeleop({
    stop: true
  });
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
  jsonRequest("/api/lights/reset", {
      method: "POST"
    })
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

let statusFailures = 0;
let lastConnection = null;
let programRunning = false;

const STATE_LABELS = {
  idle: "Disconnected",
  connecting: "Connecting…",
  connected: "Connected",
  weak: "Weak signal",
  reconnecting: "Reconnecting…",
  taken_over: "Taken over",
  busy: "Robot busy",
  robot_offline: "Robot offline",
  app_down: "App not running"
};
const ALERT_STATES = ["reconnecting", "taken_over", "busy", "robot_offline", "app_down"];
const BASE_TITLE = document.title;
const banner = $("conn-banner");
const bannerIcon = banner.querySelector(".conn-icon");
const bannerMessage = banner.querySelector(".conn-message");
const bannerActions = banner.querySelector(".conn-actions");
let bannerState = null;
let previousState = null;

function focusRobotChooser() {
  robotSelect.focus();
}

function bannerContent(state, conn) {
  const robot = conn.robot || "the robot";
  const holder = conn.holder || "Another user";
  const since = clock(conn.since);
  const at = since ? " at " + since : "";
  const retry = {label: "Retry now", run: () => connectRobot(false, conn.url || "")};
  const choose = {label: "Choose another robot", run: focusRobotChooser};
  switch (state) {
    case "connected":
      return {kind: "info", icon: "✔", text: conn.session ?
        "You are " + conn.session + " on " + robot : conn.message || "Connected to " + robot};
    case "weak":
      return {kind: "warning", icon: "⚠", text: "Weak signal. The video and controls may lag."};
    case "reconnecting":
      return {kind: "warning", icon: "⟳", text: "Connection lost. Reconnecting" +
        (conn.session ? " as " + conn.session : "") + "… (attempt " + (conn.attempt || 1) + ")",
        actions: [retry]};
    case "taken_over":
      return {kind: "danger", icon: "⛔", text: holder + " took over " + robot + at + "." +
        (conn.program_stopped ? " Your program was stopped." : ""),
        actions: [choose, {label: "Take it back", run: () => connectRobot(true, conn.url || "")}]};
    case "busy":
      return {kind: "muted", icon: "ℹ", text: (conn.robot || "The robot") + " is being used by " + holder +
        (since ? " (since " + since + ")" : "") + ".",
        actions: [choose, {label: "Take over", run: () => connectRobot(true, conn.url || "")}]};
    case "robot_offline":
      return {kind: "danger", icon: "⛔", text: "Can't reach " + robot +
        ". Is it switched on and on the same Wi-Fi?",
        actions: [{label: "Retry", run: () => connectRobot(false, conn.url || "")}]};
    case "app_down":
      return {kind: "danger", icon: "⛔", text: "The Trilobot app on your computer isn't running. " +
        "Restart it (see the Get Started guide)."};
    case "connecting":
      return {kind: "muted", icon: "…", text: conn.message || "Connecting to " + robot + "…"};
    default:
      return null;
  }
}

function renderBanner(state, conn) {
  const content = bannerContent(state, conn);
  if (!content) {
    banner.hidden = true;
    bannerState = null;
    return;
  }
  const danger = content.kind === "danger";
  const key = state + "|" + (conn.url || "") + "|" + (conn.holder || "");
  banner.hidden = false;
  banner.className = "conn-banner is-" + content.kind;
  banner.setAttribute("aria-live", danger ? "assertive" : "polite");
  bannerIcon.textContent = content.icon;
  bannerMessage.textContent = content.text;
  if (key === bannerState) return;
  bannerState = key;
  bannerActions.replaceChildren();
  for (const action of content.actions || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = action.label;
    button.addEventListener("click", action.run);
    bannerActions.appendChild(button);
  }
}

function renderVideo(state, conn) {
  const live = state === "connected" || state === "weak";
  const age = conn.last_frame_age;
  const frozen = live && typeof age === "number" && age > 2;
  const stale = !live || frozen;
  const overlay = $("video-overlay");
  let text = "";
  if (frozen) {
    text = "No new picture for " + Math.round(age) + "s";
  } else if (!live) {
    if (state === "reconnecting" || state === "connecting") text = "Reconnecting…";
    else if (state === "idle" || state === "app_down") text = "Not connected";
    else text = "Disconnected";
    if (typeof age === "number" && text !== "Not connected") {
      text += " · last picture " + (age < 2 ? "just now" : Math.round(age) + "s ago");
    }
  }
  overlay.hidden = !stale;
  overlay.textContent = text;
  const stage = document.querySelector("#camera-card .stage");
  stage.classList.toggle("is-stale", stale);
  // No real picture yet: hide the placeholder so its text doesn't clash with the overlay.
  stage.classList.toggle("no-picture", stale && typeof age !== "number");
  if ((state === "connected") && previousState !== "connected" && previousState !== "weak") {
    reloadCameraFeed();
  }
}

function renderControls(state) {
  const canDrive = state === "connected" || state === "weak";
  $("run-button").disabled = !canDrive;
  // Stop is the safety button: always available, harmless when idle.
  $("stop-button").disabled = false;
  teleopEnabled.disabled = !canDrive;
  teleopButtons.forEach((button) => { button.disabled = !canDrive; });
  $("reset-lights-button").disabled = !canDrive;
  if (!canDrive && teleopEnabled.checked) {
    teleopEnabled.checked = false;
    updateTeleopState();
    stopTeleop(true);
  }
  const connectButton = $("connect-button");
  connectButton.textContent = canDrive ? "Connected" :
    state === "connecting" ? "Connecting…" :
    state === "reconnecting" ? "Reconnecting…" : "Connect";
  connectButton.disabled = canDrive || state === "connecting" || state === "reconnecting";
  $("disconnect-button").disabled = !["connected", "weak", "connecting", "reconnecting"].includes(state);
}

const LAMP_LABELS = {
  connected: "Connected",
  weak: "Weak signal",
  reconnecting: "Reconnecting",
  connecting: "Connecting",
  taken_over: "Taken over",
  busy: "Busy",
  robot_offline: "Robot offline",
  app_down: "App offline",
  idle: "Not connected"
};

function renderLamp(state, conn) {
  const lamp = $("quality-lamp");
  const colour = state === "connected" ? (conn.health || "green") :
    state === "weak" || state === "reconnecting" || state === "connecting" ? "orange" : "red";
  const label = LAMP_LABELS[state] || "Not connected";
  lamp.className = "quality-lamp " + colour;
  lamp.title = conn.health_text && state === "connected" ? label + " · " + conn.health_text : label;
  $("quality-text").textContent = label;
}

function renderConnection(conn) {
  const state = conn.state || "idle";
  const live = state === "connected" || state === "weak";
  lastConnection = conn;
  rememberSession(conn);
  const pill = $("connection-status");
  pill.textContent = live && conn.session ?
    STATE_LABELS[state] + " · " + conn.session : STATE_LABELS[state] || conn.message || state;
  pill.className = "status-pill " + (live ? "connected" : "");
  // Controls first: they matter most and must not wait on the rest.
  renderControls(state);
  renderLamp(state, conn);
  renderBanner(state, conn);
  renderVideo(state, conn);
  const title = (ALERT_STATES.includes(state) ? "⚠ " : "") + BASE_TITLE;
  if (document.title !== title) document.title = title;
  previousState = state;
}

async function pollStatus() {
  if (statusRequestInFlight) return;
  statusRequestInFlight = true;
  try {
    const data = await jsonRequest("/api/status");
    statusFailures = 0;
    const connection = data.connection || {};
    const program = data.program || {};
    programRunning = program.status === "running";
    ingestEvents(data.events);
    renderConnection({
      ...connection,
      state: connection.state || (data.connected ? "connected" : "idle")
    });
    $("video-rate").textContent = (connection.video_hz || 0) + " fps";
    $("telemetry-rate").textContent = (connection.telemetry_hz || 0) + " msgs/s";
    $("command-latency").textContent = connection.last_command_ms == null ?
      "cmd —" :
      "cmd " + connection.last_command_ms + " ms";
    $("telemetry").textContent = data.telemetry && data.telemetry.distance_cm !== undefined ?
      "dist " + data.telemetry.distance_cm + " cm" :
      "dist —";
    updateProgram(program);
  } catch (_) {
    statusFailures += 1;
    if (statusFailures >= 2) {
      programRunning = false;
      renderConnection({state: "app_down"});
    }
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
const MONACO_BASE = window.MONACO_FROM_CDN
  ? "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min"
  // Absolute: the worker is a data: URL with no base, so a bare path can't resolve.
  : new URL("/static/vendor/monaco/min", location.href).href;
const COLOUR_CHOICES = "red,green,blue,yellow,white,purple";
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
      body: JSON.stringify({
        code: editor.getValue()
      })
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
  require.config({
    paths: {
      vs: MONACO_BASE + "/vs"
    }
  });
  require(["vs/editor/editor.main"], createEditor,
    () => setSync("error", "The Python editor could not load (it needs internet access)"));
}

async function generatePython() {
  clearTimeout(generateTimer);
  const ticket = ++generateTicket;
  try {
    const data = await jsonRequest("/api/python/generate", {
      method: "POST",
      body: JSON.stringify({
        program: workspaceData()
      })
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
  let result = {
    ok: true,
    code
  };
  if (code !== lastBlockPython) {
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
    startLineNumber: line,
    endLineNumber: line,
    startColumn: 1,
    endColumn: model.getLineMaxColumn(line)
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
  $("ranch-detail").textContent = (result.line ? "Line " + result.line + ": " : "") + (result
    .message || "");
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
const helpHighlight = $("help-highlight");
const helpSteps = [{
  emoji: "🔌",
  title: "Connect to a robot",
  target: ".connection-controls",
  targetLabel: "Connection bar",
  targetHint: "Choose a robot, then press Connect.",
  body: "Select a robot by name and IP address. If it is not listed, choose <strong>Enter address manually…</strong> and edit the pre-filled address."
}, {
  emoji: "🧩",
  title: "Choose a block",
  target: ".blocklyToolboxDiv",
  targetLabel: "Block toolbox",
  targetHint: "Drag a block into the program area.",
  body: "Open a colourful category and drag out an action. The toolbox is your menu of robot, logic, and OpenCV blocks."
}, {
  emoji: "🔢",
  title: "Build the program",
  target: "#blockly-workspace",
  targetLabel: "Program workspace",
  targetHint: "Snap blocks together from top to bottom.",
  body: "Set the number sockets to values that suit your robot. Keep actions in one connected stack so they run in order."
}, {
  emoji: "📷",
  title: "Watch the camera",
  target: "#camera-card",
  targetLabel: "Camera panel",
  targetHint: "See the live image and OpenCV preview here.",
  body: "The camera panel shows the robot's live view. OpenCV blocks can take pictures, change colour spaces, make masks, and display their result here."
}, {
  emoji: "▶️",
  title: "Run your program",
  target: "#run-button",
  targetLabel: "Run controls",
  targetHint: "Start with Run and stop safely with Stop.",
  body: "Press <strong>Run</strong> when your stack is ready. Use <strong>Stop</strong> if the robot needs to halt immediately."
}, {
  emoji: "🐍",
  title: "Try Python",
  target: "#tab-python",
  targetLabel: "Python tab",
  targetHint: "See the same program as readable Python.",
  body: "The Python tab shows the same robot API as code. You can type Python, use <code>cv2</code> and <code>numpy</code>, and run it there."
}, {
  emoji: "📚",
  title: "Try a demo or the example task",
  target: ".library-footer",
  targetLabel: "Demo library",
  targetHint: "Pick a demo here, then press Load demo.",
  body: "Start with <strong>Example task - Stop at the wall</strong>, or try any starter demo. Demos you save yourself are marked <em>(mine)</em>. Saving with a name that already exists adds (1), (2)… instead of overwriting."
}, {
  emoji: "🖥️",
  title: "Read the feedback",
  target: "#terminal-tab",
  targetLabel: "Terminal",
  targetHint: "Open this to see print output and status messages.",
  body: "Use the terminal to understand what your program is doing. It shows <code>print()</code> output, errors, and current robot activity."
}, {
  emoji: "🎮",
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
    `<h3><span class="qsg-emoji" aria-hidden="true">${step.emoji}</span> ${step.title}</h3><p>${step.body}</p>`;
  const wantedMode = step.target === "#tab-python" ? "python" : "blocks";
  if (mode !== wantedMode) await switchMode(wantedMode);
  toggleTerminal(step.target === "#terminal-tab");
  $("help-prev").disabled = helpIndex === 0;
  $("help-next").textContent = helpIndex === helpSteps.length - 1 ? "Finish" : "Next →";
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

generatePython().then(loadMonaco);

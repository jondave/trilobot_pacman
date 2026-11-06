// Robot directory: the robot chooser with its last-seen ping lamps.
import { APP_CONFIG } from "./config.js";
import { jsonRequest } from "./api.js";
import { state } from "./state.js";
import { $ } from "./ui.js";

const urlInput = $("robot-url");
export const robotSelect = $("robot-select");
const manualRobotAddress = $("manual-robot-address");
const MANUAL_ROBOT_VALUE = "__manual__";
const PING_GREEN_SECONDS = APP_CONFIG.robot_ping.green_seconds;
const PING_ORANGE_SECONDS = APP_CONFIG.robot_ping.orange_seconds;
const PING_STATUS = {
  green: {
    icon: "🟢",
    label: "Seen within " + PING_GREEN_SECONDS / 60 + " minutes"
  },
  orange: {
    icon: "🟠",
    label: "Not seen for more than " + PING_GREEN_SECONDS / 60 + " minutes"
  },
  red: {
    icon: "🔴",
    label: "Not seen for more than " + PING_ORANGE_SECONDS / 60 + " minutes"
  }
};

function robotPingState(lastPing) {
  const timestamp = Date.parse(lastPing || "");
  if (!Number.isFinite(timestamp)) return "red";
  const age = Math.max(0, Date.now() - timestamp) / 1000;
  if (age <= PING_GREEN_SECONDS) return "green";
  if (age <= PING_ORANGE_SECONDS) return "orange";
  return "red";
}

function updateManualAddressVisibility(focus = false) {
  const manual = robotSelect.value === MANUAL_ROBOT_VALUE;
  manualRobotAddress.hidden = !manual;
  if (manual && focus) urlInput.focus();
}

export function updateRobotPingStatuses() {
  for (const option of robotSelect.options) {
    const robot = state.robotChoices.find((item) => item.url === option.value);
    if (!robot) continue;
    const ping = PING_STATUS[robotPingState(robot.last_ping)];
    option.textContent = ping.icon + " " + robot.name + " (" + robot.ip + ")";
    option.title = ping.label + (robot.last_ping ? ": " + robot.last_ping : "");
  }
}

function populateRobotChoices(robots) {
  const previous = robotSelect.value;
  state.robotChoices = robots.filter((robot) => robot && robot.url && robot.ip && robot.name);
  robotSelect.replaceChildren();
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = state.robotChoices.length ? "Choose a robot…" : "No robots found";
  robotSelect.appendChild(placeholder);
  for (const robot of state.robotChoices) {
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
  } else if (state.robotChoices.length) {
    robotSelect.selectedIndex = 1;
  } else {
    robotSelect.value = MANUAL_ROBOT_VALUE;
  }
  updateManualAddressVisibility();
  updateRobotPingStatuses();
}

export async function refreshRobots() {
  try {
    const data = await jsonRequest("/api/robots");
    const robots = Array.isArray(data.robots) ? data.robots : [];
    populateRobotChoices(robots);
  } catch (error) {
    populateRobotChoices([]);
  }
}

export function selectedAddress() {
  return robotSelect.value === MANUAL_ROBOT_VALUE ? urlInput.value.trim() : robotSelect.value;
}

export function initDirectory() {
  $("refresh-robots").addEventListener("click", refreshRobots);
  robotSelect.addEventListener("change", () => {
    updateManualAddressVisibility(true);
    updateRobotPingStatuses();
  });
}

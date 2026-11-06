// Robot directory: the robot chooser with its last-seen ping lamps.
import { APP_CONFIG } from "./config.js";
import { jsonRequest } from "./api.js";
import { state } from "./state.js";
import { $ } from "./ui.js";

const urlInput = $("robot-url");
export const robotSelect = $("robot-select");
const manualRobotAddress = $("manual-robot-address");
const MANUAL_ROBOT_VALUE = "__manual__";
const STORAGE_KEY = "trilobotBlocklyRobotChoice";
const DEFAULT_PORT = "8765";
const DEFAULT_MANUAL_ADDRESS = urlInput.value;
// What the student last picked ("" until they pick, a directory URL, or manual).
const preferred = {choice: "", manual: ""};

function loadPreferred() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    if (typeof saved.choice === "string") preferred.choice = saved.choice;
    if (typeof saved.manual === "string") preferred.manual = saved.manual;
  } catch (error) {
    // Storage unavailable: the defaults apply.
  }
}

function savePreferred() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferred));
  } catch (error) {
    // Storage unavailable: nothing is remembered.
  }
}

// Trim, add ws:// when there is no scheme, and :8765 when there is no port.
export function normalizeAddress(raw) {
  let text = String(raw || "").trim();
  if (!text) return "";
  if (!/^[a-z][a-z0-9+.-]*:\/\//i.test(text)) text = "ws://" + text;
  const match = /^([a-z][a-z0-9+.-]*:\/\/)([^/?#]*)(.*)$/i.exec(text);
  if (!match) return text;
  let host = match[2];
  if (host && !/:\d+$/.test(host) && !host.endsWith("]")) host += ":" + DEFAULT_PORT;
  return match[1] + host + match[3];
}

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
  const wanted = preferred.choice || previous;
  if (wanted && [...robotSelect.options].some((option) => option.value === wanted)) {
    robotSelect.value = wanted;
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
  if (robotSelect.value !== MANUAL_ROBOT_VALUE) return robotSelect.value;
  const address = normalizeAddress(urlInput.value);
  if (address) urlInput.value = address;
  preferred.manual = urlInput.value;
  savePreferred();
  return address;
}

export function initDirectory() {
  loadPreferred();
  if (preferred.manual) urlInput.value = preferred.manual;
  else urlInput.value = DEFAULT_MANUAL_ADDRESS;
  urlInput.addEventListener("input", () => {
    preferred.manual = urlInput.value;
    savePreferred();
  });
  urlInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      $("connect-button").click();
    }
  });
  $("refresh-robots").addEventListener("click", refreshRobots);
  robotSelect.addEventListener("change", () => {
    if (robotSelect.value) {
      preferred.choice = robotSelect.value;
      savePreferred();
    }
    updateManualAddressVisibility(true);
    updateRobotPingStatuses();
  });
}

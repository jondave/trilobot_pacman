// Robot directory: the robot chooser and the typed robot address.
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
    dot: "🟢",
    label: "Seen within " + PING_GREEN_SECONDS / 60 + " minutes"
  },
  orange: {
    dot: "🟠",
    label: "Not seen for more than " + PING_GREEN_SECONDS / 60 + " minutes"
  },
  red: {
    dot: "🔴",
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

// "seen 2 min ago" style wording for the option text.
function seenText(lastPing) {
  const timestamp = Date.parse(lastPing || "");
  if (!Number.isFinite(timestamp)) return "not seen yet";
  const minutes = Math.floor(Math.max(0, Date.now() - timestamp) / 60000);
  if (minutes < 1) return "seen just now";
  if (minutes < 60) return "seen " + minutes + " min ago";
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return "seen " + hours + " h ago";
  const days = Math.floor(hours / 24);
  return "seen " + days + (days === 1 ? " day ago" : " days ago");
}

function updateManualAddressVisibility(focus = false) {
  const manual = robotSelect.value === MANUAL_ROBOT_VALUE;
  manualRobotAddress.hidden = !manual;
  if (manual && focus) urlInput.focus();
}

// An <option> can't hold a Font Awesome icon, so each robot's option keeps a
// traffic-light emoji dot (the only emoji in the UI).
export function updateRobotPingStatuses() {
  for (const option of robotSelect.options) {
    const robot = state.robotChoices.find((item) => item.url === option.value);
    if (!robot) continue;
    const ping = PING_STATUS[robotPingState(robot.last_ping)];
    option.textContent = ping.dot + " " + robot.name + " (" + robot.ip + "), " + seenText(robot.last_ping);
    option.title = ping.label + (robot.last_ping ? ": " + robot.last_ping : "");
  }
}

function addOption(value, text) {
  const option = document.createElement("option");
  option.value = value;
  option.textContent = text;
  robotSelect.appendChild(option);
  return option;
}

// Rebuilds the list. "Enter address manually…" is always the last option, so
// connecting by address never depends on the directory answering.
function populateRobotChoices(robots, placeholderText = "") {
  const previous = robotSelect.value;
  state.robotChoices = robots.filter((robot) => robot && robot.url && robot.ip && robot.name);
  robotSelect.replaceChildren();
  addOption("", placeholderText || (state.robotChoices.length ? "Choose a robot…" : "No robots found"));
  for (const robot of state.robotChoices) {
    addOption(robot.url, robot.name + " (" + robot.ip + ")").title = robot.url;
  }
  addOption(MANUAL_ROBOT_VALUE, "Enter address manually…");
  // Picking an option updates preferred.choice, so a pick made while the
  // list was loading is kept too.
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

let robotRefreshes = 0;

export async function refreshRobots() {
  // Only the newest refresh may rebuild the list.
  const refresh = ++robotRefreshes;
  const refreshButton = $("refresh-robots");
  refreshButton.disabled = true;
  try {
    // Always a fresh answer: neither the app nor the browser caches the list.
    const data = await jsonRequest("/api/robots", {cache: "no-store"});
    if (refresh !== robotRefreshes) return;
    const robots = Array.isArray(data.robots) ? data.robots : [];
    populateRobotChoices(robots, !robots.length && data.error ? "Robot list unavailable" : "");
    refreshButton.title = data.error || "Refresh the robot list";
  } catch (error) {
    if (refresh !== robotRefreshes) return;
    // The list shows only the latest answer; the manual option is always there.
    populateRobotChoices([], "Robot list unavailable");
    refreshButton.title = error.message || "Robot list unavailable";
  } finally {
    if (refresh === robotRefreshes) refreshButton.disabled = false;
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
  // A remembered manual choice applies at once, without waiting for the directory.
  if (preferred.choice === MANUAL_ROBOT_VALUE) robotSelect.value = MANUAL_ROBOT_VALUE;
  updateManualAddressVisibility();
  urlInput.addEventListener("input", () => {
    preferred.manual = urlInput.value;
    savePreferred();
  });
  urlInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      // Enter connects; it never disconnects or cancels a connection.
      const button = $("connect-button");
      if (button.dataset.action === "connect") button.click();
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

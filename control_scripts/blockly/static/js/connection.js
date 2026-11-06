// Connection: connect and disconnect, remembered sessions, and the header
// lamp, banner and controls that show the connection state.
import { alertState, closeAlert, isAlertOpen, showAlert } from "./alert-modal.js";
import { jsonRequest } from "./api.js";
import { robotSelect, selectedAddress } from "./directory.js";
import { state } from "./state.js";
import { stopTeleop, teleopButtons, teleopEnabled, updateTeleopState } from "./teleop.js";
import { $, clock, setMessage } from "./ui.js";
import { renderVideo, setVideoSettings, videoSettings } from "./video.js";

// Remembered robot-given identities, kept so a refresh or dropped connection resumes
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

// A rejected Connect (such as a bad address) has no robot state to show, so
// its message is kept here and shown in the banner until the next attempt.
let connectError = "";

let connectAttempted = false;

async function connectRobot(force = false, urlOverride = "") {
  connectError = "";
  connectAttempted = true;
  const address = urlOverride || selectedAddress();
  if (!address) {
    setMessage("Choose a robot or enter a manual WebSocket address", true);
    return;
  }
  const stored = loadSessions()[address] || {};
  const choice = state.robotChoices.find((robot) => robot.url === address);
  const robotName = (choice && choice.name) || stored.robot || (state.lastConnection && state.lastConnection.robot);
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
    connectError = error.message;
    setMessage(error.message, true);
  }
}

function isLive() {
  const current = state.lastConnection && state.lastConnection.state;
  return current === "connected" || current === "weak";
}

async function disconnectRobot() {
  // Stop the motors while the robot is still connected: a stop sent after
  // /api/disconnect has nowhere to go and the server answers 409.
  teleopEnabled.checked = false;
  updateTeleopState();
  await stopTeleop(true, isLive());
  try {
    await jsonRequest("/api/disconnect", {
      method: "POST"
    });
    setMessage("Disconnected");
  } catch (error) {
    setMessage(error.message, true);
  }
}

const STATE_LABELS = {
  idle: "Disconnected",
  connecting: "Connecting…",
  connected: "Connected",
  weak: "Slow connection",
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

function takeoverTarget(conn) {
  return {robot: conn.robot, holder: conn.holder, since: conn.since, url: conn.url || ""};
}

function usedBy(robot, holder, since) {
  const time = clock(since);
  return robot.charAt(0).toUpperCase() + robot.slice(1) + " is being used by " + holder + (time ? " (since " + time + ")" : "") + ".";
}

// Every force-connect goes through here: ask first, connect only on confirm.
export function confirmTakeover({robot, holder, since, url = ""}) {
  const name = robot || "the robot";
  const current = state.lastConnection || {};
  showAlert({
    tone: "warning",
    state: current.state || null,
    fallbackFocus: $("connect-button"),
    title: "Take over " + name + "?",
    body: usedBy(name, holder || "Another user", since) +
      " Taking over will stop their program and disconnect them.",
    buttons: [
      {label: "Cancel", isDefault: true},
      {label: "Take over", variant: "stop", run: () => connectRobot(true, url)}
    ]
  });
}

// Alerts shown once per event, keyed on state + robot + holder + since so the
// polling never re-opens a dismissed one. While the help tour is open nothing
// is shown or marked as shown, so the alert appears on the first poll after it closes.
const shownAlerts = {};

function alertKey(conn) {
  return [conn.state, conn.url || "", conn.holder || "", conn.since || ""].join("|");
}

function syncAlerts(connState, conn) {
  if (isAlertOpen() && alertState() !== connState) closeAlert();
  if (connState === "connected" || connState === "weak") connectAttempted = false;
  if (connState !== "busy" && connState !== "taken_over") return;
  if (!$("help-modal").hidden || isAlertOpen()) return;
  const key = alertKey(conn);
  if (shownAlerts[connState] === key) return;
  const robot = conn.robot || "the robot";
  const holder = conn.holder || "Another user";
  const choose = {label: "Choose another robot", run: focusRobotChooser};
  if (connState === "busy") {
    if (!connectAttempted) return;
    shownAlerts.busy = key;
    connectAttempted = false;
    showAlert({
      tone: "warning",
      state: "busy",
      fallbackFocus: $("connect-button"),
      title: (conn.robot || "This robot") + " is busy",
      body: usedBy(robot, holder, conn.since) +
        " Taking over will stop their program and disconnect them.",
      buttons: [
        Object.assign({isDefault: true}, choose),
        {label: "Take over", variant: "stop", run: () => connectRobot(true, conn.url || "")}
      ]
    });
    return;
  }
  shownAlerts.taken_over = key;
  const at = clock(conn.since);
  showAlert({
    tone: "danger",
    state: "taken_over",
    fallbackFocus: $("connect-button"),
    title: holder + " took over " + robot,
    body: (at ? "at " + at + "." : "Just now.") + (conn.program_stopped ? " Your program was stopped." : ""),
    buttons: [
      {label: "OK", isDefault: true},
      choose,
      {label: "Take it back", variant: "stop", run: () => confirmTakeover(takeoverTarget(conn))}
    ]
  });
}

function bannerContent(connState, conn) {
  if (connState !== "idle") connectError = "";
  if (connectError) return {kind: "danger", icon: "⛔", text: connectError};
  const robot = conn.robot || "the robot";
  const holder = conn.holder || "Another user";
  const since = clock(conn.since);
  const at = since ? " at " + since : "";
  const retry = {label: "Retry now", run: () => connectRobot(false, conn.url || "")};
  const choose = {label: "Choose another robot", run: focusRobotChooser};
  switch (connState) {
    case "connected":
      return {kind: "info", icon: "✔", text: conn.session ?
        "You are " + conn.session + " on " + robot : conn.message || "Connected to " + robot};
    case "weak":
      return {kind: "warning", icon: "⚠", text: "Slow connection to the robot. The video and controls may lag."};
    case "reconnecting":
      return {kind: "warning", icon: "⟳", text: "Lost connection to " + robot + ". Reconnecting" +
        (conn.session ? " as " + conn.session : "") + "… (attempt " + (conn.attempt || 1) + ")",
        actions: [retry]};
    case "taken_over":
      return {kind: "danger", icon: "⛔", text: holder + " took over " + robot + at + "." +
        (conn.program_stopped ? " Your program was stopped." : ""),
        actions: [choose, {label: "Take it back", run: () => confirmTakeover(takeoverTarget(conn))}]};
    case "busy":
      return {kind: "muted", icon: "ℹ", text: (conn.robot || "The robot") + " is being used by " + holder +
        (since ? " (since " + since + ")" : "") + ".",
        actions: [choose, {label: "Take over", run: () => confirmTakeover(takeoverTarget(conn))}]};
    case "robot_offline":
      return {kind: "danger", icon: "⛔", text: "Can't reach " + robot +
        ". Check it's switched on, or ask your teacher.",
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

function renderBanner(connState, conn) {
  const content = bannerContent(connState, conn);
  if (!content) {
    banner.hidden = true;
    bannerState = null;
    return;
  }
  const danger = content.kind === "danger";
  const key = connState + "|" + connectError + "|" + (conn.url || "") + "|" + (conn.holder || "");
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

function renderControls(connState) {
  const canDrive = connState === "connected" || connState === "weak";
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
    connState === "connecting" ? "Connecting…" :
    connState === "reconnecting" ? "Reconnecting…" : "Connect";
  connectButton.disabled = canDrive || connState === "connecting" || connState === "reconnecting";
  $("disconnect-button").disabled = !["connected", "weak", "connecting", "reconnecting"].includes(connState);
}

// The header shows one indicator: the lamp dot plus a single label.
function renderLamp(connState, conn) {
  const lamp = $("quality-lamp");
  const live = connState === "connected" || connState === "weak";
  const colour = connState === "connected" ? (conn.health || "green") :
    connState === "weak" || connState === "reconnecting" || connState === "connecting" ? "orange" : "red";
  const label = STATE_LABELS[connState] || conn.message || connState;
  lamp.className = "quality-lamp " + colour;
  const text = $("quality-text");
  text.textContent = live && conn.session ? label + " · " + conn.session : label;
  text.title = lamp.title = conn.health_text && connState === "connected" ? label + " · " + conn.health_text : label;
}

export function renderConnection(conn) {
  const connState = conn.state || "idle";
  state.lastConnection = conn;
  rememberSession(conn);
  // Controls first: they matter most and must not wait on the rest.
  renderControls(connState);
  renderLamp(connState, conn);
  renderBanner(connState, conn);
  syncAlerts(connState, conn);
  renderVideo(connState, conn, previousState);
  const title = (ALERT_STATES.includes(connState) ? "⚠ " : "") + BASE_TITLE;
  if (document.title !== title) document.title = title;
  previousState = connState;
}

export function initConnection() {
  $("connect-button").addEventListener("click", connectRobot);
  $("disconnect-button").addEventListener("click", disconnectRobot);
}

// Connection: connect and disconnect, remembered sessions, and the one place
// the connection state is shown (the header chip), plus a banner only when the
// student needs to act.
import { alertState, closeAlert, isAlertOpen, showAlert } from "./alert-modal.js";
import { jsonRequest } from "./api.js";
import { robotSelect, selectedAddress } from "./directory.js";
import { state } from "./state.js";
import { stopTeleop, teleopButtons, teleopEnabled, updateTeleopState } from "./teleop.js";
import { $, clock, problemText, setButtonLabel, setMessage } from "./ui.js";
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

// Banner icons (Font Awesome 5 classes), coloured from the palette.
const ICONS = {
  error: "fas fa-times-circle icon-danger",
  weak: "fas fa-exclamation-triangle icon-warning",
  reconnecting: "fas fa-sync-alt fa-spin icon-warning",
  takenOver: "fas fa-hand-paper icon-danger",
  busy: "fas fa-info-circle icon-accent",
  offline: "fas fa-unlink icon-danger",
  appDown: "fas fa-power-off icon-danger"
};

// A rejected Connect (such as a bad address) has no robot state to show, so
// its message is kept here and shown in the banner until the next attempt.
let connectError = "";

let connectAttempted = false;

async function connectRobot(force = false, urlOverride = "") {
  connectError = "";
  connectAttempted = true;
  const address = urlOverride || selectedAddress();
  if (!address) {
    setMessage("Choose a robot or type its address", true);
    return;
  }
  // The name must belong to THIS address: the directory's name, or the one
  // remembered for it. A new address has no name, so the address is shown.
  const stored = loadSessions()[address] || {};
  const choice = state.robotChoices.find((robot) => robot.url === address);
  const robotName = (choice && choice.name) || stored.robot || "";
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
  } catch (error) {
    // Shown in the banner (it is a connection problem), not as an app message.
    connectError = error.message;
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
  } catch (error) {
    setMessage(error.message, true);
  }
}

const STATE_LABELS = {
  idle: "Not connected",
  connecting: "Connecting…",
  connected: "Connected",
  weak: "Slow connection",
  reconnecting: "Reconnecting…",
  taken_over: "Taken over",
  busy: "Robot busy",
  robot_offline: "Can't reach robot",
  app_down: "App not running"
};
// While these, the toggle stops the link (and any retries) instead of connecting.
const CANCEL_STATES = ["connecting", "reconnecting"];
const LIVE_STATES = ["connected", "weak"];
const ALERT_STATES = ["reconnecting", "taken_over", "busy", "robot_offline", "app_down"];
const BASE_TITLE = document.title;
const banner = $("conn-banner");
const bannerIcon = banner.querySelector(".conn-icon");
const bannerMessage = banner.querySelector(".conn-message");
const bannerActions = banner.querySelector(".conn-actions");
let bannerState = null;

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
    body: conn.program_stopped ?
      (at ? "Your program was stopped at " + at + "." : "Your program was stopped.") :
      (at ? "This happened at " + at + "." : "This just happened."),
    buttons: [
      Object.assign({isDefault: true}, choose),
      {label: "Take it back", variant: "stop", run: () => confirmTakeover(takeoverTarget(conn))}
    ]
  });
}

// A banner only when the student needs to act; the chip already says the state.
function bannerContent(connState, conn) {
  if (connectError) return {kind: "danger", icon: ICONS.error, text: problemText(connectError)};
  const robot = conn.robot || robotAddressName(conn.url) || "the robot";
  const holder = conn.holder || "Another user";
  const since = clock(conn.since);
  const at = since ? " at " + since : "";
  const retry = {label: "Try again now", run: () => connectRobot(false, conn.url || "")};
  const choose = {label: "Choose another robot", run: focusRobotChooser};
  switch (connState) {
    case "weak":
      return {kind: "warning", icon: ICONS.weak, text: "Slow connection to the robot. The video and controls may lag."};
    case "reconnecting":
      return {kind: "warning", icon: ICONS.reconnecting, text: "Lost connection to " + robot + ". Trying again" +
        (conn.session ? " as " + conn.session : "") + "…",
        actions: [retry]};
    case "taken_over":
      return {kind: "danger", icon: ICONS.takenOver, text: holder + " took over " + robot + at + "." +
        (conn.program_stopped ? " Your program was stopped." : ""),
        actions: [choose, {label: "Take it back", run: () => confirmTakeover(takeoverTarget(conn))}]};
    case "busy":
      return {kind: "muted", icon: ICONS.busy, text: (conn.robot || "The robot") + " is being used by " + holder +
        (since ? " (since " + since + ")" : "") + ".",
        actions: [choose, {label: "Take over", run: () => confirmTakeover(takeoverTarget(conn))}]};
    case "robot_offline":
      return {kind: "danger", icon: ICONS.offline, text: "Can't reach " + robot +
        ". Check it's switched on, or ask your teacher. Still trying…",
        actions: [retry, {label: "Stop trying", run: disconnectRobot}]};
    case "app_down":
      return {kind: "danger", icon: ICONS.appDown, text: "The Trilobot app on your computer isn't running. " +
        "Restart it (see the Get Started guide)."};
    default:
      return null;
  }
}

// "ws://10.0.0.5:8765" -> "10.0.0.5", for a robot with no name yet.
function robotAddressName(url) {
  const match = /^[a-z]+:\/\/([^/:?#]+)/i.exec(String(url || ""));
  return match ? match[1] : "";
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
  const iconClass = "conn-icon " + content.icon;
  if (bannerIcon.className !== iconClass) bannerIcon.className = iconClass;
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
  const canDrive = LIVE_STATES.includes(connState);
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
  // One toggle: Connect / Cancel (while trying) / Disconnect (while connected).
  // robot_offline keeps retrying on the server; its banner has "Stop trying".
  const action = canDrive ? "disconnect" : CANCEL_STATES.includes(connState) ? "cancel" : "connect";
  const button = $("connect-button");
  if (button.dataset.action === action) return;
  button.dataset.action = action;
  setButtonLabel(button, {connect: "Connect", cancel: "Cancel", disconnect: "Disconnect"}[action]);
  button.querySelector("i").className = "fas " +
    {connect: "fa-plug", cancel: "fa-times icon-muted", disconnect: "fa-unlink icon-orange"}[action];
  button.classList.toggle("primary", action === "connect");
  button.disabled = false;
}

// The chip: the lamp plus one word or phrase. Who you are, and on which
// robot, is in its tooltip (and on a second line when the header has room).
function renderLamp(connState, conn) {
  const lamp = $("quality-lamp");
  const live = LIVE_STATES.includes(connState);
  const colour = connState === "connected" ? (conn.health || "green") :
    connState === "weak" || connState === "reconnecting" || connState === "connecting" ? "orange" :
    connState === "idle" ? "idle" : "red";
  const label = STATE_LABELS[connState] || connState;
  const lampClass = "quality-lamp " + colour;
  if (lamp.className !== lampClass) lamp.className = lampClass;
  const text = $("quality-text");
  if (text.textContent !== label) text.textContent = label;
  const robot = conn.robot || robotAddressName(conn.url);
  const who = conn.session ? "You are " + conn.session + (robot ? " on " + robot : "") :
    robot && connState !== "idle" ? label + ": " + robot : label;
  const chip = $("connection-chip");
  if (chip.title !== who) chip.title = who;
  const session = $("chip-session");
  const sessionText = live && conn.session ? "You are " + conn.session : "";
  session.hidden = !sessionText;
  if (session.textContent !== sessionText) session.textContent = sessionText;
}

function toggleConnection() {
  if ($("connect-button").dataset.action === "connect") connectRobot();
  else disconnectRobot();
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
  renderVideo(connState, conn);
  // A tab title can't show an icon, so alert states lead with their label.
  const title = (ALERT_STATES.includes(connState) ? (STATE_LABELS[connState] || "Disconnected") + " · " : "") + BASE_TITLE;
  if (document.title !== title) document.title = title;
}

export function initConnection() {
  $("connect-button").addEventListener("click", toggleConnection);
}

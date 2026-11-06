// Teleop: hold a direction button or key to drive; release to stop.
import { $, setMessage } from "./ui.js";

export const teleopEnabled = $("teleop-enabled");
const pressedKeys = new Set();
export const teleopButtons = new Map(
  [...document.querySelectorAll(".teleop-grid button")].map(
    (button) => [button.dataset.key, button]
  )
);
let teleopTimer = null;
let activeTeleopButton = null;

// Returns the request promise so callers can wait for a stop to be sent.
function postTeleop(payload) {
  return fetch("/api/teleop", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  }).catch((error) => setMessage("Teleop: " + error.message, true));
}

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

// send=false only resets the buttons, for when there is no robot to tell.
export function stopTeleop(force = false, send = true) {
  if (!force && !teleopEnabled.checked) return Promise.resolve();
  clearInterval(teleopTimer);
  teleopTimer = null;
  activeTeleopButton = null;
  document.querySelectorAll(".teleop-grid button.active")
    .forEach((button) => button.classList.remove("active"));
  if (!send) return Promise.resolve();
  return postTeleop({
    stop: true
  });
}

export function updateTeleopState() {
  const enabled = teleopEnabled.checked;
  const card = $("teleop-card");
  card.classList.toggle("teleop-enabled", enabled);
  // The words change too, so the state never depends on colour alone.
  $("teleop-switch-state").textContent = enabled ? "On" : "Off";
}

function keyForEvent(event) {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName)) return null;
  const key = event.key.toLowerCase();
  return teleopButtons.has(key) ? key : null;
}

export function initTeleop() {
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
    const key = event.key.toLowerCase();
    if (!pressedKeys.has(key)) return;
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
}

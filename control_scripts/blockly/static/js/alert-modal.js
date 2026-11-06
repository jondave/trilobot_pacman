// One reusable big alert dialog (#alert-modal): heading, body and action
// buttons, with a focus trap, a safe default button, Escape to dismiss and
// focus restored to whatever opened it.
import { $ } from "./ui.js";

const modal = $("alert-modal");
const panel = modal.querySelector(".alert-modal");
const titleEl = $("alert-title");
const bodyEl = $("alert-body");
const actionsEl = $("alert-actions");
let current = null;
let opener = null;

export function isAlertOpen() {
  return current !== null;
}

// The state the open alert belongs to, or null when none is open.
export function alertState() {
  return current ? current.state : null;
}

export function closeAlert(restoreFocus = true) {
  if (!current) return;
  current = null;
  modal.hidden = true;
  actionsEl.replaceChildren();
  const target = opener;
  opener = null;
  if (restoreFocus && target && target.isConnected && typeof target.focus === "function") target.focus();
}

// options: {tone: "danger"|"warning", state, fallbackFocus, title, body, buttons: [{label, variant, isDefault, run}]}.
// Showing an alert replaces any open one.
export function showAlert(options) {
  if (current) {
    const keep = opener;
    closeAlert(false);
    opener = keep;
  } else {
    opener = document.activeElement;
    // A button that was disabled while connecting drops focus to <body>.
    if (!opener || opener === document.body) opener = options.fallbackFocus || null;
  }
  current = {state: options.state || null};
  panel.className = "alert-modal is-" + (options.tone || "warning");
  titleEl.textContent = options.title;
  bodyEl.textContent = options.body;
  actionsEl.replaceChildren();
  let defaultButton = null;
  for (const spec of options.buttons) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = spec.label;
    if (spec.variant) button.className = spec.variant;
    button.addEventListener("click", () => {
      closeAlert();
      if (spec.run) spec.run();
    });
    actionsEl.appendChild(button);
    if (spec.isDefault) defaultButton = button;
  }
  modal.hidden = false;
  (defaultButton || actionsEl.firstElementChild).focus();
}

function focusable() {
  return Array.from(actionsEl.querySelectorAll("button:not(:disabled)"));
}

export function initAlertModal() {
  document.addEventListener("keydown", (event) => {
    if (!current) return;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      closeAlert();
    } else if (event.key === "Tab") {
      const items = focusable();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (!modal.contains(active)) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }
  }, true);
}

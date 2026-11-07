// Small DOM helpers shared by every module.
export const $ = (id) => document.getElementById(id);

// Sets the text of a button that also holds an icon (its .btn-label span).
export function setButtonLabel(button, text) {
  const label = button.querySelector(".btn-label");
  if (label.textContent !== text) label.textContent = text;
}

// "Line 3: NameError: x" (from the server) -> "Problem on line 3: NameError: x".
export function problemText(message) {
  const text = String(message || "").trim();
  const match = /^line (\d+):\s*(.*)$/is.exec(text);
  if (match) return "Problem on line " + match[1] + ": " + match[2];
  return text;
}

// App messages ("Saved demo", "Could not load file…") have their own area,
// separate from the program status beside Run/Stop. Notes fade after a few
// seconds; errors stay until the student's next click or key press.
const MESSAGE_SECONDS = 4;
let messageTimer = null;
let messageIsError = false;

function hideMessage() {
  clearTimeout(messageTimer);
  messageTimer = null;
  messageIsError = false;
  const element = $("app-message");
  element.hidden = true;
  element.textContent = "";
}

export function setMessage(message, error = false) {
  const element = $("app-message");
  clearTimeout(messageTimer);
  element.textContent = error ? problemText(message) : message;
  element.title = element.textContent;
  element.classList.toggle("error-text", error);
  element.hidden = false;
  messageIsError = error;
  if (!error) messageTimer = setTimeout(hideMessage, MESSAGE_SECONDS * 1000);
}

// The next action clears an error. Capture runs before the click handlers,
// so an error raised by this same click is shown after the clear.
for (const type of ["pointerdown", "keydown"]) {
  document.addEventListener(type, () => {
    if (messageIsError) hideMessage();
  }, true);
}

export function clock(epochSeconds, withSeconds = false) {
  if (!Number.isFinite(Number(epochSeconds)) || epochSeconds === null) return "";
  const date = new Date(Number(epochSeconds) * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return pad(date.getHours()) + ":" + pad(date.getMinutes()) +
    (withSeconds ? ":" + pad(date.getSeconds()) : "");
}

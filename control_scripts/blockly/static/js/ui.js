// Small DOM helpers shared by every module.
export const $ = (id) => document.getElementById(id);

// Sets the text of a button that also holds an icon (its .btn-label span).
export function setButtonLabel(button, text) {
  const label = button.querySelector(".btn-label");
  if (label.textContent !== text) label.textContent = text;
}

export function setMessage(message, error = false) {
  const element = $("program-status");
  element.textContent = message;
  element.classList.toggle("error-text", error);
}

export function clock(epochSeconds, withSeconds = false) {
  if (!Number.isFinite(Number(epochSeconds)) || epochSeconds === null) return "";
  const date = new Date(Number(epochSeconds) * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return pad(date.getHours()) + ":" + pad(date.getMinutes()) +
    (withSeconds ? ":" + pad(date.getSeconds()) : "");
}

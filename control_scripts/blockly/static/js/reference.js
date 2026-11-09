// The Python programming reference (docs/PYTHON_REFERENCE.md) in a scrolling
// panel opened from the Python tab. The markdown is fetched once, rendered
// with marked and sanitised with DOMPurify (classic scripts in index.html), so
// the rendered HTML can never run script.
import { $ } from "./ui.js";

const modal = $("reference-modal");
const body = $("reference-body");
const closeButton = $("reference-close");
// Heading ids get a prefix so they can't clash with the page's own ids.
const ID_PREFIX = "reference-";
let loading = null;
let opener = null;

// GitHub's heading anchors, so the doc's own "#moving" links work here too.
function slug(text) {
  return text.trim().toLowerCase().replace(/[^\p{L}\p{N}\s_-]/gu, "").replace(/\s/g, "-");
}

function render(markdown) {
  if (!window.marked || !window.DOMPurify) {
    // Libraries unavailable (offline, not vendored): plain text is still readable.
    const pre = document.createElement("pre");
    pre.textContent = markdown;
    body.replaceChildren(pre);
    return;
  }
  const html = window.marked.parse(markdown, {gfm: true});
  body.replaceChildren(window.DOMPurify.sanitize(html, {RETURN_DOM_FRAGMENT: true}));
  // The panel header already shows the title.
  const title = body.querySelector("h1");
  if (title) title.remove();
  const seen = new Map();
  for (const heading of body.querySelectorAll("h2, h3, h4, h5, h6")) {
    const base = slug(heading.textContent);
    const count = seen.get(base) || 0;
    seen.set(base, count + 1);
    heading.id = ID_PREFIX + (count ? base + "-" + count : base);
    heading.tabIndex = -1;
  }
  for (const link of body.querySelectorAll("a[href]")) {
    const href = link.getAttribute("href");
    if (href.startsWith("#")) continue;
    if (/^https?:\/\//i.test(href)) {
      link.target = "_blank";
      link.rel = "noopener noreferrer";
    } else {
      // Links to other docs files: the app doesn't serve them, keep the text.
      link.replaceWith(...link.childNodes);
    }
  }
}

function load() {
  if (!loading) {
    body.textContent = "Loading the Python reference…";
    loading = fetch("/api/docs/python-reference")
      .then((response) => {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.text();
      })
      .then(render)
      .catch(() => {
        loading = null;
        body.textContent = "Could not load the Python reference. Close this and try again.";
      });
  }
  return loading;
}

// Scrolls the panel (not the page) to an in-page "#anchor" link's heading.
function followAnchor(event) {
  const link = event.target.closest("a[href^='#']");
  if (!link) return;
  event.preventDefault();
  const target = document.getElementById(ID_PREFIX + decodeURIComponent(link.hash.slice(1)));
  if (!target || !body.contains(target)) return;
  body.scrollTop += target.getBoundingClientRect().top - body.getBoundingClientRect().top;
  target.focus({preventScroll: true});
}

export function openReference() {
  opener = document.activeElement;
  modal.hidden = false;
  closeButton.focus();
  load();
}

export function closeReference() {
  if (modal.hidden) return;
  modal.hidden = true;
  if (opener && opener.isConnected && typeof opener.focus === "function") opener.focus();
  opener = null;
}

export function initReference() {
  $("python-reference-button").addEventListener("click", openReference);
  closeButton.addEventListener("click", closeReference);
  body.addEventListener("click", followAnchor);
  modal.addEventListener("click", (event) => {
    if (event.target === modal) closeReference();
  });
  // Capture, so Escape closes the panel before Monaco sees it.
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || modal.hidden) return;
    event.preventDefault();
    event.stopPropagation();
    closeReference();
  }, true);
}

// Camera feed and video settings.
import { jsonRequest } from "./api.js";
import { $, setMessage } from "./ui.js";

export function videoSettings() {
  const selected = $("video-size").selectedOptions[0];
  return {
    width: Number(selected.dataset.width),
    height: Number(selected.dataset.height),
    fps: Number($("video-fps").value),
    jpeg_quality: Number($("video-quality").value)
  };
}

export function setVideoSettings(video) {
  if (!video) return;
  const size = video.width + "x" + video.height;
  const sizeOption = [...$("video-size").options].find((option) => option.value === size);
  if (sizeOption) $("video-size").value = size;
  $("video-fps").value = String(video.fps);
  $("video-quality").value = String(video.jpeg_quality);
}

const cameraImage = document.querySelector("#camera-card .stage img");
const STREAM_URL = "/api/video.mjpg";
const SNAPSHOT_URL = "/api/video.jpg";

// The live MJPEG stream holds one of the browser's few connections to this
// server for as long as it runs, so it only runs while the robot is connected
// and this tab is visible. Otherwise the picture is either the last frame as a
// single JPEG (greyed out by the stale overlay) or nothing at all.
// cameraMode is what the <img> currently shows: "stream", "snapshot" or "none".
let cameraMode = "none";
let cameraLive = false;
let cameraHasPicture = false;
let streamRetryCount = 0;
let streamRetryTimer = null;

function wantedCameraMode() {
  if (document.visibilityState !== "visible") return "none";
  if (cameraLive) return "stream";
  return cameraHasPicture ? "snapshot" : "none";
}

// Changes the <img> only on a transition, so polling never restarts the stream.
function syncCameraFeed() {
  if (!cameraImage) return;
  const mode = wantedCameraMode();
  if (mode !== "stream") {
    clearTimeout(streamRetryTimer);
    streamRetryTimer = null;
    streamRetryCount = 0;
  }
  if (mode === cameraMode) return;
  cameraMode = mode;
  if (mode === "none") cameraImage.removeAttribute("src");
  else cameraImage.src = (mode === "stream" ? STREAM_URL : SNAPSHOT_URL) + "?t=" + Date.now();
}

function retryCameraStream() {
  cameraImage.removeAttribute("src");
  const delay = Math.min(500 * 2 ** streamRetryCount, 10000);
  streamRetryCount = Math.min(streamRetryCount + 1, 10);
  clearTimeout(streamRetryTimer);
  streamRetryTimer = setTimeout(() => {
    streamRetryTimer = null;
    cameraMode = "none";
    syncCameraFeed();
  }, delay);
}

async function applyVideoSettings() {
  try {
    const data = await jsonRequest("/api/video/config", {
      method: "POST",
      body: JSON.stringify(videoSettings())
    });
    setVideoSettings(data.video);
    setMessage("Camera settings applied");
  } catch (error) {
    setMessage(error.message, true);
  }
}

export function renderVideo(connState, conn) {
  const live = connState === "connected" || connState === "weak";
  const age = conn.last_frame_age;
  const frozen = live && typeof age === "number" && age > 2;
  const stale = !live || frozen;
  const overlay = $("video-overlay");
  // Three plain phrases: no link, a link on its way, or an old picture.
  const hasPicture = typeof age === "number";
  let text = "";
  if (frozen || (!live && hasPicture && (connState === "reconnecting" || connState === "connecting"))) {
    text = "Picture paused";
  } else if (!live) {
    text = connState === "connecting" || connState === "reconnecting" ? "Connecting…" : "Not connected";
  }
  overlay.hidden = !stale;
  if (overlay.textContent !== text) overlay.textContent = text;
  const stage = document.querySelector("#camera-card .stage");
  stage.classList.toggle("is-stale", stale);
  // No real picture yet: hide the placeholder so its text doesn't clash with the overlay.
  stage.classList.toggle("no-picture", stale && !hasPicture);
  cameraLive = live;
  cameraHasPicture = hasPicture;
  syncCameraFeed();
}

// The numbers and camera settings sit behind "Details", closed by default;
// the student's choice is remembered.
const DETAILS_KEY = "trilobotCameraDetailsOpen";

function initDetails() {
  const details = $("camera-details");
  try {
    details.open = localStorage.getItem(DETAILS_KEY) === "1";
  } catch (_) {}
  details.addEventListener("toggle", () => {
    try {
      localStorage.setItem(DETAILS_KEY, details.open ? "1" : "0");
    } catch (_) {}
  });
}

// Distance for students, the rest inside Details; all "—" when not connected
// so old numbers never look live.
export function renderStats(connState, connection, telemetry) {
  const live = connState === "connected" || connState === "weak";
  const set = (id, text) => {
    const element = $(id);
    if (element.textContent !== text) element.textContent = text;
  };
  const distance = live && telemetry && typeof telemetry.distance_cm === "number" &&
    Number.isFinite(telemetry.distance_cm) ? Math.round(telemetry.distance_cm) + " cm" : "—";
  set("telemetry", distance);
  set("video-rate", (live ? connection.video_hz || 0 : "—") + " fps");
  set("telemetry-rate", (live ? connection.telemetry_hz || 0 : "—") + " msgs/s");
  set("command-latency", "cmd " + (live && connection.last_command_ms != null ? connection.last_command_ms + " ms" : "—"));
}

export function initVideo() {
  initDetails();
  $("apply-video").addEventListener("click", applyVideoSettings);
  document.addEventListener("visibilitychange", syncCameraFeed);
  if (cameraImage) {
    cameraImage.addEventListener("error", () => {
      // A snapshot that failed to load: show nothing rather than a broken image.
      if (cameraMode === "snapshot") cameraImage.removeAttribute("src");
      else if (cameraMode === "stream") retryCameraStream();
    });
  }
}

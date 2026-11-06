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

function wantedCameraMode() {
  if (document.visibilityState !== "visible") return "none";
  if (cameraLive) return "stream";
  return cameraHasPicture ? "snapshot" : "none";
}

// Changes the <img> only on a transition, so polling never restarts the stream.
function syncCameraFeed() {
  if (!cameraImage) return;
  const mode = wantedCameraMode();
  if (mode === cameraMode) return;
  cameraMode = mode;
  if (mode === "none") cameraImage.removeAttribute("src");
  else cameraImage.src = (mode === "stream" ? STREAM_URL : SNAPSHOT_URL) + "?t=" + Date.now();
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
  let text = "";
  if (frozen) {
    text = "No new picture for " + Math.round(age) + "s";
  } else if (!live) {
    if (connState === "reconnecting" || connState === "connecting") text = "Reconnecting…";
    else if (connState === "idle" || connState === "app_down") text = "Not connected";
    else text = "Disconnected";
    if (typeof age === "number" && text !== "Not connected") {
      text += " · last picture " + (age < 2 ? "just now" : Math.round(age) + "s ago");
    }
  }
  overlay.hidden = !stale;
  overlay.textContent = text;
  const stage = document.querySelector("#camera-card .stage");
  stage.classList.toggle("is-stale", stale);
  // No real picture yet: hide the placeholder so its text doesn't clash with the overlay.
  stage.classList.toggle("no-picture", stale && typeof age !== "number");
  cameraLive = live;
  cameraHasPicture = typeof age === "number";
  syncCameraFeed();
}

export function initVideo() {
  $("apply-video").addEventListener("click", applyVideoSettings);
  document.addEventListener("visibilitychange", syncCameraFeed);
  if (cameraImage) {
    cameraImage.addEventListener("error", () => {
      // A snapshot that failed to load: show nothing rather than a broken image.
      if (cameraMode === "snapshot") cameraImage.removeAttribute("src");
    });
  }
}

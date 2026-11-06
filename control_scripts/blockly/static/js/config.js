// Shared settings and block definitions are rendered into the page by the
// "/" route (see robot_config.py and static/blocks.json), so they are ready
// synchronously before Blockly.inject runs.
function readPageJson(id) {
  const element = document.getElementById(id);
  if (!element) throw new Error("Missing page data #" + id);
  return JSON.parse(element.textContent);
}

export const APP_CONFIG = readPageJson("app-config");
export const BLOCK_DEFINITIONS = readPageJson("block-definitions");
export const LED_COLOUR_NAMES = APP_CONFIG.led_colours.map(([name]) => name);

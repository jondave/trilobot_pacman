// Block definitions, the lab theme, and the Blockly workspace with its drawer.
import { APP_CONFIG, BLOCK_DEFINITIONS } from "./config.js";
import { state } from "./state.js";

function withColourOptions(definition) {
  const fill = (args) => args.map((arg) => arg.options === APP_CONFIG.led_colour_placeholder ?
    {...arg, options: APP_CONFIG.led_colours.map(([name, value]) => [name, value])} : arg);
  const result = {...definition};
  for (const key of Object.keys(result)) {
    if (/^args\d+$/.test(key)) result[key] = fill(result[key]);
  }
  return result;
}

const hex = {
  orange: "#e49a32", green: "#2fb477", blue: "#3478f6", purple: "#9b62d7",
  pink: "#d957a7", red: "#e75a5a", teal: "#36a890", slate: "#5c81a6", yellow: "#d9b21f", grey: "#8f9bb0"
};
const blockStyle = colour => ({ colourPrimary: colour });

function defineTheme() {
  return Blockly.Theme.defineTheme("trilobot_lab", {
    name: "trilobot_lab",
    base: Blockly.Themes.Classic,
    blockStyles: {
      robot_blocks: blockStyle(hex.orange),
      loop_blocks: blockStyle(hex.green),
      stop_blocks: blockStyle(hex.red),
      debug_blocks: blockStyle(hex.blue),
      opencv_blocks: blockStyle(hex.purple),
      sensor_blocks: blockStyle(hex.teal),
      light_blocks: blockStyle(hex.pink),
      colour_red_blocks: blockStyle(hex.red),
      colour_green_blocks: blockStyle(hex.green),
      colour_blue_blocks: blockStyle(hex.blue),
      colour_yellow_blocks: blockStyle(hex.yellow),
      colour_white_blocks: blockStyle(hex.grey),
      colour_purple_blocks: blockStyle(hex.purple),
      logic_blocks: blockStyle(hex.slate),
      math_blocks: blockStyle(hex.green),
      variable_blocks: blockStyle(hex.orange)
    },
    categoryStyles: {
      robot_category: { colour: hex.orange },
      loop_category: { colour: hex.green },
      logic_category: { colour: hex.slate },
      opencv_category: { colour: hex.purple },
      sensor_category: { colour: hex.teal },
      debug_category: { colour: hex.blue },
      light_category: { colour: hex.pink },
      math_category: { colour: hex.green },
      variable_category: { colour: hex.orange }
    }
  });
}

const blockDrawerCloseButton = document.getElementById("close-block-drawer");

function getBlockDrawerBounds(flyout) {
  const editorArea = document.querySelector(".editor-area");
  if (!editorArea) return null;

  const editorBounds = editorArea.getBoundingClientRect();
  const flyoutElement = document.querySelector("#blockly-workspace .blocklyFlyout");
  const renderedBounds = flyoutElement?.getBoundingClientRect();
  if (renderedBounds?.width > 0 && renderedBounds?.height > 0) {
    return {
      left: renderedBounds.left,
      right: renderedBounds.right,
      top: renderedBounds.top,
      bottom: renderedBounds.bottom,
      editorBounds
    };
  }

  // Keep the controls usable if Blockly changes the flyout SVG class name.
  const toolboxBounds = document.querySelector(".blocklyToolboxDiv")?.getBoundingClientRect();
  const width = flyout.getWidth() || 260;
  const left = toolboxBounds?.right ?? editorBounds.left;
  return {
    left,
    right: left + width,
    top: editorBounds.top,
    bottom: editorBounds.bottom,
    editorBounds
  };
}

function syncBlockDrawerCloseButton() {
  const flyout = state.workspace.getToolbox()?.getFlyout();
  const bounds = flyout && getBlockDrawerBounds(flyout);
  if (!flyout?.isVisible() || !bounds) {
    blockDrawerCloseButton.hidden = true;
    return;
  }

  blockDrawerCloseButton.hidden = false;
  const drawerRight = bounds.right - bounds.editorBounds.left;
  const drawerLeft = bounds.left - bounds.editorBounds.left;
  const buttonWidth = blockDrawerCloseButton.offsetWidth;
  const editorWidth = bounds.editorBounds.width;
  const useLeftEdge = drawerRight + buttonWidth > editorWidth;
  const buttonLeft = useLeftEdge
    ? Math.max(0, drawerLeft - buttonWidth + 1)
    : drawerRight - 1;
  blockDrawerCloseButton.classList.toggle("left-edge", useLeftEdge);
  blockDrawerCloseButton.style.left = `${buttonLeft}px`;
  blockDrawerCloseButton.style.top = `${bounds.top - bounds.editorBounds.top + 8}px`;
}

function reflowToolbox() {
  const toolbox = state.workspace.getToolbox();
  const flyout = toolbox && toolbox.getFlyout();
  if (!flyout || !flyout.isVisible()) return;
  flyout.reflow();
  // Blockly 11 can leave flyout blocks at (0, 0) when the page uses a
  // flexible, resized workspace. Put each top-level flyout block in a real
  // vertical list while preserving Blockly's own model coordinates.
  setTimeout(() => {
    const flyoutWorkspace = flyout.getWorkspace && flyout.getWorkspace();
    if (!flyoutWorkspace) return;
    let y = 8;
    for (const block of flyoutWorkspace.getTopBlocks(false)) {
      const xy = block.getRelativeToSurfaceXY();
      const size = block.getHeightWidth();
      block.moveBy(8 - xy.x, y - xy.y);
      y += Math.max(35, size.height) + 8;
    }
  }, 0);
}

export function workspaceData() {
  return Blockly.serialization.workspaces.save(state.workspace);
}

export function replaceWorkspace(program) {
  state.checkTicket++;
  state.syncingWorkspace = true;
  try {
    state.workspace.clear();
    Blockly.serialization.workspaces.load(program, state.workspace);
  } finally {
    state.syncingWorkspace = false;
  }
}

export function initBlocks() {
  Blockly.defineBlocksWithJsonArray(BLOCK_DEFINITIONS.map(withColourOptions));

  const workspace = Blockly.inject("blockly-workspace", {
    ...(window.BLOCKLY_FROM_CDN ? {} : {media: "/static/vendor/blockly/media/"}),
    toolbox: document.getElementById("toolbox"),
    theme: defineTheme(),
    trashcan: true,
    move: {
      scrollbars: true,
      drag: true,
      wheel: true
    },
    zoom: {
      controls: true,
      wheel: true,
      startScale: 0.85,
      maxScale: 1.25,
      minScale: 0.55
    }
  });
  state.workspace = workspace;

  // The flyout owns this setting; setting it in Blockly.inject is ignored by
  // Blockly 11's category toolbox.
  workspace.getToolbox()?.getFlyout()?.setAutoClose(false);

  blockDrawerCloseButton.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    const toolbox = workspace.getToolbox();
    toolbox?.setSelectedItem(null);
    toolbox?.getFlyout()?.hide();
    blockDrawerCloseButton.hidden = true;
  });

  workspace.addChangeListener((event) => {
    if (event.type === Blockly.Events.TOOLBOX_ITEM_SELECT) {
      setTimeout(syncBlockDrawerCloseButton, 0);
    }
  });

  workspace.registerButtonCallback("CREATE_VARIABLE", (button) => {
    Blockly.Variables.createVariableButtonHandler(button.getTargetWorkspace());
  });
  window.addEventListener("resize", () => {
    Blockly.svgResize(workspace);
    requestAnimationFrame(syncBlockDrawerCloseButton);
  });
  setTimeout(() => Blockly.svgResize(workspace), 0);

  document.querySelector(".blocklyToolboxDiv")?.addEventListener("click", () => {
    setTimeout(() => {
      reflowToolbox();
      syncBlockDrawerCloseButton();
    }, 0);
  });
}

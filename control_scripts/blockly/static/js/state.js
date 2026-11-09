// Mutable state shared between modules. Modules read and write these fields
// instead of reassigning each other's variables.
export const state = {
  workspace: null,       // Blockly workspace, set by initBlocks()
  editor: null,          // Monaco editor, set once Monaco loads
  mode: "blocks",        // "blocks" or "python"
  lastConnection: null,  // last connection object from /api/status
  programRunning: false,
  robotChoices: [],      // robots from /api/robots

  // Blocks <-> Python sync bookkeeping.
  lastBlockPython: "",   // the Python the current blocks generate
  lastWorkingPython: "", // the editor text those blocks came from (as typed)
  generateTimer: null,
  generateTicket: 0,
  checkTicket: 0,
  syncingWorkspace: false,
  syncingEditor: false
};

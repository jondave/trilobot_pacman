import sys
from pathlib import Path

BLOCKLY = Path(__file__).resolve().parents[1] / "control_scripts" / "blockly"
sys.path.insert(0, str(BLOCKLY))
sys.path.insert(0, str(BLOCKLY.parent))

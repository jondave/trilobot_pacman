"""The student's session name (e.g. Grapes-Escape), owned by this app.

The app picks one name and sends it to every robot it connects to (the
``name`` query parameter), so a student who moves between or takes over
robots shows up under the same name everywhere. The name is saved to a file
so it survives app restarts. Students are never asked for their real name.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
from pathlib import Path

LOG = logging.getLogger("trilobot_blockly")
WORDS_FILE = Path(__file__).resolve().with_name("session_words.json")
# Must match NAME_PATTERN in robot_scripts/robot_sender.py.
NAME_PATTERN = re.compile(r"[A-Za-z]{1,12}(?:-[A-Za-z]{1,12}){1,2}")


def load_words(path=WORDS_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def new_name(words=None, rng=random):
    words = words or load_words()
    return "-".join(word.capitalize() for word in rng.sample(words, 2))


def is_valid(name):
    return bool(NAME_PATTERN.fullmatch(str(name or "")))


def load_or_create(path, override=None):
    """Return the saved name at path, creating and saving one if needed.

    override (TRILOBOT_SESSION_NAME) wins when it is a valid name. A file that
    can't be written only costs persistence: the name still works until restart.
    """
    if override:
        if is_valid(override):
            return override
        LOG.warning("Ignoring invalid TRILOBOT_SESSION_NAME %r", override)
    path = Path(path)
    try:
        saved = path.read_text(encoding="utf-8").strip()
        if is_valid(saved):
            return saved
    except OSError:
        pass
    name = new_name()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(name + "\n", encoding="utf-8")
    except OSError as error:
        LOG.warning("Could not save the session name to %s: %s", path, error)
    return name


def default_path(user_demos_dir):
    """TRILOBOT_SESSION_NAME_FILE, else a dotfile in the saved-demos folder.

    The saved-demos folder is the app's one persistent, writable volume in
    Docker (/data/demos), and the library only lists *.json and *.py there.
    """
    configured = os.environ.get("TRILOBOT_SESSION_NAME_FILE")
    return Path(configured) if configured else Path(user_demos_dir) / ".session-name"

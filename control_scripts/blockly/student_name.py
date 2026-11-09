"""The student's session name (e.g. Otter-Lemon), owned by this app.

The app picks one name when it starts and sends it to every robot it connects
to (the ``name`` query parameter), so a student who moves between or takes
over robots shows up under the same name everywhere. Each app process gets its
own name; it is deliberately not saved to disk, because several apps (or
Docker containers sharing a volume) on one PC would then all share one name.
Students are never asked for their real name.
"""

from __future__ import annotations

import json
import logging
import random
import re
from pathlib import Path

LOG = logging.getLogger("trilobot_blockly")
WORDS_FILE = Path(__file__).resolve().with_name("session_words.json")
# Must match NAME_PATTERN in robot_scripts/robot_sender.py.
NAME_PATTERN = re.compile(r"[A-Za-z0-9]{1,64}(?:-[A-Za-z0-9]{1,64}){1,2}")


def load_words(path=WORDS_FILE):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def new_name(words=None, rng=random):
    words = words or load_words()
    return "-".join(word.capitalize() for word in rng.sample(words, 2))


def is_valid(name):
    return bool(NAME_PATTERN.fullmatch(str(name or "")))


def pick_name(override=None):
    """override (TRILOBOT_SESSION_NAME) if it is valid, else a fresh name."""
    if override:
        if is_valid(override):
            return override
        LOG.warning("Ignoring invalid TRILOBOT_SESSION_NAME %r", override)
    return new_name()

"""The app-owned session name: created once, saved, reused."""

import random

import student_name


def test_name_is_saved_and_reused(tmp_path):
    path = tmp_path / "demos" / ".session-name"
    name = student_name.load_or_create(path)
    assert student_name.is_valid(name)
    assert path.read_text().strip() == name
    assert student_name.load_or_create(path) == name


def test_override_wins_and_invalid_override_is_ignored(tmp_path):
    path = tmp_path / ".session-name"
    assert student_name.load_or_create(path, "Grapes-Escape") == "Grapes-Escape"
    assert not path.exists()
    name = student_name.load_or_create(path, "not a name!")
    assert name != "not a name!" and student_name.is_valid(name)


def test_corrupt_file_is_replaced(tmp_path):
    path = tmp_path / ".session-name"
    path.write_text("???\n")
    name = student_name.load_or_create(path)
    assert student_name.is_valid(name) and path.read_text().strip() == name


def test_unwritable_location_still_gives_a_name(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("")
    assert student_name.is_valid(student_name.load_or_create(blocker / "x" / "name"))


def test_new_name_uses_two_capitalised_words():
    name = student_name.new_name(["grapes", "escape"], random.Random(1))
    assert sorted(name.split("-")) == ["Escape", "Grapes"]


def test_default_path(tmp_path, monkeypatch):
    monkeypatch.delenv("TRILOBOT_SESSION_NAME_FILE", raising=False)
    assert student_name.default_path(tmp_path) == tmp_path / ".session-name"
    monkeypatch.setenv("TRILOBOT_SESSION_NAME_FILE", str(tmp_path / "n"))
    assert student_name.default_path(tmp_path) == tmp_path / "n"

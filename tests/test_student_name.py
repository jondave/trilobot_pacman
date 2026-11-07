"""The app-owned session name: one per app process, never shared via disk."""

import random

import student_name


def test_each_pick_is_a_fresh_valid_name():
    names = {student_name.pick_name() for _ in range(20)}
    assert all(student_name.is_valid(name) for name in names)
    assert len(names) > 1  # two apps on one PC must not share a name


def test_override_wins_and_invalid_override_is_ignored():
    assert student_name.pick_name("Grapes-Escape") == "Grapes-Escape"
    name = student_name.pick_name("not a name!")
    assert name != "not a name!" and student_name.is_valid(name)


def test_new_name_uses_two_capitalised_words():
    name = student_name.new_name(["grapes", "escape"], random.Random(1))
    assert sorted(name.split("-")) == ["Escape", "Grapes"]

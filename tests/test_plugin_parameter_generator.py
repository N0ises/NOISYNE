from __future__ import annotations

from noisyne.audio.plugin.models import ProcessingGoal
from noisyne.audio.plugin.parameter_generator import ParameterGenerator


def test_eq_parameters():
    goal = ProcessingGoal(
        id="g1",
        description="reduce harshness",
        target="harsh high end",
        root_cause=None,
        action="cut 3 kHz",
        confidence=0.85,
    )

    params = ParameterGenerator().generate(goal, "eq")
    names = {p.name for p in params}

    assert "frequency" in names
    assert "gain" in names
    assert "q" in names


def test_compressor_parameters():
    goal = ProcessingGoal(
        id="g1",
        description="tighten dynamics",
        target="flat dynamics",
        root_cause=None,
        action="compress",
        confidence=0.85,
    )

    params = ParameterGenerator().generate(goal, "compressor")
    names = {p.name for p in params}

    assert "threshold" in names
    assert "ratio" in names
    assert "attack" in names
    assert "release" in names


def test_limiter_parameters():
    goal = ProcessingGoal(
        id="g1",
        description="raise loudness",
        target="loudness",
        root_cause=None,
        action="limit",
        confidence=0.85,
    )

    params = ParameterGenerator().generate(goal, "limiter")
    names = {p.name for p in params}

    assert "ceiling" in names
    assert "release" in names


def test_unknown_category_returns_empty():
    goal = ProcessingGoal(
        id="g1",
        description="x",
        target="x",
        root_cause=None,
        action="x",
        confidence=0.5,
    )

    assert ParameterGenerator().generate(goal, "utility") == []

from textutil import slugify


def test_lowercases_and_hyphenates():
    assert slugify("Hello World") == "hello-world"


def test_strips_punctuation():
    assert slugify("Agents, Harnesses & You!") == "agents-harnesses-you"


def test_collapses_whitespace_runs():
    assert slugify("  too   many    spaces ") == "too-many-spaces"


def test_preserves_digits():
    assert slugify("QCon SF 2026") == "qcon-sf-2026"


def test_empty_input():
    assert slugify("") == ""

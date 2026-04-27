"""Tests for utils/spell_check_engine.py — pure-Python, no Qt required."""
import sys
import types
import pytest

# ---------------------------------------------------------------------------
# Stubs: installed BEFORE importing utils.spell_check_engine
# ---------------------------------------------------------------------------

def _make_stubs():
    # --- qtpy ---
    qtpy = types.ModuleType("qtpy")
    qtcore = types.ModuleType("qtpy.QtCore")
    qtcore.Signal = lambda *a, **kw: None
    qtcore.QObject = object
    qtpy.QtCore = qtcore
    sys.modules.setdefault("qtpy", qtpy)
    sys.modules.setdefault("qtpy.QtCore", qtcore)

    # --- spylls ---
    spylls = types.ModuleType("spylls")
    hunspell = types.ModuleType("spylls.hunspell")
    dictionary_mod = types.ModuleType("spylls.hunspell.dictionary")

    class _DictionaryStub:
        @staticmethod
        def from_files(path):
            return None

    dictionary_mod.Dictionary = _DictionaryStub
    hunspell.dictionary = dictionary_mod
    spylls.hunspell = hunspell
    sys.modules.setdefault("spylls", spylls)
    sys.modules.setdefault("spylls.hunspell", hunspell)
    sys.modules.setdefault("spylls.hunspell.dictionary", dictionary_mod)

    # --- torch (pulled in by utils.download_util) ---
    torch_mod = types.ModuleType("torch")
    torch_hub = types.ModuleType("torch.hub")
    torch_hub.download_url_to_file = lambda *a, **kw: None
    torch_hub.get_dir = lambda: "/tmp"
    torch_mod.hub = torch_hub
    sys.modules.setdefault("torch", torch_mod)
    sys.modules.setdefault("torch.hub", torch_hub)

    # --- utils.download_util ---
    dl_mod = types.ModuleType("utils.download_util")
    dl_mod.download_and_check_files = lambda *a, **kw: None
    sys.modules["utils.download_util"] = dl_mod

_make_stubs()

from utils.spell_check_engine import SpellCheckEngine  # noqa: E402

# ---------------------------------------------------------------------------
# Fake dictionary
# ---------------------------------------------------------------------------

class _FakeDict:
    """Minimal stand-in for a spylls Hunspell dictionary."""

    _known = {"hello", "world", "test", "python"}

    def lookup(self, word: str) -> bool:
        return word.lower() in self._known

    def suggest(self, word: str):
        return [word + "_suggestion"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engine():
    engine = SpellCheckEngine.__new__(SpellCheckEngine)
    engine.dictionary = _FakeDict()
    engine.lang = "en"
    engine.skipped_words = []
    return engine

def _unknown(text: str):
    """Return list of (word, idx) tuples for unknown words in text."""
    return _engine().GetUnknownWordsViaDictionaryFromList([(text, 0)])

# ---------------------------------------------------------------------------
# Tests: GetUnknownWordsViaDictionaryFromList
# ---------------------------------------------------------------------------

class TestGetUnknownWords:

    def test_all_known_returns_empty(self):
        assert _unknown("hello world") == []

    def test_unknown_word_returned(self):
        result = _unknown("hello xyzzy")
        words = [w for w, _ in result]
        assert "xyzzy" in words

    def test_mixed_case_known_word_not_flagged(self):
        assert _unknown("Hello World") == []

    def test_punctuation_stripped_before_lookup(self):
        assert _unknown("hello, world!") == []

    def test_empty_string_returns_empty(self):
        assert _unknown("") == []

    def test_multiple_unknown_words(self):
        result = _unknown("foo bar baz")
        words = {w for w, _ in result}
        assert words == {"foo", "bar", "baz"}

    def test_numbers_not_flagged(self):
        assert _unknown("42 3.14 $100") == []

    def test_skipped_words_not_flagged(self):
        eng = _engine()
        eng.skipped_words = ["xyzzy"]
        result = eng.GetUnknownWordsViaDictionaryFromList([("hello xyzzy", 0)])
        words = [w for w, _ in result]
        assert "xyzzy" not in words

# ---------------------------------------------------------------------------
# Tests: DoSuggest
# ---------------------------------------------------------------------------

class TestDoSuggest:

    def test_suggest_returns_list(self):
        assert isinstance(_engine().DoSuggest("xyzzy"), list)

    def test_suggest_non_empty_for_unknown(self):
        assert len(_engine().DoSuggest("xyzzy")) > 0

# ---------------------------------------------------------------------------
# Tests: is_number
# ---------------------------------------------------------------------------

class TestIsNumber:

    def test_plain_integer(self):
        assert _engine().is_number("42") is True

    def test_float(self):
        assert _engine().is_number("3.14") is True

    def test_currency(self):
        assert _engine().is_number("$100") is True

    def test_word_not_number(self):
        assert _engine().is_number("hello") is False
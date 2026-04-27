# Implementation Plan

[Overview]
Refactor the BallonsTranslator UI layer to improve code quality, maintainability, and correctness without changing external behaviour.

This plan addresses accumulated technical debt in the UI layer, primarily introduced during the SpellCheck3 feature (`87fcbe1`) and the AutoFontSize work. The codebase has three main pain points: (1) dead/commented-out code bloating key files, (2) architectural issues where Qt undo commands mutate state in their constructors and where a deleted-word handler triggers a full UI rebuild, and (3) an overly complex `layout_textblk()` function that handles two fundamentally different modes in one 170-line body. No external behaviour changes are intended; existing functionality must remain identical after each step.

[Types]
No new types are introduced; existing type annotations are corrected.

Corrections needed:
- `WordListPanel.set_words(words: List[str])` — actual argument type is `List[Tuple[str, int]]`, not `List[str]`. Change annotation to `List[Tuple[str, int]]`.
- `WordListPanel.word_selected = Signal(str, object)` — the `object` is always `int` (block index). Change to `Signal(str, int)`.
- `SceneTextManager.on_spell_word_clicked(self, word: str, idx: object)` — `idx` is always `int`. Change annotation to `int`.

[Files]
Files modified and new files created in this refactor.

**Modified files:**
- `ui/scenetext_manager.py` — remove duplicate `EmptyCommand`, fix `onWordDeleted`, simplify `_on_source_text_changed`, split `layout_textblk()` into dispatcher + two private methods, fix type annotations
- `ui/drawing_commands.py` — move auto-layout state mutation out of `RunBlkTransCommand.__init__` into `redo()`; keep `EmptyCommand` here as the single definition
- `ui/text_advanced_format.py` — remove commented-out code blocks in `WordListPanel`; fix type annotations on `set_words`, `word_selected`, `add_word_item`
- `utils/spell_check_engine.py` — remove ~200 lines of commented-out legacy code; keep only active methods
- `ui/mainwindow.py` — remove commented-out SpellCheck block (lines 1503–1542) and related dead imports/comments

**New files:**
- `tests/test_spell_check_engine.py` — unit tests for `SpellCheckEngine` (no Qt dependency)
- `tests/test_textblock.py` — unit tests for `TextBlock` data model
- `tests/test_layout_utils.py` — unit tests for `get_text_size` helper and `get_words_length_list`

[Functions]
Functions modified and new functions added.

**Modified functions:**

- `SceneTextManager.onWordDeleted(word: str)` in `ui/scenetext_manager.py`
  - Current: calls `self.updateSceneTextitems()` — full UI rebuild
  - Change: call `self.updateUnknownWordsPanel()` instead

- `SceneTextManager._on_source_text_changed()` in `ui/scenetext_manager.py`
  - Current: manually sets `textblock.text = new_text` (duplicates `updateTextBlkList` logic) then calls `updateUnknownWordsPanel()`
  - Change: remove the manual model update; just call `updateUnknownWordsPanel()` directly. The model is already kept in sync by `updateTextBlkList()` before save/translate

- `SceneTextManager.layout_textblk(...)` in `ui/scenetext_manager.py`
  - Current: 170-line function with two modes selected by `if self.auto_textlayout_flag and ...`
  - Change: keep `layout_textblk` as a thin dispatcher that calls either `_layout_textblk_auto` or `_layout_textblk_mask`

- `RunBlkTransCommand.__init__(...)` in `ui/drawing_commands.py`
  - Current: applies layout changes (setFontSize, setPlainText, set_size, setPlainTextAndKeepUndoStack) directly in `__init__`
  - Change: `__init__` only saves old state (old_html, old_font_size, old_rect, old_text); actual application is moved to `redo()`

- `RunBlkTransCommand.redo()` in `ui/drawing_commands.py`
  - Change: add the state-application logic previously in `__init__`; first call skips reapplication (op_counter guard, same pattern already used in other commands)

- `WordListPanel.set_words(words)` in `ui/text_advanced_format.py`
  - Fix type annotation: `List[Tuple[str, int]]`

**New functions:**

- `SceneTextManager._layout_textblk_auto(blkitem, text, restore_charfmts, char_fmts)` in `ui/scenetext_manager.py`
  - Extracted auto-mode body from `layout_textblk`; returns `True` on success

- `SceneTextManager._layout_textblk_mask(blkitem, text, restore_charfmts, char_fmts, mask, bounding_rect, region_rect)` in `ui/scenetext_manager.py`
  - Extracted mask-based mode body from `layout_textblk`; returns `True` on success

[Classes]
No new classes. One class receives annotation fixes.

**Modified classes:**

- `WordListPanel` in `ui/text_advanced_format.py`
  - Remove ~25 lines of commented-out `_adjust_size` / `adjust_panel_height` code
  - Fix `word_selected` signal type: `Signal(str, int)`
  - Fix `add_word_item(word: str, textblock_obj: int)` annotation

- `SpellCheckEngine` in `utils/spell_check_engine.py`
  - Remove all commented-out legacy methods (`UnknownWords`, `Handle`, `GetUnknownWordsViaDictionary`, `CountUnknownWordsViaDictionary`, etc.) — approximately 200 lines
  - Active public API remains: `__init__`, `DoSuggest`, `GetUnknownWordsViaDictionaryFromList`, `onWordDeleted`, `is_number`, `_load_data`, `_save_data`

[Dependencies]
No new dependencies. No changes to `requirements.txt`.

Tests use only `pytest` (already available) and mock standard library for file I/O in spell check tests.

[Testing]
Tests cover the pure-Python logic that has no Qt dependency.

**`tests/test_spell_check_engine.py`:**
- `test_is_number` — verify numeric strings are classified as numbers
- `test_known_word_not_flagged` — common English words pass lookup (requires dictionary files; skip if not downloaded)
- `test_skipped_word_ignored` — words in `skipped_words` are not returned as unknown
- `test_save_load_roundtrip` — `_save_data` / `_load_data` persists and restores `skipped_words`
- `test_on_word_deleted_adds_to_skipped` — `onWordDeleted` appends to `skipped_words`
- `test_get_unknown_words_empty_input` — empty list returns empty result
- `test_get_unknown_words_strips_punctuation` — punctuation stripped before lookup

**`tests/test_textblock.py`:**
- `test_textblock_get_text_single` — `get_text()` with single string in list
- `test_textblock_get_text_multiple` — `get_text()` joins multiple lines
- `test_textblock_adjust_pos` — `adjust_pos` shifts coordinates correctly
- `test_bounding_rect` — `bounding_rect()` returns xywh from xyxy

**`tests/test_layout_utils.py`:**
- These require a QApplication; use `pytest-qt` fixture or skip if Qt unavailable
- `test_get_text_size_nonempty` — returns positive width and height
- `test_get_words_length_list_count` — output length equals input word count
- `test_get_words_length_list_positive` — all lengths > 0 for non-empty words

[Implementation Order]
Steps ordered to minimise risk — each step leaves the codebase in a working state.

1. Remove duplicate `EmptyCommand` from `scenetext_manager.py`; add import from `drawing_commands.py`. Verify no runtime import errors.

2. Remove commented-out dead code from `utils/spell_check_engine.py` (~200 lines). No behaviour change.

3. Remove commented-out SpellCheck block from `ui/mainwindow.py` (lines 1503–1542) and associated dead import comments.

4. Remove commented-out code from `ui/text_advanced_format.py` (`WordListPanel.adjust_panel_height` comments). Fix type annotations on `set_words`, `word_selected`, `add_word_item`, `_on_word_clicked`.

5. Fix `SceneTextManager.onWordDeleted` — replace `updateSceneTextitems()` with `updateUnknownWordsPanel()`.

6. Simplify `SceneTextManager._on_source_text_changed` — remove manual `textblock.text = new_text`; just call `updateUnknownWordsPanel()`.

7. Fix `SceneTextManager.on_spell_word_clicked` type annotation (`idx: int`).

8. Split `layout_textblk()` into `_layout_textblk_auto()` and `_layout_textblk_mask()`; leave `layout_textblk` as dispatcher. Verify auto-layout and manual layout still work.

9. Refactor `RunBlkTransCommand.__init__` to only save state; move application logic to `redo()` with op_counter guard.

10. Write `tests/test_spell_check_engine.py` with mocked file I/O and optional dictionary tests.

11. Write `tests/test_textblock.py`.

12. Write `tests/test_layout_utils.py`.
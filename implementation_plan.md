# Implementation Plan

[Overview]
Eliminate the three-way text duplication across TextBlock (data model), TextBlkItem (canvas scene item), and TransPairWidget (right panel) by introducing sync methods that make TextBlock the single source of truth for translation and source text.

The core problem: translation text is stored and synchronised in three places — `TextBlkItem.toPlainText()/toHtml()` (canvas), `TransPairWidget.e_trans.toPlainText()` (right panel), and `TextBlock.translation/rich_text` (JSON model). Source text is duplicated between `TransPairWidget.e_source.toPlainText()` and `TextBlock.text`. Synchronisation code is scattered across `layout_textblk()`, `RunBlkTransCommand`, `updateTextBlkList()`, `updateTranslation()`, and `addTextBlock()`.

The solution introduces `_sync_translation_to_ui(blkitem)` and `_sync_source_to_ui(blkitem)` on `SceneTextManager` that write `TextBlock.translation` → `TextBlkItem.setPlainText()` + `e_trans.setPlainTextAndKeepUndoStack()`, and `TextBlock.text` → `e_source.setPlainTextAndKeepUndoStack()`. All direct widget writes are replaced with sync calls. `RunBlkTransCommand` is simplified to only save/restore `TextBlock.translation` and call the sync method. Undo/redo continues working via the widgets' own undo stacks.

Secondary cleanups: remove `ensure_text_in_block()`, remove `LOGGER.debug` from `get_words_length_list()` loop, remove duplicate `EmptyCommand` from `drawing_commands.py`.

[Types]
No new types or type changes.

[Files]

**Modified files:**
- `ui/scenetext_manager.py` — add `_sync_translation_to_ui()` and `_sync_source_to_ui()` methods; replace all direct `e_trans.setPlainText()`, `e_source.setPlainText()`, `blkitem.setPlainText()` writes with sync calls; remove `ensure_text_in_block()`; update `addTextBlock`, `_layout_textblk_auto`, `_layout_textblk_mask`, `updateTranslation`
- `ui/drawing_commands.py` — simplify `RunBlkTransCommand._apply_text_state()` to only set `blk.blk.translation` and rely on sync from caller; remove duplicate `EmptyCommand` class (already exists in `scenetext_manager` import from `drawing_commands`)

[Functions]

**New functions:**

- `SceneTextManager._sync_translation_to_ui(blkitem: TextBlkItem)` in `ui/scenetext_manager.py`
  - Reads `blkitem.blk.translation`
  - Writes to `blkitem.setPlainText(blkitem.blk.translation)`
  - Writes to `pairwidget_list[blkitem.idx].e_trans.setPlainTextAndKeepUndoStack(blkitem.blk.translation)`

- `SceneTextManager._sync_source_to_ui(blkitem: TextBlkItem)` in `ui/scenetext_manager.py`
  - Reads `blkitem.blk.get_text()`
  - Writes to `pairwidget_list[blkitem.idx].e_source.setPlainTextAndKeepUndoStack(blkitem.blk.get_text())`

**Modified functions:**

- `SceneTextManager._layout_textblk_auto(blkitem, text, ...)` — replace `blkitem.setPlainText(text)` + `e_trans.setPlainText(text)` with `blkitem.blk.translation = text` + `_sync_translation_to_ui(blkitem)` (after measurement loop, not inside it — the loop uses blockSignals so it's safe)
- `SceneTextManager._layout_textblk_mask(blkitem, text, ...)` — replace `blkitem.setPlainText(new_text)` + `e_trans.setPlainText(new_text)` with `blkitem.blk.translation = new_text` + `_sync_translation_to_ui(blkitem)`
- `SceneTextManager.addTextBlock(blk)` — replace `pair_widget.e_source.setPlainText(blk_item.blk.get_text())` with `_sync_source_to_ui(blk_item)`; replace `pair_widget.e_trans.setPlainText(blk_item.toPlainText())` with `_sync_translation_to_ui(blk_item)`
- `SceneTextManager.updateTranslation()` — replace `transwidget.e_trans.setPlainText(blk_item.blk.translation)` + `blk_item.setPlainText(blk_item.blk.translation)` with `_sync_translation_to_ui(blk_item)` for each block
- `RunBlkTransCommand._apply_text_state()` in `ui/drawing_commands.py` — simplify: remove direct `blkitem.setPlainText`, `blkitem.setFontSize`, `blkitem.set_size`, `transpairw.e_trans.setPlainTextAndKeepUndoStack` calls. Set `blk.blk.translation = trs` and store layout_data. `redo()` calls `_sync_translation_to_ui` after `_apply_text_state()`. `undo()` restores `blk.blk.translation` from saved state and calls `_sync_translation_to_ui`.
- `get_words_length_list()` in `ui/scenetext_manager.py` — remove the `LOGGER.debug` line from the loop

**Removed functions:**
- `SceneTextManager.ensure_text_in_block(blkitem)` — remove entirely; its purpose was a workaround for desync between blkitem and e_trans

**Removed classes (modified):**
- `EmptyCommand` in `ui/drawing_commands.py` — remove the class definition (it's only used via import in `scenetext_manager.py` which already imports from `drawing_commands`)

[Dependencies]
No new dependencies. No changes to `requirements.txt`.

[Testing]

Manual testing required:
- Auto-layout text blocks: verify e_trans and blkitem stay in sync
- Mask-based layout text blocks: verify e_trans and blkitem stay in sync  
- Undo/redo of `RunBlkTransCommand`: verify text state restores correctly
- Saving/loading projects: verify `updateTextBlkList()` captures correct state
- `updateSceneTextitems()`: verify all widgets rebuild with correct text
- Source text editing: verify e_source changes propagate correctly
- Spell check word panel: verify unknown words list still works

[Implementation Order]
Steps ordered to minimise risk — each step leaves the codebase in a working state.

1. Add `_sync_translation_to_ui()` and `_sync_source_to_ui()` to `scenetext_manager.py`. Verify they compile.

2. Replace direct `e_trans.setPlainText` + `blkitem.setPlainText` in `_layout_textblk_auto()` with `blkitem.blk.translation = text` + `_sync_translation_to_ui(blkitem)` (after the font-size binary search loop — the loop internally uses blockSignals so it's safe).

3. Replace direct `e_trans.setPlainText` + `blkitem.setPlainText` in `_layout_textblk_mask()` with `blkitem.blk.translation = new_text` + `_sync_translation_to_ui(blkitem)`.

4. Replace direct widget sets in `addTextBlock()` with sync calls.

5. Replace `updateTranslation()` body with sync loop.

6. Simplify `RunBlkTransCommand._apply_text_state()` to only save state + set `blk.blk.translation`. Remove all direct `blkitem.set*` and `transpairw.e_trans.set*` calls. After `_apply_text_state()` in `redo()`, call `_sync_translation_to_ui`. In `undo()`, restore `blk.blk.translation` from saved layout_data and call `_sync_translation_to_ui`.

7. Remove `ensure_text_in_block()` method.

8. Remove `LOGGER.debug` from `get_words_length_list()` loop.

9. Remove `EmptyCommand` class definition from `drawing_commands.py` (it's only used via import).
"""Tests for utils/textblock.py — no Qt required."""
import pytest
from utils.textblock import TextBlock, TextAlignment


class TestTextBlockBasics:
    def test_default_translation_empty(self):
        blk = TextBlock()
        assert blk.translation == ""

    def test_set_and_get_translation(self):
        blk = TextBlock()
        blk.translation = "Hello"
        assert blk.translation == "Hello"

    def test_get_text_returns_joined_lines(self):
        blk = TextBlock()
        blk.text = ["line one", "line two"]
        result = blk.get_text()
        assert "line one" in result
        assert "line two" in result

    def test_get_text_empty_list(self):
        blk = TextBlock()
        blk.text = []
        assert blk.get_text() == ""

    def test_rich_text_default_empty(self):
        blk = TextBlock()
        assert blk.rich_text == ""

    def test_vertical_default_false(self):
        blk = TextBlock()
        assert blk.vertical is False

    def test_font_size_positive(self):
        blk = TextBlock()
        blk.font_size = 14.0
        assert blk.font_size == pytest.approx(14.0)

    def test_alignment_default(self):
        blk = TextBlock()
        assert blk.alignment in list(TextAlignment)


class TestTextBlockBoundingRect:
    def test_bounding_rect_requires_lines(self):
        """bounding_rect() requires at least one line; verify it works after set_lines_by_xywh."""
        blk = TextBlock()
        blk.set_lines_by_xywh(
            [0, 0, 80, 40],
            angle=0,
            x_range=[0, 800],
            y_range=[0, 600],
            adjust_bbox=True,
        )
        br = blk.bounding_rect()
        assert isinstance(br, (list, tuple))
        assert len(br) >= 4

    def test_set_lines_by_xywh_updates_bbox(self):
        blk = TextBlock()
        blk.set_lines_by_xywh(
            [10, 20, 100, 50],
            angle=0,
            x_range=[0, 800],
            y_range=[0, 600],
            adjust_bbox=True,
        )
        br = blk.bounding_rect()
        assert len(br) >= 4


class TestTextBlockFontColors:
    def test_set_font_colors_fg(self):
        blk = TextBlock()
        blk.set_font_colors(fg_colors=(255, 0, 0))
        # Should not raise; exact storage format is internal

    def test_set_font_colors_bg(self):
        blk = TextBlock()
        blk.set_font_colors(bg_colors=(0, 0, 255))

    def test_set_font_colors_both(self):
        blk = TextBlock()
        blk.set_font_colors(fg_colors=(255, 255, 0), bg_colors=(0, 0, 0))


class TestTextBlockStrokeWidth:
    def test_recalculate_stroke_width_no_crash(self):
        blk = TextBlock()
        blk.recalulate_stroke_width()

    def test_stroke_width_non_negative(self):
        blk = TextBlock()
        blk.recalulate_stroke_width()
        assert blk.stroke_width >= 0
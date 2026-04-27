"""Tests for utils/text_layout.py — no Qt required."""
import pytest
from utils.text_layout import Line


class TestLine:
    def test_empty_line_has_zero_words(self):
        line = Line()
        assert line.num_words == 0

    def test_line_with_text_has_one_word(self):
        line = Line(text="hello")
        assert line.num_words == 1

    def test_initial_length(self):
        line = Line(text="hi", length=20)
        # length may include added spacing — just check it is >= 20
        assert line.length >= 20

    def test_append_right_increases_length(self):
        line = Line(text="hello", length=50)
        before = line.length
        line.append_right("world", 40, delimiter=" ")
        assert line.length > before

    def test_append_right_increments_word_count(self):
        line = Line(text="hello", length=50)
        line.append_right("world", 40, delimiter=" ")
        assert line.num_words == 2

    def test_append_right_empty_word_no_count_change(self):
        line = Line(text="hello", length=50)
        count_before = line.num_words
        line.append_right("", 0)
        assert line.num_words == count_before

    def test_append_left_prepends_text(self):
        line = Line(text="world", length=50)
        line.append_left("hello", 50, delimiter=" ")
        assert line.text.startswith("hello")

    def test_append_left_increments_word_count(self):
        line = Line(text="world", length=50)
        line.append_left("hello", 50, delimiter=" ")
        assert line.num_words == 2

    def test_add_spacing_expands_length(self):
        line = Line(text="hi", pos_x=10, length=40)
        original_length = line.length
        line.add_spacing(5)
        assert line.length > original_length

    def test_strip_spacing_restores_length(self):
        line = Line(text="hi", pos_x=10, length=40, spacing=5)
        length_with_spacing = line.length
        line.strip_spacing()
        assert line.length < length_with_spacing
        assert line.spacing == 0

    def test_strip_spacing_adjusts_pos_x(self):
        spacing = 8
        line = Line(text="hi", pos_x=10, length=40, spacing=spacing)
        original_pos_x = line.pos_x
        line.strip_spacing()
        assert line.pos_x == original_pos_x + spacing

    def test_round_trip_spacing(self):
        """add_spacing then strip_spacing returns to original length."""
        line = Line(text="hi", pos_x=20, length=60)
        original_length = line.length
        original_pos_x = line.pos_x
        line.add_spacing(10)
        line.strip_spacing()
        assert line.length == original_length
        assert line.pos_x == original_pos_x
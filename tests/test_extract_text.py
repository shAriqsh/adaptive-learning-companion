"""Tests for the shared extract_text utility."""

from backend.app.utils.content import extract_text


class TestExtractText:
    """extract_text should handle every content format Gemini may return."""

    def test_string_input(self):
        assert extract_text("hello world") == "hello world"

    def test_empty_string(self):
        assert extract_text("") == ""

    def test_none_input(self):
        assert extract_text(None) == ""

    def test_list_of_dicts(self):
        content = [
            {"text": "First paragraph."},
            {"text": "Second paragraph."},
        ]
        assert extract_text(content) == "First paragraph.\nSecond paragraph."

    def test_list_skips_non_text_blocks(self):
        content = [
            {"text": "Keep this."},
            {"type": "image", "url": "http://example.com/img.png"},
            {"text": "And this."},
        ]
        assert extract_text(content) == "Keep this.\nAnd this."

    def test_empty_list(self):
        assert extract_text([]) == ""

    def test_non_dict_list_items_skipped(self):
        content = ["not a dict", 42, {"text": "valid"}]
        assert extract_text(content) == "valid"

    def test_fallback_to_str(self):
        """Anything that isn't str, list, or None should be str()-ified."""
        assert extract_text(42) == "42"
        assert extract_text(3.14) == "3.14"

    def test_dict_with_empty_text(self):
        content = [{"text": ""}, {"text": "hello"}]
        assert extract_text(content) == "\nhello"

    def test_single_block_list(self):
        content = [{"text": "only one"}]
        assert extract_text(content) == "only one"

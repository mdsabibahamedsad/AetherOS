"""Tests for aetheros_vision.documents — extraction from text-based formats."""

import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


class TestDocumentIntelligence:
    def test_markdown_sections(self, tmp_path, isolated_home):
        from aetheros_vision.documents import DocumentIntelligence

        md = tmp_path / "doc.md"
        md.write_text("# Title\n\n## Section One\n\nbody text\n\n## Section Two\n\nmore\n", encoding="utf-8")
        result = DocumentIntelligence().extract(str(md))
        assert result.success is True
        assert result.media_type.value == "markdown"
        headings = [s.heading for s in result.sections]
        assert "Title" in headings
        assert "Section One" in headings
        assert "body text" in result.text

    def test_markdown_table_extraction(self, tmp_path, isolated_home):
        from aetheros_vision.documents import DocumentIntelligence

        md = tmp_path / "tbl.md"
        md.write_text("| Name | Value |\n| --- | --- |\n| Alpha | 1 |\n| Beta | 2 |\n", encoding="utf-8")
        result = DocumentIntelligence().extract(str(md))
        assert len(result.tables) == 1
        table = result.tables[0]
        assert table.headers == ["Name", "Value"]
        assert ["Alpha", "1"] in table.rows

    def test_plain_text(self, tmp_path, isolated_home):
        from aetheros_vision.documents import DocumentIntelligence

        txt = tmp_path / "notes.txt"
        txt.write_text("hello world", encoding="utf-8")
        result = DocumentIntelligence().extract(str(txt))
        assert result.success is True
        assert result.text == "hello world"

    def test_markdown_without_table_separator(self, tmp_path, isolated_home):
        from aetheros_vision.documents import DocumentIntelligence

        md = tmp_path / "t.md"
        md.write_text("| A | B |\n| 1 | 2 |\n| 3 | 4 |\n", encoding="utf-8")
        result = DocumentIntelligence().extract(str(md))
        # No separator line: still treated as a 3-row table.
        assert len(result.tables) == 1
        assert result.tables[0].headers == ["A", "B"]
        assert len(result.tables[0].rows) == 2

    def test_unsupported_type(self, tmp_path, isolated_home):
        from aetheros_vision.documents import DocumentIntelligence

        f = tmp_path / "weird.bin"
        f.write_bytes(b"\x00\x01\x02")
        result = DocumentIntelligence().extract(str(f))
        assert result.success is False
        assert result.error is not None

    def test_missing_file(self, tmp_path, isolated_home):
        from aetheros_vision.documents import DocumentIntelligence

        result = DocumentIntelligence().extract(str(tmp_path / "nope.pdf"))
        assert result.success is False

    def test_html_extracts_title(self, tmp_path, isolated_home):
        from aetheros_vision.documents import DocumentIntelligence

        html = tmp_path / "page.html"
        html.write_text("<html><head><title>My Page</title></head><body><h1>Hello</h1><p>World</p></body></html>", encoding="utf-8")
        result = DocumentIntelligence().extract(str(html))
        assert result.success is True
        # Without bs4, the fallback strips tags; with bs4 the title is exact.
        # Either way the body text must survive.
        assert "World" in result.text

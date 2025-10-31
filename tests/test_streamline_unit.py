from typing import Dict, Any, List
from pdf_annot.streamline_annotations import (
    normalize_text,
    extract_heading_label,
    is_link,
    process_objects,
)


def make_input(
    *,
    annot_type_first: int = 8,
    page_num: int = 0,
    content: str = "",
    extracted: str = "",
    title: str = "t",
    cdate: str = "c",
    mdate: str = "m",
) -> Dict[str, Any]:
    return {
        "annotType": [annot_type_first],
        "pageNum": page_num,
        "info": {
            "content": content,
            "extractedText": extracted,
            "title": title,
            "creationDate": cdate,
            "modDate": mdate,
        },
    }


# --- FIX: Moved 'run_objs' out of the class and removed 'self' ---
def run_objs(objs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return process_objects(objs)


class TestNormalization:
    def test_normalize_text_whitespace(self):
        assert normalize_text("  a \n b\tc  ") == "a b c"
        assert normalize_text(None) == ""
        assert normalize_text("") == ""


class TestHeadingExtraction:
    def test_heading_cases(self):
        for s in ["H1", "h2", "H3", "h4", "H5", "h6"]:
            label = extract_heading_label(s)
            assert label is not None
            assert label[0] == "H"
            assert label[1] in "123456"

    def test_non_heading(self):
        assert extract_heading_label("H7") is None
        assert extract_heading_label("Heading") is None
        assert extract_heading_label("") is None


class TestLinkLogicWithObjects:
    def test_simple_merge(self):
        objs = [
            make_input(content="note", extracted="A-"),
            make_input(content="link", extracted="B"),
            make_input(content="note", extracted="C"),
        ]
        out = run_objs(objs)  # Use module-level function
        assert len(out) == 2
        assert out[0]["highlightText"] == "AB"
        assert out[0]["commentText"] == "note"
        assert out[1]["highlightText"] == "C"

    def test_consecutive_links_ignored(self):
        objs = [
            make_input(content="note", extracted="Hello"),
            make_input(content="link", extracted="world"),
            make_input(content="link", extracted="again"),
            make_input(content="note", extracted="Done"),
        ]
        out = run_objs(objs)  # Use module-level function
        assert len(out) == 2
        assert out[0]["highlightText"] == "Hello world"
        assert out[1]["highlightText"] == "Done"

    def test_link_without_pending_creates_record(self):
        objs = [
            make_input(content="link", extracted="Start here"),
            make_input(content="note", extracted="Next"),
        ]
        out = run_objs(objs)  # Use module-level function
        assert len(out) == 2
        assert out[0]["highlightText"] == "Start here"
        assert out[0]["commentText"] == ""
        assert out[0]["header"] == ""

    def test_link_with_empty_text_when_pending_does_not_change(self):
        objs = [
            make_input(content="note", extracted="Base"),
            make_input(content="link", extracted=""),
            make_input(content="note", extracted="Next"),
        ]
        out = run_objs(objs)  # Use module-level function
        assert out[0]["highlightText"] == "Base"
        assert out[1]["highlightText"] == "Next"

    def test_header_sets_comment_empty(self):
        objs = [
            make_input(content="h2", extracted="Heading A"),
            make_input(content="note", extracted="Text"),
        ]
        out = run_objs(objs)  # Use module-level function
        assert out[0]["header"] == "H2"
        assert out[0]["commentText"] == ""
        assert out[1]["commentText"] == "note"

    def test_filter_keeps_only_annot_type_8(self):
        objs = [
            make_input(annot_type_first=7, content="note", extracted="A"),
            make_input(annot_type_first=8, content="note", extracted="B"),
            make_input(annot_type_first=9, content="note", extracted="C"),
        ]
        out = run_objs(objs)  # Use module-level function
        assert len(out) == 1
        assert out[0]["highlightText"] == "B"

    def test_merge_across_pages(self):
        objs = [
            make_input(page_num=0, content="note", extracted="Part 1 of"),
            make_input(page_num=1, content="link", extracted=" the sentence."),
            make_input(page_num=1, content="note", extracted="Next"),
        ]
        out = run_objs(objs)  # Use module-level function
        assert out[0]["highlightText"] == "Part 1 of the sentence."
        assert out[1]["highlightText"] == "Next"

    def test_dash_space_removed_and_whitespace_collapsed_after_merge(self):
        objs = [
            make_input(content="note", extracted="A- "),
            make_input(content="link", extracted="  B \n C  "),
            make_input(content="note", extracted="X"),
        ]
        out = run_objs(objs)  # Use module-level function
        assert out[0]["highlightText"] == "ABC"

    def test_is_link_case_insensitive(self):
        for s in ["link", "Link", "LINK", "lInK"]:
            assert is_link(s)
        assert not is_link("links")

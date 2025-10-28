# tests/test_frontmatter.py
from __future__ import annotations

import textwrap

from pdf_annot.frontmatter import format_note, parse_note, upsert_fields


def test_parse_note_without_front_matter():
    body = "Hello\nWorld\n"
    pn = parse_note(body)
    assert pn.has_fm is False
    assert pn.front_matter == {}
    assert pn.body == body


def test_parse_note_with_front_matter_simple():
    text = textwrap.dedent(
        """\
        ---
        a: 1
        b: two
        ---
        Body line
        """
    )
    pn = parse_note(text)
    assert pn.has_fm is True
    assert pn.front_matter == {"a": 1, "b": "two"}
    assert pn.body == "Body line\n"


def test_format_note_omits_fm_when_empty():
    out = format_note({}, "Body\n")
    assert out == "Body\n"


def test_upsert_adds_fields_to_empty_note_minimal():
    body = "Content\n"
    changed, new_text = upsert_fields(body, {"pdf_title": "Open Mind, Open Heart", "pdf_size": 12345})
    assert changed is True
    # Should create a YAML block with the two keys, then the body
    assert new_text.startswith("---\n")
    assert "pdf_title: Open Mind, Open Heart\n" in new_text
    assert "pdf_size: 12345\n" in new_text
    assert new_text.endswith("Content\n")


def test_upsert_updates_changed_value_and_preserves_others():
    text = textwrap.dedent(
        """\
        ---
        category: book
        tags:
          - meditation
        pdf_title: Old Title
        ---
        Original body
        """
    )
    changed, new_text = upsert_fields(text, {"pdf_title": "Open Mind, Open Heart", "pdf_size": 4321})
    assert changed is True
    # Reparse to check structure
    from pdf_annot.frontmatter import parse_note

    pn = parse_note(new_text)
    assert pn.front_matter["pdf_title"] == "Open Mind, Open Heart"
    assert pn.front_matter["pdf_size"] == 4321
    # Non-target keys still present
    assert pn.front_matter["category"] == "book"
    assert pn.front_matter["tags"] == ["meditation"]
    assert pn.body == "Original body\n"


def test_upsert_is_byte_stable_when_no_change_needed():
    text = textwrap.dedent(
        """\
        ---
        pdf_title: Open Mind, Open Heart
        pdf_size: 123
        other: keep
        ---
        Body
        """
    )
    changed, new_text = upsert_fields(text, {"pdf_title": "Open Mind, Open Heart", "pdf_size": 123})
    assert changed is False
    assert new_text == text


def test_upsert_keeps_existing_target_if_not_in_updates():
    text = textwrap.dedent(
        """\
        ---
        pdf_title: Foo
        other: x
        ---
        Body
        """
    )
    changed, new_text = upsert_fields(text, {"pdf_size": 9})
    assert changed is True
    pn = parse_note(new_text)
    # pdf_title preserved, pdf_size added
    assert pn.front_matter["pdf_title"] == "Foo"
    assert pn.front_matter["pdf_size"] == 9
    assert pn.front_matter["other"] == "x"


def test_unicode_diacritics_in_title_roundtrip():
    body = "B\n"
    changed, new_text = upsert_fields(body, {"pdf_title": "Überlegung – Étude", "pdf_size": 7})
    assert changed is True
    pn = parse_note(new_text)
    assert pn.front_matter["pdf_title"] == "Überlegung – Étude"
    assert pn.front_matter["pdf_size"] == 7
    assert pn.body == "B\n"

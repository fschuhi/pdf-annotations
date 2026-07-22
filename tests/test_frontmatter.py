# tests/test_frontmatter.py
from __future__ import annotations

import textwrap
from datetime import date, datetime

from pdf_annot.frontmatter import as_timestamp, format_note, parse_note, upsert_fields


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
    changed, new_text = upsert_fields(body, {"pdf_title": "Überlegung — Étude", "pdf_size": 7})
    assert changed is True
    pn = parse_note(new_text)
    assert pn.front_matter["pdf_title"] == "Überlegung — Étude"
    assert pn.front_matter["pdf_size"] == 7
    assert pn.body == "B\n"


def test_upsert_handles_all_pdf_metadata_fields():
    """Test that all PDF-related metadata fields are properly updated."""
    text = textwrap.dedent(
        """\
        ---
        pdf_id: "(Smith 2020)"
        pdf_title: Old Title
        pdf_size: 1000
        other: keep_this
        ---
        Body content
        """
    )

    updates = {
        "pdf_id": "(Smith 2020)",  # unchanged
        "pdf_title": "New Title",  # changed
        "pdf_size": 2000,  # changed
        "pdf_hash": "ABC123X",  # new
        "has_annotations": True,  # new
        "pdf_mtime": "2025-10-30T20:00:00",  # new
        "last_run_at": "2025-10-30T20:01:00",  # new
    }

    changed, new_text = upsert_fields(text, updates)
    assert changed is True

    pn = parse_note(new_text)
    assert pn.front_matter["pdf_id"] == "(Smith 2020)"
    assert pn.front_matter["pdf_title"] == "New Title"
    assert pn.front_matter["pdf_size"] == 2000
    assert pn.front_matter["pdf_hash"] == "ABC123X"
    assert pn.front_matter["has_annotations"] is True
    assert pn.front_matter["pdf_mtime"] == "2025-10-30T20:00:00"
    assert pn.front_matter["last_run_at"] == "2025-10-30T20:01:00"
    # Non-target key preserved
    assert pn.front_matter["other"] == "keep_this"
    assert pn.body == "Body content\n"


def test_upsert_byte_stable_when_all_fields_unchanged():
    """Test byte stability when all PDF metadata fields are unchanged."""
    text = textwrap.dedent(
        """\
        ---
        pdf_id: "(Doe 2021)"
        pdf_title: Some Title
        pdf_size: 5000
        pdf_hash: "XYZ789A"
        has_annotations: false
        pdf_mtime: "2025-10-29T10:00:00"
        last_run_at: "2025-10-29T10:05:00"
        ---
        Body
        """
    )

    # Submit same values
    updates = {
        "pdf_id": "(Doe 2021)",
        "pdf_title": "Some Title",
        "pdf_size": 5000,
        "pdf_hash": "XYZ789A",
        "has_annotations": False,
        "pdf_mtime": "2025-10-29T10:00:00",
        "last_run_at": "2025-10-29T10:05:00",
    }

    changed, new_text = upsert_fields(text, updates)
    assert changed is False
    assert new_text == text


def test_as_timestamp_passes_datetime_through():
    """A datetime survives unchanged -- this is the shape Obsidian leaves behind."""
    value = datetime(2025, 10, 21, 21, 20, 40)
    assert as_timestamp(value) is value


def test_as_timestamp_parses_iso_string():
    """A quoted ISO string -- the shape sync writes -- parses to the equal datetime."""
    expected = datetime(2025, 10, 21, 21, 20, 40)
    assert as_timestamp("2025-10-21T21:20:40") == expected
    # A space separator is what str(datetime) produces; fromisoformat accepts it too
    assert as_timestamp("2025-10-21 21:20:40") == expected


def test_as_timestamp_rejects_unparseable_strings():
    """Garbage is not comparable, and the caller must treat None as changed."""
    assert as_timestamp("not a timestamp") is None
    assert as_timestamp("") is None
    assert as_timestamp("2025-13-45") is None


def test_as_timestamp_rejects_non_timestamp_types():
    """Anything that is neither a datetime nor an ISO string is not comparable.

    The bare date is the interesting one: YAML resolves `2025-10-21` (no time of
    day) to a date rather than a datetime, and a date has no time to compare
    against a PDF mtime. Not comparable is the honest answer.
    """
    assert as_timestamp(None) is None
    assert as_timestamp(1761074440) is None
    assert as_timestamp(date(2025, 10, 21)) is None
    assert as_timestamp(["2025-10-21T21:20:40"]) is None


def test_as_timestamp_normalizes_quoted_and_unquoted_frontmatter():
    """The real-world case: the same instant written both ways compares equal.

    Sync writes the timestamp quoted; Obsidian's property editor rewrites the
    block and drops the quotes, so yaml.safe_load hands back a str for one and a
    datetime for the other. Normalized, they are the same value.
    """
    quoted = textwrap.dedent(
        """\
        ---
        pdf_mtime: '2025-10-21T21:20:40'
        ---
        Body
        """
    )
    unquoted = textwrap.dedent(
        """\
        ---
        pdf_mtime: 2025-10-21T21:20:40
        ---
        Body
        """
    )

    quoted_value = parse_note(quoted).front_matter["pdf_mtime"]
    unquoted_value = parse_note(unquoted).front_matter["pdf_mtime"]

    # Precondition: YAML really does hand back two different types here
    assert isinstance(quoted_value, str)
    assert isinstance(unquoted_value, datetime)

    # ... which is exactly why the raw comparison was unequal forever
    assert quoted_value != unquoted_value
    assert as_timestamp(quoted_value) == as_timestamp(unquoted_value)

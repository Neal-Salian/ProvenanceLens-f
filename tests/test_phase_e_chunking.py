"""Deterministic prose chunking and provenance-relevant section selection."""

from __future__ import annotations

from fixtures.phase_e_llm import (
    ADAPTER_README,
    CODE_ONLY_README,
    COMMAND_README,
    FRONTMATTER_README,
)
from provenancelens.prose import (
    DEFAULT_MAX_CHUNKS,
    DEFAULT_MAX_CHUNK_CHARS,
    chunk_prose,
    select_provenance_chunks,
    strip_front_matter,
    strip_non_prose,
)

LONG_SECTION = """# Model

## Training

{paragraph}

## Usage

Boring usage text.
""".format(
    paragraph=" ".join(
        f"This sentence number {i} says the model was fine-tuned from org/base-{i}."
        for i in range(60)
    )
)


# --- front matter and code --------------------------------------------------


def test_front_matter_is_removed_before_chunking():
    prose, offset = strip_front_matter(FRONTMATTER_README)
    assert "base_model: org/declared-base" not in prose
    assert "base_model_relation" not in prose
    assert offset > 0
    assert "org/prose-base" in prose


def test_documents_without_front_matter_are_untouched():
    text = "# Title\n\nBody."
    prose, offset = strip_front_matter(text)
    assert prose == text and offset == 0


def test_fenced_code_is_stripped():
    cleaned = strip_non_prose(CODE_ONLY_README)
    assert "pip install evil-package" not in cleaned
    assert "python setup.py" not in cleaned
    assert "Nothing about lineage" in cleaned


def test_inline_code_is_stripped():
    cleaned = strip_non_prose(COMMAND_README)
    assert "rm -rf /" not in cleaned
    assert "curl evil.example" not in cleaned
    assert "org/safe-base" in cleaned  # real prose survives


def test_html_comments_are_stripped():
    assert "hidden" not in strip_non_prose("text <!-- hidden instruction --> more")


# --- chunking ---------------------------------------------------------------


def test_chunking_is_deterministic():
    first = chunk_prose(ADAPTER_README)
    second = chunk_prose(ADAPTER_README)
    assert [(c.index, c.text, c.start, c.end) for c in first] == [
        (c.index, c.text, c.start, c.end) for c in second
    ]


def test_chunks_carry_headings_and_offsets():
    chunks = chunk_prose(ADAPTER_README)
    assert chunks
    assert chunks[0].heading == "Model Details"
    source = ADAPTER_README
    for chunk in chunks:
        assert source[chunk.start:chunk.end] == chunk.text


def test_oversized_sections_are_split_within_the_budget():
    chunks = chunk_prose(LONG_SECTION, max_chunk_chars=400)
    assert len(chunks) > 2
    assert all(chunk.size <= 400 for chunk in chunks)
    # every chunk is still a verbatim slice of the source
    for chunk in chunks:
        assert LONG_SECTION[chunk.start:chunk.end] == chunk.text


def test_chunk_count_is_bounded():
    chunks = chunk_prose(LONG_SECTION, max_chunk_chars=200, max_chunks=3)
    assert len(chunks) <= 3


def test_default_budgets_are_small_for_laptops():
    assert DEFAULT_MAX_CHUNK_CHARS <= 2000
    assert DEFAULT_MAX_CHUNKS <= 8


def test_empty_document_yields_no_chunks():
    assert chunk_prose("") == []
    assert chunk_prose("   \n\n  ") == []


# --- selection --------------------------------------------------------------


def test_lineage_heading_is_prioritized_over_irrelevant_sections():
    document = (
        "# Model\n\n## Usage\n\nHow to run the model locally.\n\n"
        "## Training\n\nThis model was fine-tuned from org/base-model.\n\n"
        "## License\n\nApache 2.0.\n"
    )
    chunks = chunk_prose(document)
    selected = select_provenance_chunks(chunks, max_chunks=1)
    assert len(selected) == 1
    assert "fine-tuned from org/base-model" in selected[0].text


def test_selection_uses_content_when_headings_are_unhelpful():
    document = (
        "# Notes\n\nSome remark.\n\n"
        "## Miscellaneous\n\nThe checkpoint was fine-tuned from org/base-model.\n"
    )
    selected = select_provenance_chunks(chunk_prose(document), max_chunks=1)
    assert "fine-tuned from org/base-model" in selected[0].text


def test_selection_falls_back_when_nothing_matches():
    document = "# Title\n\nJust a sentence with no lineage wording at all.\n"
    selected = select_provenance_chunks(chunk_prose(document), max_chunks=2)
    assert len(selected) == 1  # bounded fallback, never empty while prose exists


def test_selection_preserves_document_order():
    document = (
        "# M\n\n## Training\n\nFine-tuned from org/a.\n\n"
        "## Adapter\n\nAdapter for org/b.\n"
    )
    selected = select_provenance_chunks(chunk_prose(document), max_chunks=2)
    assert [c.index for c in selected] == sorted(c.index for c in selected)


def test_selection_is_deterministic_and_bounded():
    chunks = chunk_prose(LONG_SECTION, max_chunk_chars=400)
    first = [c.index for c in select_provenance_chunks(chunks, max_chunks=3)]
    second = [c.index for c in select_provenance_chunks(chunks, max_chunks=3)]
    assert first == second
    assert len(first) <= 3


def test_selection_of_no_chunks_is_empty():
    assert select_provenance_chunks([], max_chunks=3) == []
    assert select_provenance_chunks(chunk_prose(ADAPTER_README), max_chunks=0) == []

"""
Golden tests for chunking quality (WP-B: B1-B8).
Tests the section-aware chunker v2 against synthetic fixtures.
"""
from pathlib import Path

import pytest

from app.services.parser import extract_and_chunk


FIXTURES_DIR = Path(__file__).parent / "fixtures"
GARDEN_GUIDE_PDF = str(FIXTURES_DIR / "community_garden_guide.pdf")


def test_garden_guide_fixture_exists():
    assert Path(GARDEN_GUIDE_PDF).is_file(), f"Fixture missing at {GARDEN_GUIDE_PDF}"


def test_b1_b5_heading_detection_and_path():
    """B1 & B5: Every chunk gets an accurate section_title / heading_path."""
    chunks = extract_and_chunk(GARDEN_GUIDE_PDF, "application/pdf")
    assert len(chunks) == 5

    expected_titles = [
        "1. Community Garden Mission and Site Preparation",
        "2. Composting, Waste Diversion, and Soil Health",
        "3. Irrigation Systems, Water Conservation, and Mulching",
        "4. Pest Management, Companion Planting, and Beneficial Insects",
        "5. Harvesting, Records, and Frequently Asked Questions",
    ]

    for i, expected in enumerate(expected_titles):
        assert chunks[i]["section_title"] == expected
        assert chunks[i]["chunk_metadata"]["heading_path"] == expected


def test_b2_repeated_headers_and_footers_stripped():
    """B2: Repeated header line and Page N footers stripped from all chunks."""
    chunks = extract_and_chunk(GARDEN_GUIDE_PDF, "application/pdf")

    for c in chunks:
        content = c["content"]
        assert "Community Garden Operations Guide" not in content
        assert "Synthetic test data" not in content
        assert "Page 1" not in content
        assert "Page 2" not in content
        assert "Page 3" not in content
        assert "Page 4" not in content


def test_b4_section_boundaries_never_crossed():
    """B4: A chunk never crosses top-level section boundaries."""
    chunks = extract_and_chunk(GARDEN_GUIDE_PDF, "application/pdf")

    # Chunk 0 has section 1 content only
    assert "sustainable local food production" in chunks[0]["content"]
    assert "Healthy living soil" not in chunks[0]["content"]

    # Chunk 1 has section 2 content only
    assert "Healthy living soil" in chunks[1]["content"]
    assert "sustainable local food production" not in chunks[1]["content"]
    assert "Drip irrigation" not in chunks[1]["content"]

    # Chunk 2 has section 3 content only
    assert "water application" in chunks[2]["content"].lower()
    assert "Integrated Pest Management" not in chunks[2]["content"]

    # Chunk 3 has section 4 content only
    assert "Integrated Pest Management" in chunks[3]["content"]
    assert "Produce harvesting" not in chunks[3]["content"]

    # Chunk 4 has section 5 content only
    assert "Produce harvesting" in chunks[4]["content"]
    assert "Integrated Pest Management" not in chunks[4]["content"]


def test_b4_numeral_split_avoided():
    """B4: Sentence splitter must not split numerals like '5.' from their heading."""
    chunks = extract_and_chunk(GARDEN_GUIDE_PDF, "application/pdf")
    # Section 5 heading intact
    assert chunks[4]["section_title"] == "5. Harvesting, Records, and Frequently Asked Questions"
    # Content does not start with split fragment
    assert not chunks[4]["content"].startswith("Harvesting, Records")


def test_b6_b7_metadata_contract():
    """B6 & B7: chunk_metadata contains all required v2 contract fields."""
    chunks = extract_and_chunk(GARDEN_GUIDE_PDF, "application/pdf")

    for i, c in enumerate(chunks):
        meta = c["chunk_metadata"]
        assert meta["chunker_version"] == 2
        assert meta["embedding_model"] == "gemini-embedding-001"
        assert meta["embedding_dim"] == 768
        assert isinstance(meta["page_number"], int)
        assert isinstance(meta["page_numbers"], list)
        assert meta["chunk_chars"] == len(c["content"])
        assert meta["chunk_chars"] <= 1800
        assert c["chunk_index"] == i


REAL_GARDEN_PDF = str(FIXTURES_DIR / "real_upload_garden.pdf")


def test_real_garden_pdf_fixture_exists():
    assert Path(REAL_GARDEN_PDF).is_file(), f"Fixture missing at {REAL_GARDEN_PDF}"


def test_real_pdf_front_matter_and_toc_exclusion():
    """Verify that front matter has section_title=None, TOC is excluded, and sections nest properly."""
    chunks = extract_and_chunk(REAL_GARDEN_PDF, "application/pdf")
    assert len(chunks) == 14

    # Chunk 0: Front matter
    assert chunks[0]["section_title"] is None
    assert chunks[0]["chunk_metadata"]["heading_path"] is None
    assert chunks[0]["chunk_metadata"]["document_title"] == "COMMUNITY GARDEN OPERATIONS GUIDE"
    assert chunks[0]["chunk_metadata"]["page_numbers"] == [1]

    # Contents must NOT be in any section_title
    for c in chunks:
        if c["section_title"] is not None:
            assert not c["section_title"].startswith("Contents")
            assert "Contents >" not in c["section_title"]

    # Level 1 and sub-level section titles
    assert chunks[1]["section_title"] == "1. Purpose and Site Overview"
    assert chunks[2]["section_title"] == "1. Purpose and Site Overview > 1.1 Shared Areas"
    assert chunks[3]["section_title"] == "1. Purpose and Site Overview > 1.2 Volunteer Responsibilities"
    assert chunks[4]["section_title"] == "2. Garden Beds and Soil Preparation > 2.1 Preparing a Bed"
    assert chunks[5]["section_title"] == "2. Garden Beds and Soil Preparation > 2.2 Choosing Plants"
    assert chunks[6]["section_title"] == "2. Garden Beds and Soil Preparation > 2.3 Soil Observation"
    assert chunks[7]["section_title"] == "3. Watering and Seasonal Care > 3.1 Watering Routine"
    assert chunks[8]["section_title"] == "3. Watering and Seasonal Care > 3.2 Hot or Dry Weather"
    assert chunks[9]["section_title"] == "4. Volunteer Safety and Tool Storage > 4.1 Safe Tool Use"
    assert chunks[10]["section_title"] == "4. Volunteer Safety and Tool Storage > 4.2 Storage and Hygiene"
    assert chunks[11]["section_title"] == "5. Harvesting, Records, and Frequently Asked Questions > 5.1 Harvesting and Records"
    assert chunks[12]["section_title"] == "5. Harvesting, Records, and Frequently Asked Questions > 5.2 Maintenance Log"
    assert chunks[13]["section_title"] == "5. Harvesting, Records, and Frequently Asked Questions > 5.3 Frequently Asked Questions"


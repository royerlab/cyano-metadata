"""Tests for DaXi v0.1 metadata models."""

import json
from pathlib import Path

from cyano_metadata_specs.daxi.v0_1 import DaxiMetadata

SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "daxi" / "v0_1"


def test_all_v0_1_samples_parse():
    """Ensure all v0.1 sample files parse without error."""
    sample_files = sorted(SAMPLES_DIR.glob("*.json"))
    assert len(sample_files) > 0, "No v0.1 sample files found"

    for sample_file in sample_files:
        with sample_file.open() as f:
            data = json.load(f)

        metadata = DaxiMetadata.model_validate(data)
        assert metadata.version == "0.1"

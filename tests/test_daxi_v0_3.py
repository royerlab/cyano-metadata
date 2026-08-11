"""Tests for DaXi v0.3 metadata models (adds the ``processing`` record)."""

import json

import pytest
from pydantic import ValidationError

from cyano_metadata.daxi.v0_3 import ChannelProcessing, DaxiMetadata, Processing


def test_all_v0_3_samples_parse(daxi_v0_3_samples):
    """Ensure all v0.3 sample files parse without error."""
    sample_files = sorted(daxi_v0_3_samples.glob("*.json"))
    assert len(sample_files) > 0, "No v0.3 sample files found"

    for sample_file in sample_files:
        with sample_file.open() as f:
            data = json.load(f)

        metadata = DaxiMetadata.model_validate(data)
        assert metadata.version == "0.3"


def test_processing_parsed_from_sample(daxi_v0_3_samples):
    """The per-wavelength processing block should round-trip into the typed model."""
    with (daxi_v0_3_samples / "with_processing.json").open() as f:
        data = json.load(f)

    metadata = DaxiMetadata.model_validate(data)
    assert metadata.processing is not None
    proc = metadata.processing.root
    # Label-free (780nm): quantized, not subtracted.
    assert proc["780nm"].subtract is None
    assert proc["780nm"].quantize_step == 4
    # Fluorescence (561nm): subtracted, not quantized.
    assert proc["561nm"].subtract == 100
    assert proc["561nm"].quantize_step is None


def test_processing_absent_on_raw_acquisition():
    """A dataset with no processing key has processing == None (self-identifying: raw)."""
    metadata = DaxiMetadata.model_validate({
        "version": "0.3",
        "microscope_name": "DaXi",
        "framerate_hz": 50,
        "global_exposure_ms": 10.0,
        "positions": {"pos0": [0.0, 0.0]},
        "timing_detail": {},
    })
    assert metadata.processing is None


def test_partial_processing_records():
    """Each per-channel key is independent: subtract and quantize_step stand alone."""
    subtract_only = ChannelProcessing.model_validate({"subtract": 100})
    assert subtract_only.subtract == 100
    assert subtract_only.quantize_step is None

    quant_only = ChannelProcessing.model_validate({"quantize_step": 4})
    assert quant_only.subtract is None
    assert quant_only.quantize_step == 4


def test_processing_rejects_unknown_ops():
    """The per-channel vocabulary is closed: unknown ops must not be silently dropped."""
    with pytest.raises(ValidationError):
        ChannelProcessing.model_validate({"deskew": True})
    # And through the per-wavelength map.
    with pytest.raises(ValidationError):
        Processing.model_validate({"561nm": {"deskew": True}})


def test_v0_3_reads_older_data(daxi_v0_1_samples, daxi_v0_2_samples):
    """v0.3 inherits every v0.1/v0.2 field and reads older datasets unchanged."""
    for samples in (daxi_v0_1_samples, daxi_v0_2_samples):
        for sample_file in sorted(samples.glob("*.json")):
            with sample_file.open() as f:
                data = json.load(f)
            metadata = DaxiMetadata.model_validate(data)
            assert metadata.processing is None

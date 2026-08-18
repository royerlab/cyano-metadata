"""Tests for DaXi v0.3 metadata models (adds the ``processing`` record)."""

import json

import pytest
from pydantic import ValidationError

from cyano_metadata.daxi.v0_3 import ChannelProcessing, DaxiMetadata, Processing
from cyano_metadata.errors import AmbiguousWavelengthError


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


def record(processing, label):
    """Look up one wavelength record, asserting it is present."""
    found = processing.for_label(label)
    assert found is not None
    return found


class TestChannelProcessingSubtracted:
    """`subtracted` exists so consumers never special-case the absent value."""

    def test_null_and_zero_both_mean_nothing_removed(self):
        assert ChannelProcessing().subtracted == 0
        assert ChannelProcessing(subtract=0).subtracted == 0

    def test_reports_the_recorded_floor(self):
        assert ChannelProcessing(subtract=100).subtracted == 100

    def test_negative_subtract_is_rejected(self):
        """A negative pedestal would invert the sign of any compensation."""
        with pytest.raises(ValidationError):
            ChannelProcessing(subtract=-5)


class TestProcessingLookup:
    """Wavelength keys are opaque strings, matched key-to-key without parsing."""

    def test_labels_are_returned_as_written(self, daxi_v0_3_samples):
        with (daxi_v0_3_samples / "with_processing.json").open() as f:
            metadata = DaxiMetadata.model_validate(json.load(f))
        assert metadata.processing is not None
        assert metadata.processing.labels() == {"780nm", "488nm", "561nm"}

    def test_exact_match(self):
        processing = Processing.model_validate({"488nm": {"subtract": 100}})
        assert record(processing, "488nm").subtracted == 100

    @pytest.mark.parametrize("label", ["488 nm", "488NM", " 488nm "])
    def test_case_and_whitespace_are_tolerated(self, label):
        processing = Processing.model_validate({"488nm": {"subtract": 100}})
        assert record(processing, label).subtracted == 100

    def test_absent_label_returns_none(self):
        processing = Processing.model_validate({"488nm": {"subtract": 100}})
        assert processing.for_label("561nm") is None

    def test_non_numeric_labels_resolve_normally(self):
        """Guards against reintroducing digit parsing: a white-light or
        supercontinuum channel has no wavelength number to extract.
        """
        processing = Processing.model_validate({
            "white": {"subtract": 100},
            "supercontinuum": {"quantize_step": 4},
        })
        assert record(processing, "white").subtracted == 100
        assert record(processing, "supercontinuum").quantize_step == 4

    def test_exact_match_wins_over_a_loose_one(self):
        processing = Processing.model_validate({
            "488nm": {"subtract": 100},
            "488 nm": {"subtract": 50},
        })
        assert record(processing, "488nm").subtracted == 100

    def test_ambiguous_loose_match_raises(self):
        processing = Processing.model_validate({
            "488nm": {"subtract": 100},
            "488 nm": {"subtract": 50},
        })
        with pytest.raises(AmbiguousWavelengthError) as caught:
            processing.for_label("488NM")
        assert caught.value.matches == ["488 nm", "488nm"]

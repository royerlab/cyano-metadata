"""Shared pytest fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def samples_dir():
    """Return the base samples directory."""
    return Path(__file__).parent.parent / "samples"


@pytest.fixture
def daxi_v0_1_samples(samples_dir):
    """Return the daxi v0.1 samples directory."""
    return samples_dir / "daxi" / "v0_1"


@pytest.fixture
def daxi_v0_2_samples(samples_dir):
    """Return the daxi v0.2 samples directory."""
    return samples_dir / "daxi" / "v0_2"

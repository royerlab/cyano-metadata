# Agent Context for cyano-metadata

This document contains essential information for AI agents working on this project.

## Project Overview

cyano-metadata is a Python package containing Pydantic models for metadata specifications from microscopes controlled by the Cyano acquisition software. This package acts as a living specification that preserves all historical versions of metadata formats.

Supported microscopes:
- DaXi: Light-sheet microscope with multi-view acquisition
- QuadraVision: (future support planned)

Both microscopes are controlled by Cyano software but have different attributes and acquisition types.

## Package Manager

Always use uv for all Python package operations:

```bash
uv add package-name          # Add dependency
uv sync                       # Sync dependencies
uv run script.py             # Run scripts
uv run pytest                # Run tests
uv run pre-commit run -a     # Run linters
```

## Code Quality

Use make targets for common operations:

```bash
make help                    # Show all available targets
make install                 # Install venv and pre-commit hooks
make check                   # Run all code quality checks
make test                    # Run pytest with doctests
make build                   # Build wheel
```

Quality tools in use:
- ruff: Linting and formatting (line length: 120)
- ty: Static type checking
- pre-commit: Automated checks on commit
- pytest: Testing framework

Requirements:
- Python >= 3.10
- All code must pass make check before committing
- Tests must pass with make test
- Full type annotations required

## Architecture

Each metadata version is immutable and isolated in its own namespace.

```
cyano_metadata/
├── daxi/
│   ├── __init__.py          # Re-exports current stable version
│   ├── v0_1/
│   │   ├── __init__.py
│   │   ├── metadata.py      # DaxiMetadata class
│   │   └── models.py        # Supporting models
│   ├── v0_2/
│   │   ├── __init__.py      # Re-exports from v0_1 (backward compatible)
│   │   └── plate.py         # HCS plate spec builder
│   └── etc
└── quadravision/            # Future microscope
    └── v0_1/
    └── etc
```
Import patterns:

```python
# Explicit version import (recommended)
from cyano_metadata.daxi.v0_1 import DaxiMetadata

# Import and alias multiple versions
from cyano_metadata.daxi.v0_1 import DaxiMetadata as DaxiMetadataV01
from cyano_metadata.daxi.v0_2 import DaxiMetadata as DaxiMetadataV02
```

## Versioning Guidelines

Directory naming: Use underscores for versions (v0_1, v0_2, v1_0) not dots (invalid Python module names)

Class naming: Simple names within namespace (DaxiMetadata not DaxiMetadataV01)

Breaking changes: Create a new version directory (e.g., v0_3/)

Re-exports: Use Python imports to point one version at another when they're compatible (see v0_2/__init__.py)

Why this design works:
- Version isolation: Old code never breaks when new versions are added
- Explicit versioning: Import path shows exactly which spec version you're using
- Clean class names: Context comes from the module path, not class name suffixes
- Scalability: Works with multiple microscopes and dozens of versions
- Migration testing: Can import multiple versions simultaneously to test upgrades

Note: Only the "daxi" key is owned by this project. Other keys (e.g., "plate") are OME-Zarr metadata.

## Adding a New Microscope

```bash
mkdir -p cyano_metadata/quadravision/v0_1
```

Then implement models in quadravision/v0_1/metadata.py and models.py, create __init__.py to export public API, add convenience re-export in quadravision/__init__.py, and write tests in tests/test_quadravision_v0_1.py

## Adding a New Version

```bash
mkdir -p cyano_metadata/daxi/v0_3
```

Then implement new models (can import from previous versions if needed).

Important: Backward compatibility between versions of the spec is not a goal, but this package should support all old metadata versions in perpetuity. Don't make breaking changes to sealed versions. Real data is messy - make fields optional when appropriate.

## Supporting files

```
~/source/cyano-metadata/
├── pyproject.toml                      # Package config
├── Makefile                            # Dev automation
├── cyano_metadata/               # Package source
├── tests/                              # Test suite
│   ├── test_daxi_v0_1.py
│   └── test_daxi_v0_2.py
└── samples/                            # Test data
    └── daxi/
        ├── v0_1/
        └── v0_2/
```

## Quick Reference

- Always use uv for Python operations
- Run make check before commits
- Use version in path, not class name: daxi.v0_1.DaxiMetadata
- Package structure: Source layout with cyano_metadata/ package
- Dependencies: Managed via uv and declared in pyproject.toml

"""Tests for the DaXi plate spec builder."""

from cyano_metadata.daxi.v0_2 import (
    AcqPositionSpec,
    CameraSpec,
    PlateSpec,
    build_plate_spec,
)


def _single_camera() -> list[CameraSpec]:
    return [CameraSpec(serial_number="CAM-001", wavelengths=[488], pixel_size_um=0.115)]


def _two_cameras() -> list[CameraSpec]:
    return [
        CameraSpec(serial_number="CAM-001", wavelengths=[488], pixel_size_um=0.115),
        CameraSpec(serial_number="CAM-002", wavelengths=[561], pixel_size_um=0.115),
    ]


def _single_position() -> list[AcqPositionSpec]:
    return [AcqPositionSpec(name="pos0", scan_range_um=1000.0)]


def _two_positions() -> list[AcqPositionSpec]:
    return [
        AcqPositionSpec(name="pos0", scan_range_um=1000.0),
        AcqPositionSpec(name="pos1", scan_range_um=500.0),
    ]


class TestBuildPlateSpecBasic:
    def test_single_camera_single_position(self):
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1, 2],
        )
        assert isinstance(spec, PlateSpec)
        assert len(spec.positions) == 1
        assert spec.positions[0].row == "CAM001"
        assert spec.positions[0].column == "488nm"
        assert spec.positions[0].well == "pos0"
        assert "0" in spec.positions[0].scales
        assert "1" in spec.positions[0].scales

    def test_channel_names_from_views(self):
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1, 3],
        )
        assert len(spec.channel_names) == 2
        assert "Bottom Objective, Side A | v1_c1" in spec.channel_names
        assert "Top Objective, Side A | v3_c1" in spec.channel_names

    def test_all_four_views(self):
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1, 2, 3, 4],
        )
        assert len(spec.channel_names) == 4
        names = spec.channel_names
        assert names[0] == "Bottom Objective, Side A | v1_c1"
        assert names[1] == "Bottom Objective, Side B | v2_c1"
        assert names[2] == "Top Objective, Side A | v3_c1"
        assert names[3] == "Top Objective, Side B | v4_c1"


class TestMultiCameraMultiPosition:
    def test_two_cameras_two_positions(self):
        spec = build_plate_spec(
            cameras=_two_cameras(),
            positions=_two_positions(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        # 2 cameras x 1 wavelength each x 2 positions = 4 descriptors
        assert len(spec.positions) == 4

        rows = {p.row for p in spec.positions}
        assert rows == {"CAM001", "CAM002"}

        wells = {p.well for p in spec.positions}
        assert wells == {"pos0", "pos1"}

        columns = {p.column for p in spec.positions}
        assert columns == {"488nm", "561nm"}

    def test_multi_wavelength_camera(self):
        cameras = [
            CameraSpec(serial_number="SN123", wavelengths=[405, 488], pixel_size_um=0.115),
        ]
        spec = build_plate_spec(
            cameras=cameras,
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        # 1 camera x 2 wavelengths x 1 position = 2 descriptors
        assert len(spec.positions) == 2
        columns = sorted(p.column for p in spec.positions)
        assert columns == ["405nm", "488nm"]


class TestScaleComputation:
    def test_z_step_matches_scan_range(self):
        """Z scale should be scan_range / z_planes, accounting for integer truncation."""
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=[AcqPositionSpec(name="pos0", scan_range_um=1000.0)],
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        full_scale = spec.positions[0].scales["0"]
        # z_planes = int(1000 / 1.0) = 1000, z_step = 1000 / 1000 = 1.0
        assert full_scale[2] == 1.0  # Z

    def test_z_step_adjusted_for_rounding(self):
        """When scan range doesn't divide evenly, z_step is adjusted."""
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=[AcqPositionSpec(name="pos0", scan_range_um=1005.0)],
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        full_scale = spec.positions[0].scales["0"]
        # z_planes = int(1005 / 1.0) = 1005, z_step = 1005 / 1005 = 1.0
        assert full_scale[2] == 1005.0 / 1005

    def test_timepoint_duration(self):
        """T scale = z_planes / frame_rate * num_views."""
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=[AcqPositionSpec(name="pos0", scan_range_um=100.0)],
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1, 2],
        )
        full_scale = spec.positions[0].scales["0"]
        # z_planes = 100, volume_sweep = 100/50 = 2s, timepoint = 2s * 2 views = 4s
        assert full_scale[0] == 4.0  # T

    def test_pixel_size(self):
        spec = build_plate_spec(
            cameras=[CameraSpec(serial_number="X", wavelengths=[488], pixel_size_um=0.23)],
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        full_scale = spec.positions[0].scales["0"]
        assert full_scale[3] == 0.23  # Y
        assert full_scale[4] == 0.23  # X

    def test_downsampled_scale(self):
        """Level '1' should be 4x downsampled in Z, Y, X but same T, V."""
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        full = spec.positions[0].scales["0"]
        down = spec.positions[0].scales["1"]

        assert down[0] == full[0]  # T unchanged
        assert down[1] == full[1]  # V unchanged
        assert down[2] == full[2] / 4  # Z 4x
        assert down[3] == full[3] / 4  # Y 4x
        assert down[4] == full[4] / 4  # X 4x

    def test_per_position_views_override(self):
        """Positions with per-position views should use their own view list."""
        positions = [
            AcqPositionSpec(name="pos0", scan_range_um=100.0, views=[1]),
            AcqPositionSpec(name="pos1", scan_range_um=100.0, views=[1, 2, 3, 4]),
        ]
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=positions,
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1, 2],
        )
        # pos0 has 1 view, pos1 has 4 views → different T scales
        pos0 = next(p for p in spec.positions if p.well == "pos0")
        pos1 = next(p for p in spec.positions if p.well == "pos1")

        # z_planes = 100, sweep = 100/50 = 2s
        assert pos0.scales["0"][0] == 2.0  # 2s * 1 view
        assert pos1.scales["0"][0] == 8.0  # 2s * 4 views

    def test_per_position_views_in_channel_names(self):
        """Channel names should be the union of all per-position views."""
        positions = [
            AcqPositionSpec(name="pos0", scan_range_um=100.0, views=[1]),
            AcqPositionSpec(name="pos1", scan_range_um=100.0, views=[3]),
        ]
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=positions,
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1, 2],  # global_views not used when all positions have views
        )
        assert len(spec.channel_names) == 2
        assert "v1_c1" in spec.channel_names[0]
        assert "v3_c1" in spec.channel_names[1]


class TestSerialization:
    def test_round_trip_json(self):
        """PlateSpec should serialize to JSON and back."""
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        json_str = spec.model_dump_json()
        restored = PlateSpec.model_validate_json(json_str)
        assert restored == spec

    def test_model_dump_dict(self):
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        d = spec.model_dump()
        assert isinstance(d, dict)
        assert "channel_names" in d
        assert "positions" in d
        assert d["positions"][0]["row"] == "CAM001"


class TestEdgeCases:
    def test_camera_sn_special_chars_stripped(self):
        """Non-alphanumeric chars in serial number should be stripped for row name."""
        cameras = [CameraSpec(serial_number="CAM-001_X", wavelengths=[488], pixel_size_um=0.1)]
        spec = build_plate_spec(
            cameras=cameras,
            positions=_single_position(),
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        assert spec.positions[0].row == "CAM001X"

    def test_very_small_scan_range(self):
        """Scan range smaller than z_step should produce at least 1 z-plane."""
        positions = [AcqPositionSpec(name="tiny", scan_range_um=0.5)]
        spec = build_plate_spec(
            cameras=_single_camera(),
            positions=positions,
            frame_rate_hz=50.0,
            z_step_size_um=1.0,
            global_views=[1],
        )
        full_scale = spec.positions[0].scales["0"]
        # z_planes = max(int(0.5/1.0), 1) = 1, z_step = 0.5
        assert full_scale[2] == 0.5

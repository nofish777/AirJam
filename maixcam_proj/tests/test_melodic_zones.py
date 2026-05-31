from face_tracking.melodic_zones import MelodicZoneController


def test_piano_zones_map_horizontal_position_to_c_major_notes():
    controller = MelodicZoneController(0, 0, 280, 200, [60, 62, 64, 65, 67, 69, 71])

    assert controller.update((10, 100), now_ms=0) == 60
    assert controller.update((10, 100), now_ms=20) is None
    assert controller.update((90, 100), now_ms=140) == 64


def test_guitar_zones_can_use_six_strings():
    controller = MelodicZoneController(0, 0, 300, 200, [40, 45, 50, 55, 59, 64])

    assert controller.update((10, 100), now_ms=0) == 40
    assert controller.update((260, 100), now_ms=140) == 64
    assert controller.update((260, 220), now_ms=300) is None

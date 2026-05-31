from face_tracking.instrument_select import (
    InstrumentReturnController,
    InstrumentSelectionController,
    InstrumentSelectionEvent,
    InstrumentZone,
    default_instrument_zones,
    instrument_at,
    is_fist,
)


def _open_hand():
    return [
        (0, 100, 0),
        (-30, 90, 0), (-45, 75, 0), (-58, 60, 0), (-70, 45, 0),
        (-20, 75, 0), (-25, 50, 0), (-27, 25, 0), (-28, 0, 0),
        (0, 72, 0), (0, 45, 0), (0, 20, 0), (0, -5, 0),
        (20, 75, 0), (24, 50, 0), (26, 25, 0), (28, 0, 0),
        (40, 82, 0), (47, 60, 0), (53, 38, 0), (60, 15, 0),
    ]


def _fist():
    points = _open_hand()
    folded = list(points)
    for mcp, pip, dip, tip in [(5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16), (17, 18, 19, 20)]:
        x, y, z = folded[mcp]
        folded[pip] = (x + 2, y + 12, z)
        folded[dip] = (x + 3, y + 20, z)
        folded[tip] = (x + 4, y + 30, z)
    return folded


def _fold_finger(points, mcp, pip, dip, tip):
    updated = list(points)
    base_x, base_y, _ = updated[mcp]
    updated[pip] = (base_x + 4, base_y + 16, 0)
    updated[dip] = (base_x + 8, base_y + 24, 0)
    updated[tip] = (base_x + 12, base_y + 30, 0)
    return updated


def _fold_thumb(points):
    updated = list(points)
    updated[1] = (-16, 95, 0)
    updated[2] = (-10, 96, 0)
    updated[3] = (-6, 98, 0)
    updated[4] = (-2, 100, 0)
    return updated


def _number_hand(number):
    if number == 1:
        keep_open = {"index"}
    elif number == 2:
        keep_open = {"index", "middle"}
    elif number == 3:
        keep_open = {"index", "middle", "ring"}
    elif number == 4:
        keep_open = {"index", "middle", "ring", "pinky"}
    elif number == 5:
        keep_open = {"thumb", "index", "middle", "ring", "pinky"}
    else:
        raise ValueError(number)

    updated = _open_hand()
    if "thumb" not in keep_open:
        updated = _fold_thumb(updated)
    if "index" not in keep_open:
        updated = _fold_finger(updated, 5, 6, 7, 8)
    if "middle" not in keep_open:
        updated = _fold_finger(updated, 9, 10, 11, 12)
    if "ring" not in keep_open:
        updated = _fold_finger(updated, 13, 14, 15, 16)
    if "pinky" not in keep_open:
        updated = _fold_finger(updated, 17, 18, 19, 20)
    return updated


def _slanted_index_hand(tip_dx):
    updated = _number_hand(1)
    base_x, base_y, z = updated[5]
    updated[6] = (base_x + tip_dx // 3, base_y - 20, z)
    updated[7] = (base_x + tip_dx * 2 // 3, base_y - 40, z)
    updated[8] = (base_x + tip_dx, base_y - 60, z)
    return updated


def _translated(points, dx, dy):
    return [(x + dx, y + dy, z) for x, y, z in points]


def test_default_instrument_zones_split_screen_into_four_columns():
    zones = default_instrument_zones(400, 240)

    assert zones == [
        InstrumentZone("drums", 0, 0, 100, 240),
        InstrumentZone("electric_guitar", 100, 0, 100, 240),
        InstrumentZone("acoustic_guitar", 200, 0, 100, 240),
        InstrumentZone("piano", 300, 0, 100, 240),
    ]


def test_instrument_at_returns_zone_by_point():
    zones = default_instrument_zones(400, 240)

    assert instrument_at(50, 120, zones).name == "drums"
    assert instrument_at(150, 120, zones).name == "electric_guitar"
    assert instrument_at(250, 120, zones).name == "acoustic_guitar"
    assert instrument_at(350, 120, zones).name == "piano"


def test_fist_recognizer_accepts_folded_four_fingers_only():
    assert is_fist(_fist()) is True
    assert is_fist(_open_hand()) is False


def test_selection_controller_selects_zone_only_when_matching_number_is_seen():
    zones = default_instrument_zones(400, 240)
    controller = InstrumentSelectionController(zones)

    moving = controller.update(_translated(_open_hand(), 150, 20), now_ms=0)
    wrong_number = controller.update(_translated(_number_hand(1), 150, 20), now_ms=50)
    selected = controller.update(_translated(_number_hand(2), 150, 20), now_ms=80)
    repeated = controller.update(_translated(_number_hand(2), 150, 20), now_ms=100)

    assert moving is None
    assert wrong_number is None
    assert selected == InstrumentSelectionEvent("electric_guitar", 158, 100)
    assert repeated is None
    assert controller.selected_instrument == "electric_guitar"


def test_return_controller_detects_crossed_index_fingers():
    controller = InstrumentReturnController()

    returned = controller.update(
        [
            (0, _translated(_slanted_index_hand(45), 150, 40)),
            (1, _translated(_slanted_index_hand(-45), 195, 40)),
        ],
        now_ms=0,
    )

    assert returned is True


def test_return_controller_requires_both_hands_to_show_index_number_one():
    controller = InstrumentReturnController()

    returned = controller.update(
        [
            (0, _translated(_slanted_index_hand(45), 150, 40)),
            (1, _translated(_number_hand(5), 195, 40)),
        ],
        now_ms=0,
    )

    assert returned is False


def test_return_controller_rejects_parallel_index_fingers():
    controller = InstrumentReturnController()

    returned = controller.update(
        [
            (0, _translated(_slanted_index_hand(45), 150, 40)),
            (1, _translated(_slanted_index_hand(45), 220, 40)),
        ],
        now_ms=0,
    )

    assert returned is False

from face_tracking.guitar import (
    ACOUSTIC_GUITAR_CHORDS,
    ELECTRIC_GUITAR_CHORDS,
    GuitarModeController,
    GuitarStrumEvent,
    chord_for_number,
)


def _hand(center_y):
    return [(0, center_y, 0)] * 21


def test_chord_numbers_map_to_common_power_chords():
    assert [chord.name for chord in ELECTRIC_GUITAR_CHORDS] == ["C5", "D5", "E5", "F5", "G5", "A5", "Bb5", "B5"]
    assert chord_for_number(1).notes == [48, 55, 60]
    assert chord_for_number(8).name == "B5"


def test_acoustic_chord_numbers_map_to_common_open_chords():
    assert [chord.name for chord in ACOUSTIC_GUITAR_CHORDS] == ["C", "G", "Am", "F", "D", "Em", "A", "E"]
    assert chord_for_number(1, ACOUSTIC_GUITAR_CHORDS).notes == [48, 52, 55, 60, 64]
    assert chord_for_number(8, ACOUSTIC_GUITAR_CHORDS).name == "E"


def test_guitar_controller_selects_chord_from_left_hand_number():
    controller = GuitarModeController()

    assert controller.update_left(3) == "E5"
    assert controller.selected_chord.name == "E5"
    assert controller.update_left(None) is None


def test_acoustic_guitar_controller_uses_acoustic_chord_set():
    controller = GuitarModeController(chords=ACOUSTIC_GUITAR_CHORDS, strum_threshold=600)

    assert controller.update_left(2) == "G"
    controller.update_right(_hand(80), now_ms=0)
    down = controller.update_right(_hand(120), now_ms=40)

    assert down == GuitarStrumEvent("G", "down", [43, 47, 50, 55, 59, 67])


def test_guitar_controller_triggers_down_and_up_strums_from_right_hand_motion():
    controller = GuitarModeController(strum_threshold=600, cooldown_ms=80)
    controller.update_left(1)

    first = controller.update_right(_hand(80), now_ms=0)
    down = controller.update_right(_hand(120), now_ms=40)
    repeated = controller.update_right(_hand(160), now_ms=60)
    controller.update_right(_hand(160), now_ms=160)
    up = controller.update_right(_hand(120), now_ms=200)

    assert first is None
    assert down == GuitarStrumEvent("C5", "down", [48, 55, 60])
    assert repeated is None
    assert up == GuitarStrumEvent("C5", "up", [60, 55, 48])


def test_guitar_controller_does_not_strum_without_selected_chord():
    controller = GuitarModeController(strum_threshold=600)

    controller.update_right(_hand(80), now_ms=0)

    assert controller.update_right(_hand(130), now_ms=40) is None

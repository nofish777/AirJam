from face_tracking.piano import (
    MAJOR_DEGREES,
    MINOR_DEGREES,
    PianoModeController,
    create_touch_piano_layout,
)


def _hand(index_x, index_y):
    points = [(0, 0, 0)] * 21
    points[8] = (index_x, index_y, 0)
    return points


def test_touch_piano_layout_has_real_piano_white_and_black_keys():
    layout = create_touch_piano_layout(350, 200, octave=3)

    assert [key.degree for key in layout.white_keys] == MAJOR_DEGREES
    assert [key.degree for key in layout.black_keys] == MINOR_DEGREES
    assert [key.midi for key in layout.white_keys] == [48, 50, 52, 53, 55, 57, 59]
    assert [key.midi for key in layout.black_keys] == [49, 51, 54, 56, 58]


def test_black_keys_take_priority_over_white_keys():
    layout = create_touch_piano_layout(350, 200, octave=3)
    black = layout.black_keys[0]

    assert layout.key_at(black.x + 1, black.y + 1).midi == black.midi


def test_left_hand_numbers_select_five_octaves_from_low_to_high():
    controller = PianoModeController(350, 200)

    assert controller.update_left(1) == 1
    assert controller.selected_octave == 1
    assert [key.midi for key in controller.layout.white_keys] == [36, 38, 40, 41, 43, 45, 47]
    assert controller.update_left(5) == 5
    assert [key.midi for key in controller.layout.white_keys] == [84, 86, 88, 89, 91, 93, 95]
    assert controller.update_left(6) is None


def test_right_index_touch_triggers_selected_octave_key():
    controller = PianoModeController(350, 200, cooldown_ms=80)
    controller.update_left(3)

    first = controller.update_right(_hand(25, 160), now_ms=0)
    repeated = controller.update_right(_hand(25, 160), now_ms=20)
    after_cooldown = controller.update_right(_hand(25, 160), now_ms=120)

    assert first == 60
    assert repeated is None
    assert after_cooldown == 60

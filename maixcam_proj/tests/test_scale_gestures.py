from face_tracking.scale_gestures import (
    GestureScalePlayer,
    NumericGestureRecognizer,
    ScaleNote,
    is_right_hand,
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


def _fold_all_except(points, names):
    updated = points
    if "thumb" not in names:
        updated = _fold_thumb(updated)
    if "index" not in names:
        updated = _fold_finger(updated, 5, 6, 7, 8)
    if "middle" not in names:
        updated = _fold_finger(updated, 9, 10, 11, 12)
    if "ring" not in names:
        updated = _fold_finger(updated, 13, 14, 15, 16)
    if "pinky" not in names:
        updated = _fold_finger(updated, 17, 18, 19, 20)
    return updated


def test_recognizes_right_hand_number_1_to_5_from_extended_fingers():
    recognizer = NumericGestureRecognizer()

    assert recognizer.classify(_fold_all_except(_open_hand(), {"index"})) == 1
    assert recognizer.classify(_fold_all_except(_open_hand(), {"index", "middle"})) == 2
    assert recognizer.classify(_fold_all_except(_open_hand(), {"index", "middle", "ring"})) == 3
    assert recognizer.classify(_fold_all_except(_open_hand(), {"index", "middle", "ring", "pinky"})) == 4
    assert recognizer.classify(_open_hand()) == 5


def test_recognizes_chinese_number_6_and_7_shapes():
    recognizer = NumericGestureRecognizer()

    six = _fold_all_except(_open_hand(), {"thumb", "pinky"})
    seven = _fold_all_except(_open_hand(), {"thumb", "index", "middle"})

    assert recognizer.classify(six) == 6
    assert recognizer.classify(seven) == 7


def test_recognizes_chinese_number_8_shape():
    recognizer = NumericGestureRecognizer()

    eight = _fold_all_except(_open_hand(), {"thumb", "index"})

    assert recognizer.classify(eight) == 8


def test_scale_player_maps_numbers_to_one_octave_and_debounces_repeated_frames():
    player = GestureScalePlayer()

    first = player.update(1)
    repeated = player.update(1)
    changed = player.update(2)
    released = player.update(None)
    after_release = player.update(1)

    assert first == ScaleNote(1, 60, "C4")
    assert repeated is None
    assert changed == ScaleNote(2, 62, "D4")
    assert released is None
    assert after_release == ScaleNote(1, 60, "C4")


def test_right_hand_detection_prefers_labels_and_falls_back_to_class_id():
    class Obj:
        def __init__(self, class_id):
            self.class_id = class_id

    assert is_right_hand(Obj(1), labels=["left", "right"]) is True
    assert is_right_hand(Obj(0), labels=["left", "right"]) is False
    assert is_right_hand(Obj(1), labels=None) is True


def test_right_hand_detection_can_mirror_handedness_for_mirrored_camera_frames():
    class Obj:
        def __init__(self, class_id):
            self.class_id = class_id

    assert is_right_hand(Obj(1), labels=["left", "right"], mirrored=True) is False
    assert is_right_hand(Obj(0), labels=["left", "right"], mirrored=True) is True
    assert is_right_hand(Obj(1), labels=None, mirrored=True) is False

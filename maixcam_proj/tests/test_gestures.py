from face_tracking.gestures import GestureRecognizer, hand_covers_face


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


def test_classifies_ok_when_thumb_and_index_tips_touch():
    points = _open_hand()
    points[4] = (-30, 3, 0)
    points[8] = (-28, 0, 0)

    assert GestureRecognizer().classify(points) == "ok"


def test_classifies_index_down_when_only_index_points_down():
    points = _open_hand()
    points[5] = (0, 70, 0)
    points[6] = (0, 105, 0)
    points[7] = (0, 140, 0)
    points[8] = (0, 175, 0)
    points = _fold_finger(points, 9, 10, 11, 12)
    points = _fold_finger(points, 13, 14, 15, 16)
    points = _fold_finger(points, 17, 18, 19, 20)

    assert GestureRecognizer().classify(points) == "index_down"


def test_returns_none_for_open_hand():
    assert GestureRecognizer().classify(_open_hand()) is None


def test_detects_hand_covering_face_box():
    face_box = (80, 40, 80, 80)
    hand = [(100, 60, 0)] * 21

    assert hand_covers_face(hand, face_box) is True


def test_hand_covering_face_rejects_hands_outside_face_box():
    face_box = (80, 40, 80, 80)
    hand = [(10, 200, 0)] * 21

    assert hand_covers_face(hand, face_box) is False

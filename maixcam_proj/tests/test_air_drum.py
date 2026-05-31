from face_tracking.air_drum import (
    DrumHit,
    SnareDrumController,
    hand_center,
    stroke_level,
)


def _hand(center_x=120, center_y=100):
    pts = [(center_x, center_y, 0)] * 21
    pts[0] = (center_x, center_y + 20, 0)
    pts[5] = (center_x - 20, center_y, 0)
    pts[9] = (center_x, center_y, 0)
    pts[13] = (center_x + 20, center_y, 0)
    pts[17] = (center_x + 40, center_y, 0)
    return pts


def test_hand_center_uses_palm_landmarks():
    assert hand_center(_hand(120, 100)) == (128, 104)


def test_stroke_level_maps_downstroke_speed_to_snare_articulations():
    assert stroke_level(350) == "ghost"
    assert stroke_level(600) == "normal"
    assert stroke_level(850) == "accent"


def test_snare_controller_triggers_ghost_normal_and_accent_hits():
    controller = SnareDrumController(cooldown_ms=20)

    controller.update(_hand(100, 100), now_ms=0, hand_id=0)
    ghost = controller.update(_hand(100, 114), now_ms=30, hand_id=0)

    controller.update(_hand(120, 80), now_ms=100, hand_id=0)
    normal = controller.update(_hand(120, 99), now_ms=130, hand_id=0)

    controller.update(_hand(140, 80), now_ms=200, hand_id=0)
    accent = controller.update(_hand(140, 140), now_ms=230, hand_id=0)

    assert ghost == DrumHit("snare", "hit", "ghost", 466, 108, 118)
    assert normal == DrumHit("snare", "hit", "normal", 633, 128, 103)
    assert accent == DrumHit("snare", "hit", "accent", 2000, 148, 144)


def test_snare_controller_tracks_left_and_right_hands_independently():
    controller = SnareDrumController(cooldown_ms=80)

    controller.update(_hand(80, 80), now_ms=0, hand_id=0)
    controller.update(_hand(200, 80), now_ms=0, hand_id=1)

    left = controller.update(_hand(80, 130), now_ms=30, hand_id=0)
    right = controller.update(_hand(200, 130), now_ms=30, hand_id=1)

    assert left.velocity == "accent"
    assert right.velocity == "accent"

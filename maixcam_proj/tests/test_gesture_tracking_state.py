from face_tracking.gestures import (
    GestureName,
    GestureTrackingController,
    TrackingMode,
)


def test_tracks_normally_without_command_gesture():
    controller = GestureTrackingController(ok_pitch_delta=5.5, lowering_pitch_delta=1.25)

    command = controller.update(gesture=None, face_visible=True)

    assert command.should_track is True
    assert command.pitch_delta == 0
    assert command.locked is False
    assert controller.mode is TrackingMode.TRACKING


def test_ok_gesture_locks_after_one_pitch_drop():
    controller = GestureTrackingController(ok_pitch_delta=5.5, lowering_pitch_delta=1.25)

    command = controller.update(gesture=GestureName.OK, face_visible=True)
    later = controller.update(gesture=None, face_visible=True)

    assert command.should_track is False
    assert command.pitch_delta == 5.5
    assert command.locked is True
    assert later.should_track is False
    assert later.pitch_delta == 0
    assert controller.mode is TrackingMode.LOCKED


def test_covering_face_lowers_until_face_disappears_then_locks():
    controller = GestureTrackingController(ok_pitch_delta=5.5, lowering_pitch_delta=1.25)

    first = controller.update(gesture=GestureName.FACE_COVERED, face_visible=True)
    continuing = controller.update(gesture=None, face_visible=True)
    stopped = controller.update(gesture=None, face_visible=False)

    assert first.should_track is False
    assert first.pitch_delta == 1.25
    assert continuing.should_track is False
    assert continuing.pitch_delta == 1.25
    assert stopped.should_track is False
    assert stopped.pitch_delta == 0
    assert stopped.locked is True
    assert controller.mode is TrackingMode.LOCKED


def test_index_down_no_longer_lowers_before_lock():
    controller = GestureTrackingController(ok_pitch_delta=5.5, lowering_pitch_delta=1.25)

    command = controller.update(gesture=GestureName.INDEX_DOWN, face_visible=True)

    assert command.should_track is True
    assert command.pitch_delta == 0
    assert controller.mode is TrackingMode.TRACKING


def test_locked_state_ignores_later_gestures_and_faces():
    controller = GestureTrackingController(ok_pitch_delta=5.5, lowering_pitch_delta=1.25)
    controller.update(gesture=GestureName.OK, face_visible=True)

    command = controller.update(gesture=GestureName.INDEX_DOWN, face_visible=True)

    assert command.should_track is False
    assert command.pitch_delta == 0
    assert command.locked is True
    assert controller.mode is TrackingMode.LOCKED

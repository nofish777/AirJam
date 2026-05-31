from dataclasses import dataclass
from enum import Enum
from math import hypot


class GestureName:
    OK = "ok"
    INDEX_DOWN = "index_down"
    FACE_COVERED = "face_covered"


class TrackingMode(Enum):
    TRACKING = "tracking"
    LOWERING_UNTIL_NO_FACE = "lowering_until_no_face"
    LOCKED = "locked"


@dataclass(frozen=True)
class GestureCommand:
    should_track: bool
    pitch_delta: float = 0
    locked: bool = False


class GestureRecognizer:
    def __init__(self, pinch_ratio=0.42, extended_ratio=0.72):
        self.pinch_ratio = pinch_ratio
        self.extended_ratio = extended_ratio

    def classify(self, points):
        landmarks = _normalize_points(points)
        if len(landmarks) != 21:
            return None
        if self._is_ok(landmarks):
            return GestureName.OK
        if self._is_index_down(landmarks):
            return GestureName.INDEX_DOWN
        return None

    def _is_ok(self, points):
        hand_scale = _distance(points[0], points[9])
        if hand_scale <= 0:
            return False
        pinch = _distance(points[4], points[8]) <= hand_scale * self.pinch_ratio
        return (
            pinch
            and _finger_extended_up(points, 9, 10, 12, self.extended_ratio)
            and _finger_extended_up(points, 13, 14, 16, self.extended_ratio)
            and _finger_extended_up(points, 17, 18, 20, self.extended_ratio)
        )

    def _is_index_down(self, points):
        return (
            _finger_extended_down(points, 5, 6, 8, self.extended_ratio)
            and _finger_folded(points, 9, 10, 12)
            and _finger_folded(points, 13, 14, 16)
            and _finger_folded(points, 17, 18, 20)
        )


class GestureTrackingController:
    def __init__(self, ok_pitch_delta, lowering_pitch_delta):
        self.ok_pitch_delta = ok_pitch_delta
        self.lowering_pitch_delta = lowering_pitch_delta
        self.mode = TrackingMode.TRACKING

    def update(self, gesture, face_visible):
        if self.mode is TrackingMode.LOCKED:
            return GestureCommand(should_track=False, locked=True)

        if self.mode is TrackingMode.LOWERING_UNTIL_NO_FACE:
            if face_visible:
                return GestureCommand(should_track=False, pitch_delta=self.lowering_pitch_delta)
            self.mode = TrackingMode.LOCKED
            return GestureCommand(should_track=False, locked=True)

        if gesture == GestureName.OK:
            self.mode = TrackingMode.LOCKED
            return GestureCommand(
                should_track=False,
                pitch_delta=self.ok_pitch_delta,
                locked=True,
            )

        if gesture == GestureName.FACE_COVERED:
            self.mode = TrackingMode.LOWERING_UNTIL_NO_FACE
            return GestureCommand(should_track=False, pitch_delta=self.lowering_pitch_delta)

        return GestureCommand(should_track=True)


def _normalize_points(points):
    if not points:
        return []
    first = points[0]
    if isinstance(first, (int, float)):
        step = 3 if len(points) >= 63 else 2
        return [
            tuple(points[index:index + step])
            for index in range(0, min(len(points), 21 * step), step)
        ]
    return [tuple(point) for point in points]


def _distance(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def hand_covers_face(points, face_box, min_inside_points=5):
    landmarks = _normalize_points(points)
    if len(landmarks) != 21 or face_box is None:
        return False
    x, y, w, h = face_box
    inside = 0
    for point in landmarks:
        if x <= point[0] <= x + w and y <= point[1] <= y + h:
            inside += 1
    return inside >= min_inside_points


def _finger_extended_up(points, mcp, pip, tip, ratio):
    vertical = points[mcp][1] - points[tip][1]
    length = _distance(points[mcp], points[tip])
    return length > 0 and vertical / length >= ratio and points[tip][1] < points[pip][1]


def _finger_extended_down(points, mcp, pip, tip, ratio):
    vertical = points[tip][1] - points[mcp][1]
    length = _distance(points[mcp], points[tip])
    return length > 0 and vertical / length >= ratio and points[tip][1] > points[pip][1]


def _finger_folded(points, mcp, pip, tip):
    return points[tip][1] > points[pip][1] and points[tip][1] >= points[mcp][1]

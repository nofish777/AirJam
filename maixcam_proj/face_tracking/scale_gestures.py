from dataclasses import dataclass
from math import hypot

from face_tracking.piano import midi_to_name, normalize_landmarks


SCALE_MIDI_BY_NUMBER = {
    1: 60,
    2: 62,
    3: 64,
    4: 65,
    5: 67,
    6: 69,
    7: 71,
}


@dataclass(frozen=True)
class ScaleNote:
    number: int
    midi: int
    name: str


class GestureScalePlayer:
    def __init__(self, scale_midi_by_number=None):
        self.scale_midi_by_number = scale_midi_by_number or SCALE_MIDI_BY_NUMBER
        self._last_number = None

    def update(self, number):
        if number is None:
            self._last_number = None
            return None
        if number == self._last_number:
            return None
        self._last_number = number
        midi = self.scale_midi_by_number[number]
        return ScaleNote(number, midi, midi_to_name(midi))


class NumericGestureRecognizer:
    def __init__(self, extended_ratio=0.72, thumb_open_ratio=1.2):
        self.extended_ratio = extended_ratio
        self.thumb_open_ratio = thumb_open_ratio

    def classify(self, points):
        landmarks = normalize_landmarks(points)
        if len(landmarks) != 21:
            return None

        fingers = {
            "thumb": self._thumb_open(landmarks),
            "index": _finger_extended_up(landmarks, 5, 6, 8, self.extended_ratio),
            "middle": _finger_extended_up(landmarks, 9, 10, 12, self.extended_ratio),
            "ring": _finger_extended_up(landmarks, 13, 14, 16, self.extended_ratio),
            "pinky": _finger_extended_up(landmarks, 17, 18, 20, self.extended_ratio),
        }
        extended = {name for name, is_open in fingers.items() if is_open}

        patterns = {
            frozenset({"index"}): 1,
            frozenset({"index", "middle"}): 2,
            frozenset({"index", "middle", "ring"}): 3,
            frozenset({"index", "middle", "ring", "pinky"}): 4,
            frozenset({"thumb", "index", "middle", "ring", "pinky"}): 5,
            frozenset({"thumb", "pinky"}): 6,
            frozenset({"thumb", "index", "middle"}): 7,
            frozenset({"thumb", "index"}): 8,
        }
        return patterns.get(frozenset(extended))

    def _thumb_open(self, points):
        hand_scale = _distance(points[0], points[9])
        if hand_scale <= 0:
            return False
        return _distance(points[0], points[4]) >= hand_scale * self.thumb_open_ratio


def is_right_hand(obj, labels=None, mirrored=False):
    if labels and 0 <= obj.class_id < len(labels):
        is_right = str(labels[obj.class_id]).lower() == "right"
    else:
        is_right = obj.class_id == 1
    return not is_right if mirrored else is_right


def _distance(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


def _finger_extended_up(points, mcp, pip, tip, ratio):
    vertical = points[mcp][1] - points[tip][1]
    length = _distance(points[mcp], points[tip])
    return length > 0 and vertical / length >= ratio and points[tip][1] < points[pip][1]

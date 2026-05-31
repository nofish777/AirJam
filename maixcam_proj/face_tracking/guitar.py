from dataclasses import dataclass

from face_tracking.piano import normalize_landmarks


@dataclass(frozen=True)
class GuitarChord:
    name: str
    notes: list


@dataclass(frozen=True)
class GuitarStrumEvent:
    chord: str
    direction: str
    notes: list


ELECTRIC_GUITAR_CHORDS = [
    GuitarChord("C5", [48, 55, 60]),
    GuitarChord("D5", [50, 57, 62]),
    GuitarChord("E5", [52, 59, 64]),
    GuitarChord("F5", [53, 60, 65]),
    GuitarChord("G5", [55, 62, 67]),
    GuitarChord("A5", [57, 64, 69]),
    GuitarChord("Bb5", [58, 65, 70]),
    GuitarChord("B5", [59, 66, 71]),
]


ACOUSTIC_GUITAR_CHORDS = [
    GuitarChord("C", [48, 52, 55, 60, 64]),
    GuitarChord("G", [43, 47, 50, 55, 59, 67]),
    GuitarChord("Am", [45, 52, 57, 60, 64]),
    GuitarChord("F", [41, 48, 53, 57, 60, 65]),
    GuitarChord("D", [50, 57, 62, 66]),
    GuitarChord("Em", [40, 47, 52, 55, 59, 64]),
    GuitarChord("A", [45, 52, 57, 61, 64]),
    GuitarChord("E", [40, 47, 52, 56, 59, 64]),
]

GUITAR_CHORDS = ELECTRIC_GUITAR_CHORDS


class GuitarModeController:
    def __init__(self, chords=None, strum_threshold=650, cooldown_ms=120):
        self.chords = chords or ELECTRIC_GUITAR_CHORDS
        self.strum_threshold = strum_threshold
        self.cooldown_ms = cooldown_ms
        self.selected_chord = None
        self.last_y = None
        self.last_t = None
        self.cooldown_until = 0

    def update_left(self, number):
        if number is None:
            return None
        chord = chord_for_number(number, self.chords)
        if not chord:
            return None
        self.selected_chord = chord
        return chord.name

    def update_right(self, points, now_ms):
        if not self.selected_chord:
            self._remember_right(points, now_ms)
            return None
        landmarks = normalize_landmarks(points)
        if len(landmarks) != 21:
            self.last_y = None
            self.last_t = None
            return None

        y = _hand_y(landmarks)
        event = None
        if self.last_y is not None and self.last_t is not None:
            dt = max(1, now_ms - self.last_t)
            vy = (y - self.last_y) * 1000 / dt
            if now_ms >= self.cooldown_until and abs(vy) >= self.strum_threshold:
                direction = "down" if vy > 0 else "up"
                notes = self.selected_chord.notes if direction == "down" else list(reversed(self.selected_chord.notes))
                event = GuitarStrumEvent(self.selected_chord.name, direction, notes)
                self.cooldown_until = now_ms + self.cooldown_ms

        self.last_y = y
        self.last_t = now_ms
        return event

    def _remember_right(self, points, now_ms):
        landmarks = normalize_landmarks(points)
        if len(landmarks) == 21:
            self.last_y = _hand_y(landmarks)
            self.last_t = now_ms


def chord_for_number(number, chords=None):
    chords = chords or ELECTRIC_GUITAR_CHORDS
    if number is None or number < 1 or number > len(chords):
        return None
    return chords[number - 1]


def _hand_y(points):
    ids = [0, 5, 9, 13, 17]
    return int(sum(points[index][1] for index in ids) / len(ids))

from dataclasses import dataclass

from face_tracking.piano import normalize_landmarks
from face_tracking.scale_gestures import NumericGestureRecognizer


@dataclass(frozen=True)
class InstrumentZone:
    name: str
    x: int
    y: int
    w: int
    h: int

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass(frozen=True)
class InstrumentSelectionEvent:
    instrument: str
    x: int
    y: int


class InstrumentSelectionController:
    def __init__(self, zones, cooldown_ms=500):
        self.zones = zones
        self.cooldown_ms = cooldown_ms
        self.cooldown_until = 0
        self.selected_instrument = None
        self.hover_instrument = None
        self.hand_center = None
        self.numeric_recognizer = NumericGestureRecognizer()

    def update(self, points, now_ms):
        if self.selected_instrument:
            return None
        landmarks = normalize_landmarks(points)
        if len(landmarks) != 21:
            self.hover_instrument = None
            self.hand_center = None
            return None

        x, y = hand_center(landmarks)
        self.hand_center = (x, y)
        zone = instrument_at(x, y, self.zones)
        self.hover_instrument = zone.name if zone else None

        number = self.numeric_recognizer.classify(landmarks)
        zone_number = self.zones.index(zone) + 1 if zone else None
        if zone and number == zone_number and now_ms >= self.cooldown_until:
            self.selected_instrument = zone.name
            self.cooldown_until = now_ms + self.cooldown_ms
            return InstrumentSelectionEvent(zone.name, x, y)
        return None

    def reset(self):
        self.cooldown_until = 0
        self.selected_instrument = None
        self.hover_instrument = None
        self.hand_center = None


class InstrumentReturnController:
    def __init__(self, min_index_dx=12, cooldown_ms=700):
        self.min_index_dx = min_index_dx
        self.cooldown_ms = cooldown_ms
        self.cooldown_until = 0
        self.numeric_recognizer = NumericGestureRecognizer()

    def update(self, hands, now_ms):
        index_segments = []
        for hand_id, points in hands:
            landmarks = normalize_landmarks(points)
            if len(landmarks) != 21:
                continue
            if self.numeric_recognizer.classify(landmarks) == 1:
                index_segments.append((landmarks[5], landmarks[8]))

        if now_ms < self.cooldown_until:
            return False
        if self._index_fingers_crossed(index_segments):
            self.cooldown_until = now_ms + self.cooldown_ms
            return True
        return False

    def reset(self):
        self.cooldown_until = 0

    def _index_fingers_crossed(self, index_segments):
        if len(index_segments) < 2:
            return False
        for first_index in range(len(index_segments) - 1):
            for second_index in range(first_index + 1, len(index_segments)):
                first_base, first_tip = index_segments[first_index]
                second_base, second_tip = index_segments[second_index]
                first_dx = first_tip[0] - first_base[0]
                second_dx = second_tip[0] - second_base[0]
                if abs(first_dx) < self.min_index_dx or abs(second_dx) < self.min_index_dx:
                    continue
                if first_dx * second_dx >= 0:
                    continue
                if _segments_intersect(first_base, first_tip, second_base, second_tip):
                    return True
        return False


def default_instrument_zones(width, height):
    zone_w = width // 4
    return [
        InstrumentZone("drums", 0, 0, zone_w, height),
        InstrumentZone("electric_guitar", zone_w, 0, zone_w, height),
        InstrumentZone("acoustic_guitar", zone_w * 2, 0, zone_w, height),
        InstrumentZone("piano", zone_w * 3, 0, width - zone_w * 3, height),
    ]


def instrument_at(x, y, zones):
    for zone in zones:
        if zone.contains(x, y):
            return zone
    return None


def is_fist(points):
    landmarks = normalize_landmarks(points)
    if len(landmarks) != 21:
        return False
    return all(
        _finger_folded(landmarks, mcp, pip, tip)
        for mcp, pip, tip in [(5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)]
    )


def hand_center(points):
    landmarks = normalize_landmarks(points)
    ids = [0, 5, 9, 13, 17]
    return (
        int(sum(landmarks[index][0] for index in ids) / len(ids)),
        int(sum(landmarks[index][1] for index in ids) / len(ids)),
    )


def _finger_folded(points, mcp, pip, tip):
    return points[tip][1] > points[pip][1] and points[tip][1] >= points[mcp][1]


def _segments_intersect(a, b, c, d):
    return (
        _orientation(a, b, c) * _orientation(a, b, d) <= 0
        and _orientation(c, d, a) * _orientation(c, d, b) <= 0
    )


def _orientation(a, b, c):
    value = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0

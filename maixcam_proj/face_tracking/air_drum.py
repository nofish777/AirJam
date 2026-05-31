from dataclasses import dataclass

from face_tracking.piano import normalize_landmarks


GHOST_THRESHOLD = 300
NORMAL_THRESHOLD = 550
ACCENT_THRESHOLD = 800


@dataclass(frozen=True)
class DrumHit:
    drum: str
    articulation: str
    velocity: str
    power: int
    x: int
    y: int


@dataclass
class _HandMotionState:
    last_y: int = None
    last_t: int = None
    cooldown_until: int = 0
    armed: bool = True


class SnareDrumController:
    def __init__(
        self,
        ghost_threshold=GHOST_THRESHOLD,
        normal_threshold=NORMAL_THRESHOLD,
        accent_threshold=ACCENT_THRESHOLD,
        rearm_threshold=140,
        cooldown_ms=85,
    ):
        self.ghost_threshold = ghost_threshold
        self.normal_threshold = normal_threshold
        self.accent_threshold = accent_threshold
        self.rearm_threshold = rearm_threshold
        self.cooldown_ms = cooldown_ms
        self._states = {}
        self.last_hit = None

    def update(self, points, now_ms, hand_id=0):
        landmarks = normalize_landmarks(points)
        if len(landmarks) != 21:
            return None

        x, y = hand_center(landmarks)
        state = self._states.setdefault(hand_id, _HandMotionState())
        hit = None

        if state.last_y is not None and state.last_t is not None:
            dt = max(1, now_ms - state.last_t)
            vy = (y - state.last_y) * 1000 / dt
            if vy < self.rearm_threshold:
                state.armed = True
            if state.armed and now_ms >= state.cooldown_until and vy >= self.ghost_threshold:
                hit = DrumHit("snare", "hit", stroke_level(vy), int(vy), x, y)
                state.armed = False
                state.cooldown_until = now_ms + self.cooldown_ms
                self.last_hit = hit

        state.last_y = y
        state.last_t = now_ms
        return hit


def hand_center(points):
    landmarks = normalize_landmarks(points)
    ids = [0, 5, 9, 13, 17]
    return (
        int(sum(landmarks[index][0] for index in ids) / len(ids)),
        int(sum(landmarks[index][1] for index in ids) / len(ids)),
    )


def stroke_level(vy):
    if vy >= ACCENT_THRESHOLD:
        return "accent"
    if vy >= NORMAL_THRESHOLD:
        return "normal"
    return "ghost"

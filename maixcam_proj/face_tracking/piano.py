from dataclasses import dataclass
from math import pi, sin


NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MAJOR_DEGREES = ["1", "2", "3", "4", "5", "6", "7"]
MINOR_DEGREES = ["1#", "2#", "4#", "5#", "6#"]
WHITE_OFFSETS = [0, 2, 4, 5, 7, 9, 11]
BLACK_OFFSETS = [1, 3, 6, 8, 10]
LEFT_HAND_OCTAVES = {1: 2, 2: 3, 3: 4, 4: 5, 5: 6}


def midi_to_name(midi):
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def midi_to_frequency(midi):
    return 440.0 * (2 ** ((midi - 69) / 12))


@dataclass(frozen=True)
class PianoKey:
    name: str
    midi: int
    x: int
    y: int
    w: int
    h: int
    black: bool = False
    degree: str = ""

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass(frozen=True)
class PianoFrame:
    notes_on: list
    notes_off: list
    active_midi: list


@dataclass(frozen=True)
class PianoKeyboardLayout:
    white_keys: list
    black_keys: list

    def key_at(self, px, py):
        for key in self.black_keys:
            if key.contains(px, py):
                return key
        for key in self.white_keys:
            if key.contains(px, py):
                return key
        return None


class PianoGesturePlayer:
    def __init__(self, white_keys, black_keys, debounce_frames=1, release_frames=4):
        self.white_keys = white_keys
        self.black_keys = black_keys
        self.debounce_frames = debounce_frames
        self.release_frames = release_frames
        self._states = {
            key.midi: {"frames": 0, "release_frames": 0, "playing": False}
            for key in white_keys + black_keys
        }

    def update(self, points):
        active = set()
        notes_on = []
        notes_off = []

        for point in points:
            key = self.key_at(point[0], point[1])
            if key:
                active.add(key.midi)

        for key in self.white_keys + self.black_keys:
            state = self._states[key.midi]
            if key.midi in active:
                state["frames"] += 1
                state["release_frames"] = 0
                if not state["playing"] and state["frames"] >= self.debounce_frames:
                    state["playing"] = True
                    notes_on.append(key.midi)
            else:
                state["frames"] = 0
                if state["playing"]:
                    state["release_frames"] += 1
                    if state["release_frames"] >= self.release_frames:
                        state["playing"] = False
                        state["release_frames"] = 0
                        notes_off.append(key.midi)

        return PianoFrame(notes_on, notes_off, sorted(active))

    def key_at(self, px, py):
        for key in self.black_keys:
            if key.contains(px, py):
                return key
        for key in self.white_keys:
            if key.contains(px, py):
                return key
        return None


def create_piano_layout(width, height, white_count=14, start_midi=57, y=0, key_height=None):
    key_height = key_height if key_height is not None else int(height * 0.34)
    key_width = max(1, width // white_count)
    white_keys = []
    black_keys = []
    midi = start_midi
    white_midis = []

    for index in range(white_count):
        white_keys.append(
            PianoKey(midi_to_name(midi), midi, index * key_width, y, key_width, key_height, False)
        )
        white_midis.append(midi)
        midi += 2 if midi % 12 not in [4, 11] else 1

    black_width = max(1, int(key_width * 0.6))
    black_height = max(1, int(key_height * 0.6))
    for index, midi in enumerate(white_midis[:-1]):
        black_midi = midi + 1
        if black_midi % 12 in [1, 3, 6, 8, 10]:
            black_keys.append(
                PianoKey(
                    "",
                    black_midi,
                    (index + 1) * key_width - black_width // 2,
                    y,
                    black_width,
                    black_height,
                    True,
                )
            )

    return white_keys, black_keys


def create_touch_piano_layout(width, height, octave=4, y=0, key_height=None):
    key_height = key_height if key_height is not None else height
    white_width = max(1, width // 7)
    base_midi = 12 * (octave + 1)
    white_keys = []
    black_keys = []

    for index, offset in enumerate(WHITE_OFFSETS):
        x = index * white_width
        w = width - x if index == 6 else white_width
        white_keys.append(
            PianoKey(
                NOTE_NAMES[offset],
                base_midi + offset,
                x,
                y,
                w,
                key_height,
                False,
                MAJOR_DEGREES[index],
            )
        )

    black_width = max(1, int(white_width * 0.58))
    black_height = max(1, int(key_height * 0.62))
    black_after_white = [0, 1, 3, 4, 5]
    for degree, offset, white_index in zip(MINOR_DEGREES, BLACK_OFFSETS, black_after_white):
        black_keys.append(
            PianoKey(
                NOTE_NAMES[offset],
                base_midi + offset,
                (white_index + 1) * white_width - black_width // 2,
                y,
                black_width,
                black_height,
                True,
                degree,
            )
        )

    return PianoKeyboardLayout(white_keys, black_keys)


class PianoModeController:
    def __init__(self, width, height, y=0, key_height=None, default_octave=3, cooldown_ms=100):
        self.width = width
        self.height = height
        self.y = y
        self.key_height = key_height if key_height is not None else height
        self.cooldown_ms = cooldown_ms
        self.selected_octave = default_octave
        self.layout = create_touch_piano_layout(width, self.key_height, LEFT_HAND_OCTAVES[default_octave], y=y)
        self.last_midi = None
        self.cooldown_until = 0

    def update_left(self, number):
        if number not in LEFT_HAND_OCTAVES:
            return None
        self.selected_octave = number
        self.layout = create_touch_piano_layout(
            self.width,
            self.key_height,
            LEFT_HAND_OCTAVES[number],
            y=self.y,
        )
        self.last_midi = None
        self.cooldown_until = 0
        return number

    def update_right(self, points, now_ms):
        landmarks = normalize_landmarks(points)
        if len(landmarks) != 21:
            self.last_midi = None
            return None
        px, py = index_touch_point(landmarks)
        key = self.layout.key_at(px, py)
        if not key:
            self.last_midi = None
            return None
        if key.midi == self.last_midi and now_ms < self.cooldown_until:
            return None
        self.last_midi = key.midi
        self.cooldown_until = now_ms + self.cooldown_ms
        return key.midi


def index_touch_point(points):
    landmarks = normalize_landmarks(points)
    if len(landmarks) != 21:
        return None
    point = landmarks[8]
    return int(point[0]), int(point[1])


def normalize_landmarks(points):
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


def active_fingertips(points, finger_names=("Index", "Middle", "Ring"), lift_pixels=8):
    landmarks = normalize_landmarks(points)
    if len(landmarks) != 21:
        return []

    fingers = {
        "Index": (5, 8),
        "Middle": (9, 12),
        "Ring": (13, 16),
        "Pinky": (17, 20),
    }
    tips = []
    for name in finger_names:
        mcp, tip = fingers[name]
        if landmarks[tip][1] < landmarks[mcp][1] - lift_pixels:
            tips.append((int(landmarks[tip][0]), int(landmarks[tip][1])))
    return tips


def sine_pcm(midi, duration_ms=160, sample_rate=48000, volume=0.35):
    frequency = midi_to_frequency(midi)
    sample_count = max(1, int(sample_rate * duration_ms / 1000))
    data = bytearray()
    fade_samples = max(1, int(sample_rate * 0.018))
    max_amp = int(32767 * volume)

    for index in range(sample_count):
        fade_in = min(1.0, index / fade_samples)
        fade_out = min(1.0, (sample_count - index - 1) / fade_samples)
        envelope = min(fade_in, fade_out)
        value = int(max_amp * envelope * sin(2 * pi * frequency * index / sample_rate))
        data.extend(value.to_bytes(2, "little", signed=True))

    return bytes(data)


class PcmTonePlayer:
    def __init__(
        self,
        audio_module,
        sample_rate=48000,
        duration_ms=160,
        volume=100,
        tone_volume=0.18,
        min_gap_ms=120,
        now_ms=None,
    ):
        self.audio = audio_module
        self.sample_rate = sample_rate
        self.duration_ms = duration_ms
        self.tone_volume = tone_volume
        self.min_gap_ms = min_gap_ms
        self.now_ms = now_ms
        self._last_play_ms = None
        self.player = audio_module.Player(
            sample_rate=sample_rate,
            format=audio_module.Format.FMT_S16_LE,
            channel=1,
            block=True,
        )
        self.player.volume(volume)
        self._cache = {}

    def play_midi(self, midi):
        if self.now_ms:
            now = self.now_ms()
            if self._last_play_ms is not None and now - self._last_play_ms < self.min_gap_ms:
                return False
            self._last_play_ms = now
        if midi not in self._cache:
            self._cache[midi] = sine_pcm(
                midi,
                duration_ms=self.duration_ms,
                sample_rate=self.sample_rate,
                volume=self.tone_volume,
            )
        self.player.play(bytes(self._cache[midi]))
        return True

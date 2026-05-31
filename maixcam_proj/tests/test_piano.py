from face_tracking.piano import (
    PcmTonePlayer,
    PianoGesturePlayer,
    create_piano_layout,
    midi_to_frequency,
    sine_pcm,
)


def test_white_key_layout_starts_on_a3_and_reaches_g5():
    white_keys, black_keys = create_piano_layout(1400, 600)

    assert white_keys[0].name == "A3"
    assert white_keys[-1].name == "G5"
    assert black_keys[0].midi == 58


def test_piano_triggers_note_on_when_touch_enters_key_and_note_off_after_release():
    white_keys, black_keys = create_piano_layout(1400, 600)
    player = PianoGesturePlayer(white_keys, black_keys, debounce_frames=1, release_frames=2)
    first_key = white_keys[0]
    point = (first_key.x + first_key.w // 2, first_key.y + first_key.h // 2)

    pressed = player.update([point])
    held = player.update([point])
    first_release = player.update([])
    second_release = player.update([])

    assert pressed.notes_on == [first_key.midi]
    assert held.notes_on == []
    assert first_release.notes_off == []
    assert second_release.notes_off == [first_key.midi]


def test_black_keys_take_priority_over_white_keys():
    white_keys, black_keys = create_piano_layout(1400, 600)
    player = PianoGesturePlayer(white_keys, black_keys)
    black_key = black_keys[0]
    point = (black_key.x + black_key.w // 2, black_key.y + black_key.h // 2)

    frame = player.update([point])

    assert frame.notes_on == [black_key.midi]


def test_midi_to_frequency_uses_a4_reference():
    assert round(midi_to_frequency(69), 2) == 440.00


def test_sine_pcm_generates_16_bit_mono_samples_for_requested_duration():
    data = sine_pcm(69, duration_ms=100, sample_rate=48000)

    assert len(data) == 4800 * 2


def test_pcm_tone_player_sends_note_bytes_to_maix_player():
    calls = []

    class FakeMaixPlayer:
        def __init__(self, sample_rate, format, channel, block):
            calls.append(("init", sample_rate, format, channel, block))

        def volume(self, value):
            calls.append(("volume", value))

        def play(self, data):
            calls.append(("play", len(data)))

    class FakeAudio:
        class Format:
            FMT_S16_LE = "s16"

        Player = FakeMaixPlayer

    player = PcmTonePlayer(audio_module=FakeAudio, duration_ms=50)
    player.play_midi(69)

    assert calls[0] == ("init", 48000, "s16", 1, True)
    assert calls[1] == ("volume", 100)
    assert calls[2] == ("play", 2400 * 2)


def test_pcm_tone_player_skips_notes_until_minimum_gap_passes():
    calls = []

    class FakeMaixPlayer:
        def __init__(self, sample_rate, format, channel, block):
            pass

        def volume(self, value):
            pass

        def play(self, data):
            calls.append(len(data))

    class FakeAudio:
        class Format:
            FMT_S16_LE = "s16"

        Player = FakeMaixPlayer

    ticks = iter([0, 50, 180])
    player = PcmTonePlayer(audio_module=FakeAudio, duration_ms=50, now_ms=lambda: next(ticks))

    player.play_midi(69)
    player.play_midi(71)
    player.play_midi(72)

    assert calls == [2400 * 2, 2400 * 2]

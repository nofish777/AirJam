from face_tracking.note_output import (
    DrumHitEvent,
    GuitarChordEvent,
    ModeEvent,
    NoteEvent,
    UdpInstrumentOutput,
    UdpDrumOutput,
    UdpNoteOutput,
    parse_mode_event,
    parse_drum_hit_event,
    parse_instrument_note_event,
    parse_guitar_chord_event,
    parse_note_event,
)


def test_udp_note_output_sends_compact_note_event():
    sent = []

    class FakeSocket:
        def sendto(self, payload, address):
            sent.append((payload, address))

    output = UdpNoteOutput("192.168.1.10", 5010, socket_factory=lambda: FakeSocket())

    output.play_midi(60, duration_ms=160)

    assert sent == [(b"NOTE 60 160", ("192.168.1.10", 5010))]


def test_parse_note_event_accepts_valid_note_message():
    assert parse_note_event("NOTE 64 120") == NoteEvent(midi=64, duration_ms=120)


def test_parse_note_event_rejects_invalid_or_out_of_range_messages():
    assert parse_note_event("HELLO 64 120") is None
    assert parse_note_event("NOTE nope 120") is None
    assert parse_note_event("NOTE 200 120") is None


def test_udp_drum_output_sends_hit_event():
    sent = []

    class FakeSocket:
        def sendto(self, payload, address):
            sent.append((payload, address))

    output = UdpDrumOutput("192.168.1.10", 5020, socket_factory=lambda: FakeSocket())

    output.play_hit("snare", "hit", "hard", 1800)

    assert sent == [(b"HIT|snare|hit|hard|1800", ("192.168.1.10", 5020))]


def test_udp_drum_output_can_send_simple_hit_event():
    sent = []

    class FakeSocket:
        def sendto(self, payload, address):
            sent.append((payload, address))

    output = UdpDrumOutput("192.168.1.10", 5020, socket_factory=lambda: FakeSocket())

    output.play_simple_hit("kick")

    assert sent == [(b"HIT|kick", ("192.168.1.10", 5020))]


def test_parse_drum_hit_event_accepts_valid_hit_message():
    assert parse_drum_hit_event("HIT|hihat|open|normal|1200") == DrumHitEvent(
        drum="hihat",
        articulation="open",
        velocity="normal",
        power=1200,
    )
    assert parse_drum_hit_event("HIT|snare|hit|ghost|700") == DrumHitEvent(
        drum="snare",
        articulation="hit",
        velocity="ghost",
        power=700,
    )
    assert parse_drum_hit_event("HIT|snare|hit|accent|1800") == DrumHitEvent(
        drum="snare",
        articulation="hit",
        velocity="accent",
        power=1800,
    )


def test_parse_drum_hit_event_accepts_simple_hit_message():
    assert parse_drum_hit_event("HIT|ride") == DrumHitEvent(
        drum="ride",
        articulation="hit",
        velocity="normal",
        power=1000,
    )


def test_parse_drum_hit_event_rejects_bad_messages():
    assert parse_drum_hit_event("NOTE 60 160") is None
    assert parse_drum_hit_event("HIT|snare|hit|loud|1200") is None
    assert parse_drum_hit_event("HIT|snare|hit|hard|oops") is None


def test_udp_instrument_output_sends_mode_and_note_messages():
    sent = []

    class FakeSocket:
        def sendto(self, payload, address):
            sent.append((payload, address))

    output = UdpInstrumentOutput("192.168.1.10", 5020, socket_factory=lambda: FakeSocket())

    output.set_mode("electric_guitar")
    output.play_note("piano", 60, duration_ms=140)

    assert sent == [
        (b"MODE|electric_guitar", ("192.168.1.10", 5020)),
        (b"NOTE|piano|60|140", ("192.168.1.10", 5020)),
    ]


def test_udp_instrument_output_sends_snare_hit_velocity_messages():
    sent = []

    class FakeSocket:
        def sendto(self, payload, address):
            sent.append((payload, address))

    output = UdpInstrumentOutput("192.168.1.10", 5020, socket_factory=lambda: FakeSocket())

    output.play_hit("snare", "hit", "accent", 1800)

    assert sent == [(b"HIT|snare|hit|accent|1800", ("192.168.1.10", 5020))]


def test_parse_mode_event_accepts_known_instruments():
    assert parse_mode_event("MODE|electric_guitar") == ModeEvent("electric_guitar")
    assert parse_mode_event("MODE|acoustic_guitar") == ModeEvent("acoustic_guitar")
    assert parse_mode_event("MODE|flute") is None


def test_parse_instrument_note_event_accepts_valid_note():
    assert parse_instrument_note_event("NOTE|piano|60|140") == NoteEvent(
        midi=60,
        duration_ms=140,
    )
    assert parse_instrument_note_event("NOTE|acoustic_guitar|52|140") == NoteEvent(
        midi=52,
        duration_ms=140,
    )
    assert parse_instrument_note_event("NOTE|piano|200|140") is None


def test_udp_instrument_output_sends_guitar_chord_messages():
    sent = []

    class FakeSocket:
        def sendto(self, payload, address):
            sent.append((payload, address))

    output = UdpInstrumentOutput("192.168.1.10", 5020, socket_factory=lambda: FakeSocket())

    output.play_guitar_chord("electric_guitar", "Bb5", "down")

    assert sent == [(b"GUITAR|electric_guitar|Bb5|down", ("192.168.1.10", 5020))]


def test_parse_guitar_chord_event_accepts_common_chords_and_direction():
    assert parse_guitar_chord_event("GUITAR|electric_guitar|C5|up") == GuitarChordEvent(
        "electric_guitar",
        "C5",
        "up",
    )
    assert parse_guitar_chord_event("GUITAR|acoustic_guitar|E|down") == GuitarChordEvent(
        "acoustic_guitar",
        "E",
        "down",
    )
    assert parse_guitar_chord_event("GUITAR|guitar|C5|down") is None
    assert parse_guitar_chord_event("GUITAR|acoustic_guitar|B5|down") is None
    assert parse_guitar_chord_event("GUITAR|electric_guitar|Cmaj7|down") is None
    assert parse_guitar_chord_event("GUITAR|electric_guitar|C5|side") is None

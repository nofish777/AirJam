import argparse
import os
from pathlib import Path
import socket
import subprocess
import threading
import time

import fluidsynth

from face_tracking.note_output import (
    parse_guitar_chord_event,
    parse_drum_hit_event,
    parse_instrument_note_event,
    parse_mode_event,
)


DEFAULT_PORT = 5020
DEFAULT_DRUM_SF2 = "../pc_runtime/instruments/drums/Shino Drums(sf2)/02_Shino_Snare.sf2"
DEFAULT_DRUM_SAMPLE_DIR = "../pc_runtime/instruments/drums/Shino Drums(sf2)/snare_samples"
DEFAULT_GM_SF2 = "../pc_runtime/instruments/pianos/SalamanderGrandPiano-V3/SalamanderGrandPiano-V3+20200602.sf2"
DEFAULT_PIANO_SAMPLE_DIR = "../pc_runtime/instruments/pianos/SalamanderGrandPiano-V3/samples"
DEFAULT_ELECTRIC_GUITAR_SF2 = "../pc_runtime/instruments/guitars/Bread Breads Distortion Guitar/Bread Breads Distortion Guitar v2.1.sf2"
DEFAULT_ACOUSTIC_GUITAR_SF2 = "../pc_runtime/instruments/guitars/acoustic_guitar/FSS-SteelStringGuitar-20200521.sf2"
DEFAULT_ELECTRIC_GUITAR_SAMPLE_DIR = "../pc_runtime/instruments/guitars/Bread Breads Distortion Guitar/strums"
DEFAULT_ACOUSTIC_GUITAR_SAMPLE_DIR = "../pc_runtime/instruments/guitars/acoustic_guitar/strums"

SNARE_MIDI_NOTE = 40
SNARE_BANK = 0
SNARE_PRESET = 2
SNARE_VELOCITIES = {
    "ghost": 42,
    "soft": 52,
    "normal": 90,
    "hard": 118,
    "accent": 127,
}

CHANNELS = {
    "piano": 0,
    "electric_guitar": 1,
    "acoustic_guitar": 2,
    "drums": 9,
}

ELECTRIC_GUITAR_CHORDS = {
    "C5": [48, 55, 60],
    "D5": [50, 57, 62],
    "E5": [52, 59, 64],
    "F5": [53, 60, 65],
    "G5": [55, 62, 67],
    "A5": [57, 64, 69],
    "Bb5": [58, 65, 70],
    "B5": [59, 66, 71],
}

ACOUSTIC_GUITAR_CHORDS = {
    "C": [48, 52, 55, 60, 64],
    "G": [43, 47, 50, 55, 59, 67],
    "Am": [45, 52, 57, 60, 64],
    "F": [41, 48, 53, 57, 60, 65],
    "D": [50, 57, 62, 66],
    "Em": [40, 47, 52, 55, 59, 64],
    "A": [45, 52, 57, 61, 64],
    "E": [40, 47, 52, 56, 59, 64],
}


class InstrumentSynthServer:
    def __init__(
        self,
        drum_sf2,
        gm_sf2,
        electric_guitar_sf2,
        acoustic_guitar_sf2,
        drum_sample_dir,
        piano_sample_dir,
        electric_guitar_sample_dir,
        acoustic_guitar_sample_dir,
        gain=1.2,
    ):
        _require_soundfont(drum_sf2, "drum")
        _require_soundfont(gm_sf2, "piano")
        _require_soundfont(electric_guitar_sf2, "electric guitar")
        self.current_mode = "drums"
        self.loaded_instruments = {"drums", "piano", "electric_guitar"}
        self.synth = fluidsynth.Synth(gain=gain)
        self.snare_samples = SnareSampleBank(drum_sample_dir)
        self.piano_samples = PianoSampleBank(piano_sample_dir)
        self.electric_samples = WaveSampleBank(electric_guitar_sample_dir, ELECTRIC_GUITAR_CHORDS)
        self.acoustic_samples = WaveSampleBank(acoustic_guitar_sample_dir, ACOUSTIC_GUITAR_CHORDS)
        self._start_audio_driver()
        drum_sfid = self.synth.sfload(str(drum_sf2))
        gm_sfid = self.synth.sfload(str(gm_sf2))
        electric_guitar_sfid = self.synth.sfload(str(electric_guitar_sf2))
        acoustic_guitar_sfid = self._load_optional_soundfont(acoustic_guitar_sf2, "acoustic guitar")
        self.synth.program_select(CHANNELS["drums"], drum_sfid, SNARE_BANK, SNARE_PRESET)
        self.synth.program_select(CHANNELS["piano"], gm_sfid, 0, 0)
        self.synth.program_select(CHANNELS["electric_guitar"], electric_guitar_sfid, 0, 0)
        if acoustic_guitar_sfid is not None:
            self.loaded_instruments.add("acoustic_guitar")
            self.synth.program_select(CHANNELS["acoustic_guitar"], acoustic_guitar_sfid, 0, 0)

    def set_mode(self, instrument):
        self.current_mode = instrument
        print(f"mode: {instrument}")

    def play_drum(self, drum, velocity="normal"):
        if drum != "snare":
            print(f"unknown drum: {drum}")
            return
        if self.snare_samples.play(velocity):
            return
        midi_velocity = SNARE_VELOCITIES.get(velocity, SNARE_VELOCITIES["normal"])
        self._play(CHANNELS["drums"], SNARE_MIDI_NOTE, 90, velocity=midi_velocity)

    def play_note(self, instrument, midi, duration_ms):
        if instrument == "piano":
            self._play_piano_note(midi, duration_ms)
            return
        channel = CHANNELS[instrument]
        self._play(channel, midi, duration_ms)

    def play_guitar_chord(self, instrument, chord, direction):
        if instrument == "electric_guitar":
            self._play_electric_guitar_chord(chord, direction)
            return
        if instrument == "acoustic_guitar":
            self._play_acoustic_guitar_chord(chord, direction)
            return
        if instrument not in self.loaded_instruments:
            print(f"{instrument} soundfont is not loaded")
            return
        notes = ELECTRIC_GUITAR_CHORDS.get(chord)
        if notes is None:
            print(f"unknown guitar chord: {chord}")
            return
        channel = CHANNELS[instrument]
        ordered = notes if direction == "down" else list(reversed(notes))
        threading.Thread(target=self._strum_notes, args=(channel, ordered), daemon=True).start()

    def close(self):
        self.synth.delete()

    def _play_piano_note(self, midi, duration_ms):
        if self.piano_samples.play(midi):
            return
        self._play(CHANNELS["piano"], midi, duration_ms)

    def _play_electric_guitar_chord(self, chord, direction):
        if self.electric_samples.play(chord, direction):
            return
        if "electric_guitar" not in self.loaded_instruments:
            print(f"missing electric guitar strum sample: {chord} {direction}")
            return
        notes = ELECTRIC_GUITAR_CHORDS.get(chord)
        if notes is None:
            print(f"unknown electric guitar chord: {chord}")
            return
        channel = CHANNELS["electric_guitar"]
        ordered = notes if direction == "down" else list(reversed(notes))
        threading.Thread(target=self._strum_notes, args=(channel, ordered), daemon=True).start()

    def _play_acoustic_guitar_chord(self, chord, direction):
        if self.acoustic_samples.play(chord, direction):
            return
        if "acoustic_guitar" not in self.loaded_instruments:
            print(f"missing acoustic guitar strum sample: {chord} {direction}")
            return
        notes = ACOUSTIC_GUITAR_CHORDS.get(chord)
        if notes is None:
            print(f"unknown acoustic guitar chord: {chord}")
            return
        channel = CHANNELS["acoustic_guitar"]
        ordered = notes if direction == "down" else list(reversed(notes))
        threading.Thread(target=self._strum_notes, args=(channel, ordered), daemon=True).start()

    def _play(self, channel, midi, duration_ms, velocity=127):
        self.synth.noteon(channel, midi, velocity)
        threading.Thread(target=self._noteoff_later, args=(channel, midi, duration_ms), daemon=True).start()

    def _noteoff_later(self, channel, midi, duration_ms):
        time.sleep(duration_ms / 1000)
        self.synth.noteoff(channel, midi)

    def _strum_notes(self, channel, notes):
        active = []
        for midi in notes:
            self.synth.noteon(channel, midi, 127)
            active.append(midi)
            time.sleep(0.018)
        time.sleep(0.22)
        for midi in active:
            self.synth.noteoff(channel, midi)

    def _start_audio_driver(self):
        last_error = None
        for audio_driver in ("dsound", "waveout", "wasapi"):
            try:
                self.synth.start(driver=audio_driver, midi_driver=None)
                print(f"FluidSynth audio driver: {audio_driver}")
                return
            except Exception as exc:
                last_error = exc
                print(f"FluidSynth driver failed ({audio_driver}): {exc}")
        raise RuntimeError(f"No usable FluidSynth audio driver found: {last_error}")

    def _load_optional_soundfont(self, path, label):
        if not Path(path).exists():
            print(f"warning: {label} soundfont not found, mode will be silent: {path}")
            return None
        return self.synth.sfload(str(path))


def _require_soundfont(path, label):
    if not Path(path).exists():
        raise FileNotFoundError(f"{label} soundfont not found: {path}")


class WaveSampleBank:
    def __init__(self, sample_dir, chord_notes, player=None):
        self.sample_dir = Path(sample_dir)
        self.chord_notes = chord_notes
        self.player = player or _default_wave_player
        self.samples = {
            (chord, direction): self.sample_dir / f"{chord}_{direction}.wav"
            for chord in chord_notes
            for direction in ("down", "up")
        }

    def play(self, chord, direction):
        path = self.samples.get((chord, direction))
        if path is None or not path.exists():
            return False
        self.player(path)
        return True


class SnareSampleBank:
    def __init__(self, sample_dir, player=None):
        self.sample_dir = Path(sample_dir)
        self.player = player or _default_wave_player
        self.samples = {
            velocity: self.sample_dir / f"{velocity}.wav"
            for velocity in ("ghost", "normal", "accent")
        }

    def play(self, velocity):
        path = self.samples.get(velocity)
        if path is None or not path.exists():
            return False
        self.player(path)
        return True


class PianoSampleBank:
    def __init__(self, sample_dir, player=None):
        self.sample_dir = Path(sample_dir)
        self.player = player or _default_wave_player

    def play(self, midi):
        path = self.sample_dir / f"{int(midi):03d}.wav"
        if not path.exists():
            return False
        self.player(path)
        return True


def _default_wave_player(path):
    if os.name == "nt":
        import winsound

        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
        return
    subprocess.Popen(["aplay", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def serve(
    host,
    port,
    drum_sf2,
    gm_sf2,
    electric_guitar_sf2,
    acoustic_guitar_sf2,
    drum_sample_dir,
    piano_sample_dir,
    electric_guitar_sample_dir,
    acoustic_guitar_sample_dir,
    gain,
):
    server = InstrumentSynthServer(
        drum_sf2,
        gm_sf2,
        electric_guitar_sf2,
        acoustic_guitar_sf2,
        drum_sample_dir,
        piano_sample_dir,
        electric_guitar_sample_dir,
        acoustic_guitar_sample_dir,
        gain=gain,
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"Instrument server listening on {host}:{port}")
    try:
        while True:
            payload, address = sock.recvfrom(128)
            mode = parse_mode_event(payload)
            if mode:
                server.set_mode(mode.instrument)
                continue
            hit = parse_drum_hit_event(payload)
            if hit:
                print(f"hit {hit.drum} {hit.velocity} from {address}")
                server.play_drum(hit.drum, hit.velocity)
                continue
            note = parse_instrument_note_event(payload)
            if note:
                message = payload.decode("ascii", "ignore")
                instrument = message.split("|")[1]
                print(f"note {instrument} {note.midi} from {address}")
                server.play_note(instrument, note.midi, note.duration_ms)
                continue
            guitar = parse_guitar_chord_event(payload)
            if guitar:
                print(f"{guitar.instrument} {guitar.chord} {guitar.direction} from {address}")
                server.play_guitar_chord(guitar.instrument, guitar.chord, guitar.direction)
                continue
            print(f"ignored from {address}: {payload!r}")
    except KeyboardInterrupt:
        print("stopping")
    finally:
        sock.close()
        server.close()


def main():
    parser = argparse.ArgumentParser(description="Receive MaixCAM2 instrument events and route to soundfonts.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--drum-sf2", default=DEFAULT_DRUM_SF2)
    parser.add_argument("--drum-sample-dir", default=DEFAULT_DRUM_SAMPLE_DIR)
    parser.add_argument("--gm-sf2", default=DEFAULT_GM_SF2)
    parser.add_argument("--piano-sample-dir", default=DEFAULT_PIANO_SAMPLE_DIR)
    parser.add_argument("--electric-guitar-sf2", default=DEFAULT_ELECTRIC_GUITAR_SF2)
    parser.add_argument("--acoustic-guitar-sf2", default=DEFAULT_ACOUSTIC_GUITAR_SF2)
    parser.add_argument("--electric-guitar-sample-dir", default=DEFAULT_ELECTRIC_GUITAR_SAMPLE_DIR)
    parser.add_argument("--acoustic-guitar-sample-dir", default=DEFAULT_ACOUSTIC_GUITAR_SAMPLE_DIR)
    parser.add_argument("--gain", type=float, default=1.2)
    args = parser.parse_args()
    serve(
        args.host,
        args.port,
        Path(args.drum_sf2).resolve(),
        Path(args.gm_sf2).resolve(),
        Path(args.electric_guitar_sf2).resolve(),
        Path(args.acoustic_guitar_sf2).resolve(),
        Path(args.drum_sample_dir).resolve(),
        Path(args.piano_sample_dir).resolve(),
        Path(args.electric_guitar_sample_dir).resolve(),
        Path(args.acoustic_guitar_sample_dir).resolve(),
        args.gain,
    )


if __name__ == "__main__":
    main()

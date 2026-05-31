import argparse
from pathlib import Path
import socket
import threading
import time

import fluidsynth

from face_tracking.note_output import parse_drum_hit_event


DEFAULT_PORT = 5020
DEFAULT_SF2_PATH = "../pc_runtime/instruments/drums/bread_breads_drum_kit/Bread Breads Drum Kit1.03.1.sf2"
DEFAULT_BANK = 128
DEFAULT_PRESET = 0

DRUM_MIDI_NOTES = {
    "kick": 36,
    "snare": 38,
    "hihat": 42,
    "closed_hihat": 42,
    "open_hihat": 46,
    "high_tom": 50,
    "mid_tom": 47,
    "floor_tom": 43,
    "crash": 49,
    "ride": 51,
}


class BreadDrumSynth:
    def __init__(self, sf2_path, bank=DEFAULT_BANK, preset=DEFAULT_PRESET, gain=1.0):
        self.synth = fluidsynth.Synth(gain=gain)
        self._start_audio_driver()
        sfid = self.synth.sfload(str(sf2_path))
        self.synth.program_select(9, sfid, bank, preset)

    def play(self, drum):
        midi = DRUM_MIDI_NOTES.get(drum)
        if midi is None:
            print(f"unknown drum: {drum}")
            return
        self.synth.noteon(9, midi, 127)
        threading.Thread(target=self._noteoff_later, args=(midi,), daemon=True).start()

    def close(self):
        self.synth.delete()

    def _noteoff_later(self, midi):
        time.sleep(0.08)
        self.synth.noteoff(9, midi)

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


def serve(host, port, sf2_path, bank, preset, gain):
    synth = BreadDrumSynth(sf2_path, bank=bank, preset=preset, gain=gain)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"Bread drum server listening on {host}:{port}")
    print(f"SoundFont: {sf2_path}")
    try:
        while True:
            payload, address = sock.recvfrom(128)
            event = parse_drum_hit_event(payload)
            if not event:
                print(f"ignored from {address}: {payload!r}")
                continue
            print(f"hit {event.drum} from {address}")
            synth.play(event.drum)
    except KeyboardInterrupt:
        print("stopping")
    finally:
        sock.close()
        synth.close()


def main():
    parser = argparse.ArgumentParser(description="Receive MaixCAM2 air-drum events and play Bread Bread's Drum Kit.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--sf2", default=DEFAULT_SF2_PATH)
    parser.add_argument("--bank", type=int, default=DEFAULT_BANK)
    parser.add_argument("--preset", type=int, default=DEFAULT_PRESET)
    parser.add_argument("--gain", type=float, default=1.2)
    args = parser.parse_args()
    serve(args.host, args.port, Path(args.sf2).resolve(), args.bank, args.preset, args.gain)


if __name__ == "__main__":
    main()

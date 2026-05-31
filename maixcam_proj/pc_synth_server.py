import argparse
from pathlib import Path
import socket
import time

import fluidsynth

from face_tracking.note_output import parse_note_event


DEFAULT_PORT = 5010
DEFAULT_SF2_PATH = "../pc_runtime/instruments/pianos/fluid_r3/FluidR3_GM.sf2"
DEFAULT_PROGRAM = 0


class FluidSynthNotePlayer:
    def __init__(self, sf2_path, program=DEFAULT_PROGRAM, gain=1.0):
        self.synth = fluidsynth.Synth(gain=gain)
        self._start_audio_driver()
        sfid = self.synth.sfload(str(sf2_path))
        self.synth.program_select(0, sfid, 0, program)

    def play(self, midi, duration_ms):
        self.synth.noteon(0, midi, 127)
        time.sleep(duration_ms / 1000)
        self.synth.noteoff(0, midi)

    def close(self):
        self.synth.delete()

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


def serve(host, port, sf2_path, program, gain):
    player = FluidSynthNotePlayer(sf2_path, program=program, gain=gain)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"PC synth server listening on {host}:{port}")
    print(f"SoundFont: {sf2_path}")
    try:
        while True:
            payload, address = sock.recvfrom(128)
            event = parse_note_event(payload)
            if not event:
                print(f"ignored from {address}: {payload!r}")
                continue
            print(f"note {event.midi}, {event.duration_ms}ms from {address}")
            player.play(event.midi, event.duration_ms)
    except KeyboardInterrupt:
        print("stopping")
    finally:
        player.close()
        sock.close()


def main():
    parser = argparse.ArgumentParser(description="Receive MaixCam2 note events and play them on this PC.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--sf2", default=DEFAULT_SF2_PATH)
    parser.add_argument("--program", type=int, default=DEFAULT_PROGRAM)
    parser.add_argument("--gain", type=float, default=1.0)
    args = parser.parse_args()

    sf2_path = Path(args.sf2).resolve()
    serve(args.host, args.port, sf2_path, args.program, args.gain)


if __name__ == "__main__":
    main()

import argparse
from pathlib import Path
import socket
import threading
import wave

import numpy as np
import sounddevice as sd

try:
    import pygame
except ModuleNotFoundError:
    pygame = None

from face_tracking.note_output import parse_drum_hit_event


DEFAULT_PORT = 5020
DEFAULT_SAMPLE_DIR = "../pc_runtime/instruments/samples/drums"
DRUMS = ["kick", "snare", "hihat", "high_tom", "mid_tom", "floor_tom", "crash", "ride"]
VELOCITIES = ["soft", "normal", "hard"]


class DrumSampler:
    def __init__(self, sample_dir):
        self.sample_dir = Path(sample_dir)
        if pygame is not None:
            self.backend = PygameDrumBackend(self.sample_dir)
        else:
            self.backend = SoundDeviceDrumBackend(self.sample_dir)

    def play(self, drum, articulation, velocity):
        self.backend.play(drum, articulation, velocity)

    def close(self):
        self.backend.close()


class PygameDrumBackend:
    def __init__(self, sample_dir):
        self.sample_dir = sample_dir
        pygame.mixer.pre_init(44100, -16, 2, 256)
        pygame.init()
        pygame.mixer.set_num_channels(32)
        self.samples = {}
        self._load_samples()
        print("audio backend: pygame")

    def play(self, drum, articulation, velocity):
        sound = self.samples.get((drum, articulation, velocity))
        if sound is None:
            sound = self.samples.get((drum, articulation, "normal"))
        if sound is not None:
            sound.play()

    def close(self):
        pygame.quit()

    def _load_samples(self):
        for drum in DRUMS:
            articulations = ["closed", "open"] if drum == "hihat" else ["hit"]
            for articulation in articulations:
                for velocity in VELOCITIES:
                    path = self.sample_dir / _sample_name(drum, articulation, velocity)
                    if path.exists():
                        self.samples[(drum, articulation, velocity)] = pygame.mixer.Sound(str(path))
        print(f"loaded {len(self.samples)} drum samples from {self.sample_dir}")


class SoundDeviceDrumBackend:
    def __init__(self, sample_dir):
        self.sample_dir = sample_dir
        self.samples = {}
        self.active = []
        self.lock = threading.Lock()
        self.sample_rate = 44100
        self._load_samples()
        self.stream = sd.OutputStream(
            samplerate=self.sample_rate,
            channels=2,
            dtype="float32",
            blocksize=256,
            callback=self._callback,
        )
        self.stream.start()
        print("audio backend: sounddevice")

    def play(self, drum, articulation, velocity):
        sample = self.samples.get((drum, articulation, velocity))
        if sample is None:
            sample = self.samples.get((drum, articulation, "normal"))
        if sample is None:
            return
        with self.lock:
            self.active.append({"data": sample, "pos": 0})

    def close(self):
        self.stream.stop()
        self.stream.close()

    def _load_samples(self):
        for drum in DRUMS:
            articulations = ["closed", "open"] if drum == "hihat" else ["hit"]
            for articulation in articulations:
                for velocity in VELOCITIES:
                    path = self.sample_dir / _sample_name(drum, articulation, velocity)
                    if not path.exists():
                        continue
                    data, sample_rate = _read_wav_float32(path)
                    if sample_rate != self.sample_rate:
                        print(f"skipped {path}: sample rate {sample_rate}, expected {self.sample_rate}")
                        continue
                    self.samples[(drum, articulation, velocity)] = data
        print(f"loaded {len(self.samples)} drum samples from {self.sample_dir}")

    def _callback(self, outdata, frames, time_info, status):
        outdata.fill(0)
        with self.lock:
            remaining = []
            for active in self.active:
                data = active["data"]
                pos = active["pos"]
                chunk = data[pos:pos + frames]
                outdata[:len(chunk)] += chunk
                active["pos"] += len(chunk)
                if active["pos"] < len(data):
                    remaining.append(active)
            self.active = remaining
        np.clip(outdata, -1.0, 1.0, out=outdata)


def serve(host, port, sample_dir):
    sampler = DrumSampler(sample_dir)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"PC drum sampler listening on {host}:{port}")
    try:
        while True:
            payload, address = sock.recvfrom(128)
            event = parse_drum_hit_event(payload)
            if not event:
                print(f"ignored from {address}: {payload!r}")
                continue
            print(f"{event.drum} {event.articulation} {event.velocity} power={event.power}")
            sampler.play(event.drum, event.articulation, event.velocity)
    except KeyboardInterrupt:
        print("stopping")
    finally:
        sock.close()
        sampler.close()


def _sample_name(drum, articulation, velocity):
    if drum == "hihat":
        return f"hihat_{articulation}_{velocity}.wav"
    return f"{drum}_{velocity}.wav"


def _read_wav_float32(path):
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if sample_width != 2:
        raise ValueError(f"{path} must be 16-bit PCM WAV")
    data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    data = data.reshape(-1, channels)
    if channels == 1:
        data = np.repeat(data, 2, axis=1)
    elif channels > 2:
        data = data[:, :2]
    return data, sample_rate


def main():
    parser = argparse.ArgumentParser(description="Receive MaixCAM2 air-drum hit events and play WAV samples.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--samples", default=DEFAULT_SAMPLE_DIR)
    args = parser.parse_args()
    serve(args.host, args.port, args.samples)


if __name__ == "__main__":
    main()

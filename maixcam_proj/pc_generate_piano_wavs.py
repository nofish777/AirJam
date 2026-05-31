import argparse
from array import array
from dataclasses import dataclass
from pathlib import Path
import sys
import wave


DEFAULT_SF2 = "../pc_runtime/instruments/pianos/SalamanderGrandPiano-V3/SalamanderGrandPiano-V3+20200602.sf2"
DEFAULT_OUTPUT_DIR = "../pc_runtime/instruments/pianos/SalamanderGrandPiano-V3/samples"
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_GAIN = 1.2
PIANO_BANK = 0
PIANO_PRESET = 0
LOWEST_MIDI = 36
HIGHEST_MIDI = 95
VELOCITY = 104
SUSTAIN_MS = 900
RELEASE_MS = 260


@dataclass(frozen=True)
class RenderPlan:
    midi: int
    filename: str


def build_render_plan():
    return [
        RenderPlan(midi, f"{midi:03d}.wav")
        for midi in range(LOWEST_MIDI, HIGHEST_MIDI + 1)
    ]


def render_all(soundfont_path, output_dir, sample_rate=DEFAULT_SAMPLE_RATE, gain=DEFAULT_GAIN):
    import fluidsynth

    soundfont_path = Path(soundfont_path)
    output_dir = Path(output_dir)
    if not soundfont_path.exists():
        raise FileNotFoundError(f"piano soundfont not found: {soundfont_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    synth = fluidsynth.Synth(samplerate=sample_rate, gain=gain)
    try:
        sfid = synth.sfload(str(soundfont_path))
        synth.program_select(0, sfid, PIANO_BANK, PIANO_PRESET)
        for plan in build_render_plan():
            wav_path = output_dir / plan.filename
            audio = render_note(synth, plan.midi, sample_rate)
            write_wav(wav_path, audio, sample_rate)
            print(f"wrote {wav_path}")
    finally:
        synth.delete()


def render_note(synth, midi, sample_rate):
    sustain_frames = _ms_to_frames(SUSTAIN_MS, sample_rate)
    release_frames = _ms_to_frames(RELEASE_MS, sample_rate)
    synth.noteon(0, midi, VELOCITY)
    audio = _samples_to_bytes(synth.get_samples(sustain_frames))
    synth.noteoff(0, midi)
    audio += _samples_to_bytes(synth.get_samples(release_frames))
    return audio


def write_wav(path, pcm_bytes, sample_rate):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)


def _ms_to_frames(milliseconds, sample_rate):
    return max(1, int(sample_rate * milliseconds / 1000))


def _samples_to_bytes(samples):
    if hasattr(samples, "astype"):
        return samples.astype("<i2").tobytes()
    values = list(samples)
    if values and max(abs(float(value)) for value in values) <= 1.5:
        values = [int(float(value) * 32767) for value in values]
    pcm = array("h", [max(-32768, min(32767, int(value))) for value in values])
    if sys.byteorder != "little":
        pcm.byteswap()
    return pcm.tobytes()


def main():
    parser = argparse.ArgumentParser(description="Render SalamanderGrandPiano-V3 chromatic WAV samples for MaixCAM2 piano mode.")
    parser.add_argument("--sf2", default=DEFAULT_SF2)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--gain", type=float, default=DEFAULT_GAIN)
    args = parser.parse_args()
    render_all(
        Path(args.sf2).resolve(),
        Path(args.output_dir).resolve(),
        sample_rate=args.sample_rate,
        gain=args.gain,
    )


if __name__ == "__main__":
    main()

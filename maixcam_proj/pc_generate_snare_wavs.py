import argparse
from array import array
from dataclasses import dataclass
from pathlib import Path
import sys
import wave


DEFAULT_SF2 = "../pc_runtime/instruments/drums/Shino Drums(sf2)/02_Shino_Snare.sf2"
DEFAULT_OUTPUT_DIR = "../pc_runtime/instruments/drums/Shino Drums(sf2)/snare_samples"
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_GAIN = 5.4
SNARE_BANK = 0
SNARE_PRESET = 2
SNARE_MIDI_NOTE = 40
RELEASE_MS = 180


@dataclass(frozen=True)
class RenderPlan:
    name: str
    filename: str
    velocity: int
    duration_ms: int


def build_render_plan():
    return [
        RenderPlan("ghost", "ghost.wav", 42, 420),
        RenderPlan("normal", "normal.wav", 88, 520),
        RenderPlan("accent", "accent.wav", 124, 680),
    ]


def render_all(soundfont_path, output_dir, sample_rate=DEFAULT_SAMPLE_RATE, gain=DEFAULT_GAIN):
    import fluidsynth

    soundfont_path = Path(soundfont_path)
    output_dir = Path(output_dir)
    if not soundfont_path.exists():
        raise FileNotFoundError(f"snare soundfont not found: {soundfont_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    synth = fluidsynth.Synth(samplerate=sample_rate, gain=gain)
    try:
        sfid = synth.sfload(str(soundfont_path))
        synth.program_select(0, sfid, SNARE_BANK, SNARE_PRESET)
        for plan in build_render_plan():
            wav_path = output_dir / plan.filename
            audio = render_snare(synth, plan, sample_rate)
            write_wav(wav_path, audio, sample_rate)
            print(f"wrote {wav_path}")
    finally:
        synth.delete()


def render_snare(synth, plan, sample_rate):
    sustain_frames = _ms_to_frames(plan.duration_ms, sample_rate)
    release_frames = _ms_to_frames(RELEASE_MS, sample_rate)
    synth.noteon(0, SNARE_MIDI_NOTE, plan.velocity)
    audio = _samples_to_bytes(synth.get_samples(sustain_frames))
    synth.noteoff(0, SNARE_MIDI_NOTE)
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
    parser = argparse.ArgumentParser(description="Render Shino snare ghost/normal/accent WAV samples.")
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

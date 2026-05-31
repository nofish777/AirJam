import argparse
from array import array
from dataclasses import dataclass
from pathlib import Path
import sys
import wave


DEFAULT_ELECTRIC_GUITAR_SF2 = "../pc_runtime/instruments/guitars/Bread Breads Distortion Guitar/Bread Breads Distortion Guitar v2.1.sf2"
DEFAULT_ACOUSTIC_GUITAR_SF2 = "../pc_runtime/instruments/guitars/acoustic_guitar/FSS-SteelStringGuitar-20200521.sf2"
DEFAULT_ELECTRIC_OUTPUT_DIR = "../pc_runtime/instruments/guitars/Bread Breads Distortion Guitar/strums"
DEFAULT_ACOUSTIC_OUTPUT_DIR = "../pc_runtime/instruments/guitars/acoustic_guitar/strums"
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_GAIN = 0.85
DEFAULT_VELOCITY = 112

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


@dataclass(frozen=True)
class RenderPlan:
    instrument: str
    chord: str
    direction: str
    notes: list
    velocities: list
    gap_ms: int
    sustain_ms: int
    release_ms: int
    filename: str


def build_render_plan(instrument):
    chords = _chords_for_instrument(instrument)
    plans = []
    for chord, notes in chords.items():
        plans.append(_plan_for_direction(instrument, chord, notes, "down"))
        plans.append(_plan_for_direction(instrument, chord, notes, "up"))
    return plans


def render_all(
    instrument,
    soundfont_path,
    output_dir,
    sample_rate=DEFAULT_SAMPLE_RATE,
    gain=DEFAULT_GAIN,
    velocity=DEFAULT_VELOCITY,
):
    import fluidsynth

    soundfont_path = Path(soundfont_path)
    output_dir = Path(output_dir)
    if not soundfont_path.exists():
        raise FileNotFoundError(f"{instrument} soundfont not found: {soundfont_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    synth = fluidsynth.Synth(samplerate=sample_rate, gain=gain)
    try:
        sfid = synth.sfload(str(soundfont_path))
        synth.program_select(0, sfid, 0, 0)
        for plan in build_render_plan(instrument):
            wav_path = output_dir / plan.filename
            audio = render_strum(synth, plan, sample_rate, velocity)
            write_wav(wav_path, audio, sample_rate)
            print(f"wrote {wav_path}")
    finally:
        synth.delete()


def render_strum(synth, plan, sample_rate, velocity=DEFAULT_VELOCITY):
    chunks = []
    active = []
    gap_frames = _ms_to_frames(plan.gap_ms, sample_rate)
    sustain_frames = _ms_to_frames(plan.sustain_ms, sample_rate)
    release_frames = _ms_to_frames(plan.release_ms, sample_rate)

    for midi, relative_velocity in zip(plan.notes, plan.velocities):
        synth.noteon(0, midi, max(1, min(127, int(relative_velocity * velocity / DEFAULT_VELOCITY))))
        active.append(midi)
        chunks.append(_samples_to_bytes(synth.get_samples(gap_frames)))
    chunks.append(_samples_to_bytes(synth.get_samples(sustain_frames)))

    for midi in active:
        synth.noteoff(0, midi)
    chunks.append(_samples_to_bytes(synth.get_samples(release_frames)))
    return b"".join(chunks)


def write_wav(path, pcm_bytes, sample_rate):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm_bytes)


def _plan_for_direction(instrument, chord, notes, direction):
    if direction == "down":
        return RenderPlan(
            instrument,
            chord,
            "down",
            list(notes),
            _fit_velocity_curve([127, 118, 110, 104, 98, 92], len(notes)),
            26 if instrument == "electric_guitar" else 28,
            620 if instrument == "electric_guitar" else 850,
            160 if instrument == "electric_guitar" else 220,
            f"{chord}_down.wav",
        )

    return RenderPlan(
        instrument,
        chord,
        "up",
        list(reversed(notes)),
        _fit_velocity_curve([98, 108, 88, 78, 68, 58], len(notes)),
        14 if instrument == "electric_guitar" else 16,
        430 if instrument == "electric_guitar" else 620,
        120 if instrument == "electric_guitar" else 170,
        f"{chord}_up.wav",
    )


def _fit_velocity_curve(curve, count):
    if count <= len(curve):
        return curve[:count]
    return curve + [curve[-1]] * (count - len(curve))


def _chords_for_instrument(instrument):
    if instrument == "electric_guitar":
        return ELECTRIC_GUITAR_CHORDS
    if instrument == "acoustic_guitar":
        return ACOUSTIC_GUITAR_CHORDS
    raise ValueError(f"unknown guitar instrument: {instrument}")


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
    parser = argparse.ArgumentParser(description="Render differentiated guitar down/up strum WAV samples from SoundFonts.")
    parser.add_argument("--instrument", choices=["electric_guitar", "acoustic_guitar", "all"], default="all")
    parser.add_argument("--electric-sf2", default=DEFAULT_ELECTRIC_GUITAR_SF2)
    parser.add_argument("--acoustic-sf2", default=DEFAULT_ACOUSTIC_GUITAR_SF2)
    parser.add_argument("--electric-output-dir", default=DEFAULT_ELECTRIC_OUTPUT_DIR)
    parser.add_argument("--acoustic-output-dir", default=DEFAULT_ACOUSTIC_OUTPUT_DIR)
    parser.add_argument("--sample-rate", type=int, default=DEFAULT_SAMPLE_RATE)
    parser.add_argument("--gain", type=float, default=DEFAULT_GAIN)
    parser.add_argument("--velocity", type=int, default=DEFAULT_VELOCITY)
    args = parser.parse_args()

    if args.instrument in ("electric_guitar", "all"):
        render_all(
            "electric_guitar",
            Path(args.electric_sf2).resolve(),
            Path(args.electric_output_dir).resolve(),
            sample_rate=args.sample_rate,
            gain=args.gain,
            velocity=args.velocity,
        )
    if args.instrument in ("acoustic_guitar", "all"):
        render_all(
            "acoustic_guitar",
            Path(args.acoustic_sf2).resolve(),
            Path(args.acoustic_output_dir).resolve(),
            sample_rate=args.sample_rate,
            gain=args.gain,
            velocity=args.velocity,
        )


if __name__ == "__main__":
    main()

from pathlib import Path

from pc_generate_guitar_strum_wavs import (
    ACOUSTIC_GUITAR_CHORDS,
    DEFAULT_ACOUSTIC_GUITAR_SF2 as DEFAULT_SF2,
    DEFAULT_ACOUSTIC_OUTPUT_DIR as DEFAULT_OUTPUT_DIR,
    DEFAULT_GAIN,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_VELOCITY,
    RenderPlan,
    build_render_plan as _build_render_plan,
    main as _main,
    render_all as _render_all,
)


def build_render_plan():
    return _build_render_plan("acoustic_guitar")


def render_all(soundfont_path, output_dir, sample_rate=DEFAULT_SAMPLE_RATE, gain=DEFAULT_GAIN, velocity=DEFAULT_VELOCITY):
    return _render_all(
        "acoustic_guitar",
        Path(soundfont_path),
        Path(output_dir),
        sample_rate=sample_rate,
        gain=gain,
        velocity=velocity,
    )


if __name__ == "__main__":
    _main()

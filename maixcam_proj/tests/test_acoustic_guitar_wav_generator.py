import pc_generate_guitar_strum_wavs as generator


def test_generator_plans_common_acoustic_chord_strum_wavs_with_distinct_directions():
    plans = generator.build_render_plan("acoustic_guitar")

    assert [plan.chord for plan in plans] == [
        "C",
        "C",
        "G",
        "G",
        "Am",
        "Am",
        "F",
        "F",
        "D",
        "D",
        "Em",
        "Em",
        "A",
        "A",
        "E",
        "E",
    ]
    assert plans[0].direction == "down"
    assert plans[1].direction == "up"
    assert plans[0].filename == "C_down.wav"
    assert plans[0].notes == generator.ACOUSTIC_GUITAR_CHORDS["C"]
    assert plans[1].notes == [64, 60, 55, 52, 48]
    assert plans[0].velocities != plans[1].velocities
    assert plans[0].gap_ms != plans[1].gap_ms


def test_generator_plans_electric_power_chord_strum_wavs_with_distinct_directions():
    plans = generator.build_render_plan("electric_guitar")

    assert [plan.chord for plan in plans[:4]] == ["C5", "C5", "D5", "D5"]
    assert plans[0].filename == "C5_down.wav"
    assert plans[1].filename == "C5_up.wav"
    assert plans[0].notes == generator.ELECTRIC_GUITAR_CHORDS["C5"]
    assert plans[1].notes == [60, 55, 48]
    assert plans[0].velocities == [127, 118, 110]
    assert plans[1].velocities == [98, 108, 88]

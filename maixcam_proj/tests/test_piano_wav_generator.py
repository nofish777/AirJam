import pc_generate_piano_wavs as generator


def test_generator_plans_five_octaves_of_chromatic_piano_samples():
    plans = generator.build_render_plan()

    assert len(plans) == 60
    assert plans[0].midi == 36
    assert plans[-1].midi == 95
    assert plans[0].filename == "036.wav"
    assert plans[-1].filename == "095.wav"

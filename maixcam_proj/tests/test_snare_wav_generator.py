import pc_generate_snare_wavs as generator


def test_generator_plans_three_shino_snare_velocity_layers():
    plans = generator.build_render_plan()

    assert [plan.name for plan in plans] == ["ghost", "normal", "accent"]
    assert [plan.filename for plan in plans] == ["ghost.wav", "normal.wav", "accent.wav"]
    assert [plan.velocity for plan in plans] == [42, 88, 124]
    assert plans[0].duration_ms < plans[2].duration_ms


def test_generator_defaults_to_triple_snare_gain():
    assert generator.DEFAULT_GAIN == 5.4

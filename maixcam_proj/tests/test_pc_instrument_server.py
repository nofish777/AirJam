import ast
from pathlib import Path


def _source():
    return (Path(__file__).resolve().parents[1] / "pc_instrument_server.py").read_text(encoding="utf-8")


def test_instrument_server_routes_mode_hit_note_and_guitar_chord_messages():
    source = _source()

    assert "parse_mode_event" in source
    assert "parse_drum_hit_event" in source
    assert "parse_instrument_note_event" in source
    assert "parse_guitar_chord_event" in source
    assert "DEFAULT_ELECTRIC_GUITAR_SF2" in source
    assert "DEFAULT_ACOUSTIC_GUITAR_SF2" in source
    assert "InstrumentSynthServer" in source


def test_instrument_server_defaults_to_shared_instruments_paths():
    tree = ast.parse(_source())
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"DEFAULT_DRUM_SF2", "DEFAULT_DRUM_SAMPLE_DIR", "DEFAULT_GM_SF2", "DEFAULT_PIANO_SAMPLE_DIR", "DEFAULT_ELECTRIC_GUITAR_SF2", "DEFAULT_ACOUSTIC_GUITAR_SF2", "DEFAULT_ELECTRIC_GUITAR_SAMPLE_DIR", "DEFAULT_ACOUSTIC_GUITAR_SAMPLE_DIR", "DEFAULT_PORT"}:
                    assignments[target.id] = ast.literal_eval(node.value)

    assert assignments["DEFAULT_DRUM_SF2"] == "../pc_runtime/instruments/drums/Shino Drums(sf2)/02_Shino_Snare.sf2"
    assert assignments["DEFAULT_DRUM_SAMPLE_DIR"] == "../pc_runtime/instruments/drums/Shino Drums(sf2)/snare_samples"
    assert assignments["DEFAULT_GM_SF2"] == "../pc_runtime/instruments/pianos/SalamanderGrandPiano-V3/SalamanderGrandPiano-V3+20200602.sf2"
    assert assignments["DEFAULT_PIANO_SAMPLE_DIR"] == "../pc_runtime/instruments/pianos/SalamanderGrandPiano-V3/samples"
    assert assignments["DEFAULT_ELECTRIC_GUITAR_SF2"] == "../pc_runtime/instruments/guitars/Bread Breads Distortion Guitar/Bread Breads Distortion Guitar v2.1.sf2"
    assert assignments["DEFAULT_ACOUSTIC_GUITAR_SF2"] == "../pc_runtime/instruments/guitars/acoustic_guitar/FSS-SteelStringGuitar-20200521.sf2"
    assert assignments["DEFAULT_ELECTRIC_GUITAR_SAMPLE_DIR"] == "../pc_runtime/instruments/guitars/Bread Breads Distortion Guitar/strums"
    assert assignments["DEFAULT_ACOUSTIC_GUITAR_SAMPLE_DIR"] == "../pc_runtime/instruments/guitars/acoustic_guitar/strums"
    assert assignments["DEFAULT_PORT"] == 5020


def test_instrument_server_uses_pre_rendered_guitar_strum_wavs():
    source = _source()

    assert "WaveSampleBank" in source
    assert "ELECTRIC_GUITAR_CHORDS" in source
    assert "ACOUSTIC_GUITAR_CHORDS" in source
    assert "electric_guitar_sample_dir" in source
    assert "acoustic_guitar_sample_dir" in source
    assert "_play_electric_guitar_chord" in source
    assert "_play_acoustic_guitar_chord" in source


def test_instrument_server_uses_shino_snare_sample_layers():
    source = _source()

    assert "SNARE_MIDI_NOTE" in source
    assert "SNARE_VELOCITIES" in source
    assert "SnareSampleBank" in source
    assert "drum_sample_dir" in source
    assert "ghost" in source
    assert "accent" in source


def test_instrument_server_uses_pre_rendered_piano_samples():
    source = _source()

    assert "PianoSampleBank" in source
    assert "piano_sample_dir" in source
    assert "_play_piano_note" in source

import ast
from pathlib import Path


def _source():
    return (Path(__file__).resolve().parents[1] / "pc_bread_drum_server.py").read_text(encoding="utf-8")


def test_bread_drum_server_uses_fluidsynth_and_drum_hit_parser():
    source = _source()

    assert "import fluidsynth" in source
    assert "parse_drum_hit_event" in source
    assert "DRUM_MIDI_NOTES" in source


def test_bread_drum_server_defaults_to_bread_soundfont_name_and_port():
    tree = ast.parse(_source())
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"DEFAULT_SF2_PATH", "DEFAULT_PORT"}:
                    assignments[target.id] = ast.literal_eval(node.value)

    assert assignments["DEFAULT_SF2_PATH"] == "../pc_runtime/instruments/drums/bread_breads_drum_kit/Bread Breads Drum Kit1.03.1.sf2"
    assert assignments["DEFAULT_PORT"] == 5020

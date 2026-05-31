import ast
from pathlib import Path


def _server_source():
    return (Path(__file__).resolve().parents[1] / "pc_synth_server.py").read_text(encoding="utf-8")


def test_pc_synth_server_uses_fluidsynth_and_udp_note_parser():
    source = _server_source()

    assert "import fluidsynth" in source
    assert "parse_note_event" in source
    assert "socket.SOCK_DGRAM" in source


def test_pc_synth_server_defaults_to_airpiano_soundfont():
    tree = ast.parse(_server_source())
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"DEFAULT_SF2_PATH", "DEFAULT_PORT"}:
                    assignments[target.id] = ast.literal_eval(node.value)

    assert assignments["DEFAULT_SF2_PATH"] == "../pc_runtime/instruments/pianos/fluid_r3/FluidR3_GM.sf2"
    assert assignments["DEFAULT_PORT"] == 5010

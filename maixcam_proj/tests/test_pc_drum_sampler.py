import ast
from pathlib import Path


def _source():
    return (Path(__file__).resolve().parents[1] / "pc_drum_sampler.py").read_text(encoding="utf-8")


def test_pc_drum_sampler_uses_optional_audio_backends_and_drum_hit_parser():
    source = _source()

    assert "import sounddevice as sd" in source
    assert "pygame = None" in source
    assert "parse_drum_hit_event" in source
    assert "socket.SOCK_DGRAM" in source


def test_pc_drum_sampler_defaults_to_udp_5020_and_samples_dir():
    tree = ast.parse(_source())
    assignments = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"DEFAULT_PORT", "DEFAULT_SAMPLE_DIR"}:
                    assignments[target.id] = ast.literal_eval(node.value)

    assert assignments["DEFAULT_PORT"] == 5020
    assert assignments["DEFAULT_SAMPLE_DIR"] == "../pc_runtime/instruments/samples/drums"

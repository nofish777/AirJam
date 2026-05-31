import ast
from pathlib import Path


def _demo_tree():
    demo_path = Path(__file__).resolve().parents[1] / "piano_demo.py"
    return ast.parse(demo_path.read_text(encoding="utf-8"))


def test_piano_demo_imports_maix_audio_for_official_pcm_player():
    tree = _demo_tree()
    maix_imports = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "maix"
        for alias in node.names
    ]

    assert "audio" in maix_imports


def test_piano_demo_uses_hand_model_without_face_model():
    source = (Path(__file__).resolve().parents[1] / "piano_demo.py").read_text(encoding="utf-8")

    assert "/root/models/hand_landmarks.mud" in source
    assert "YOLO11" not in source
    assert "Retinaface" not in source


def test_piano_demo_uses_pcm_tone_player():
    tree = _demo_tree()
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]

    assert "PcmTonePlayer" in calls


def test_main_app_entry_does_not_switch_to_piano_demo_after_gimbal_lock():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")

    assert "from piano_demo import PianoDemo" not in source
    assert "PianoDemo().run()" not in source


def test_main_app_sends_locked_drum_hits_to_pc_sampler():
    source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")

    assert "InstrumentSelectionController" in source
    assert "UdpInstrumentOutput" in source
    assert "GuitarModeController" in source
    assert "NumericGestureRecognizer" in source
    assert "SnareDrumController" in source
    assert "DrumZoneController" not in source
    assert "__draw_drum_regions" not in source
    assert "UdpInstrumentOutput(PC_SYNTH_HOST, PC_DRUM_PORT)" in source
    assert "set_mode(selection.instrument)" in source
    assert "play_hit" in source
    assert "play_guitar_chord" in source
    assert "electric_guitar" in source
    assert "acoustic_guitar" in source
    assert "from maix import image, camera, display, time, nn, touchscreen, sys, app, audio" not in source


def test_piano_keys_are_drawn_above_bottom_hud():
    source = (Path(__file__).resolve().parents[1] / "piano_demo.py").read_text(encoding="utf-8")

    assert "key_y = HEIGHT - hud_height - key_height" in source
    assert "create_piano_layout(WIDTH, HEIGHT, key_height=key_height, y=key_y)" in source

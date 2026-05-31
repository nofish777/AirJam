from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


class _FakeFlipDir:
    Y = "horizontal"


class _FakeImageModule:
    FlipDir = _FakeFlipDir


class _FakeFrame:
    def __init__(self):
        self.flip_calls = []

    def flip(self, direction):
        self.flip_calls.append(direction)
        return "mirrored-frame"


def test_mirror_camera_frame_flips_horizontally():
    from face_tracking.frame_ops import mirror_camera_frame

    frame = _FakeFrame()

    mirrored = mirror_camera_frame(frame, _FakeImageModule)

    assert mirrored == "mirrored-frame"
    assert frame.flip_calls == [_FakeFlipDir.Y]


def test_main_and_piano_demo_mirror_frames_after_camera_read():
    main_source = (PROJECT_DIR / "main.py").read_text(encoding="utf-8")
    demo_source = (PROJECT_DIR / "piano_demo.py").read_text(encoding="utf-8")

    assert "from face_tracking.frame_ops import mirror_camera_frame" in main_source
    assert "from face_tracking.frame_ops import mirror_camera_frame" in demo_source
    assert "img = mirror_camera_frame(self.cam.read(), image)" in main_source
    assert "img = mirror_camera_frame(self.cam.read(), image)" in demo_source


def test_main_mirrors_left_right_hand_roles_with_camera_frame():
    main_source = (PROJECT_DIR / "main.py").read_text(encoding="utf-8")

    assert "is_right_hand(obj, getattr(self.hand_detector, \"labels\", None), mirrored=True)" in main_source

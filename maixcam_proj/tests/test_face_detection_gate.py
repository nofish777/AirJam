import sys
import types


def _install_fake_maix():
    maix = types.ModuleType("maix")
    maix.image = types.SimpleNamespace(
        load=lambda path: None,
        FlipDir=types.SimpleNamespace(Y="horizontal"),
    )
    maix.camera = types.SimpleNamespace(Camera=lambda w, h: None)
    maix.display = types.SimpleNamespace(Display=lambda: None)
    maix.time = types.SimpleNamespace(ticks_ms=lambda: 0)
    maix.nn = types.SimpleNamespace(YOLO11=object, Retinaface=object, HandLandmarks=object)
    maix.touchscreen = types.SimpleNamespace(TouchScreen=lambda: None)
    maix.sys = types.SimpleNamespace(device_name=lambda: "maixcam2")
    maix.app = types.SimpleNamespace(need_exit=lambda: False)
    maix.pwm = types.SimpleNamespace(PWM=object)
    maix.pinmap = types.SimpleNamespace(get_pins=lambda: [], get_pin_functions=lambda pin: [])
    maix.audio = types.SimpleNamespace()
    sys.modules["maix"] = maix


class _FakeDetector:
    def detect(self, img, conf_th=0.4, iou_th=0.45):
        raise AssertionError("face detector should not run after tracking is locked")


class _FakeCamera:
    def read(self):
        return _FakeFrame()


class _FakeFrame:
    def flip(self, direction):
        return self


class _FakeDisplay:
    def show(self, img):
        pass


def test_target_can_skip_face_detector_when_only_gestures_are_needed():
    _install_fake_maix()
    from main import Target

    target = object.__new__(Target)
    target.w = 320
    target.h = 240
    target.out_range = 10
    target.ignore = 0.08
    target.pitch = 0
    target.roll = 0
    target.detector = _FakeDetector()
    target.cam = _FakeCamera()
    target.disp = _FakeDisplay()
    target._Target__get_gesture = lambda img: "ok"
    target._Target__exit_listener = lambda img: None

    pitch, roll, face_visible, gesture = Target.get_target_err(target, track_faces=False)

    assert pitch == 0
    assert roll == 0
    assert face_visible is False
    assert gesture == "ok"

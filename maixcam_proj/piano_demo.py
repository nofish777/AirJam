from face_tracking.gestures import GestureRecognizer
from face_tracking.frame_ops import mirror_camera_frame
from face_tracking.piano import (
    PcmTonePlayer,
    PianoGesturePlayer,
    active_fingertips,
    create_piano_layout,
    midi_to_name,
)
from maix import app, audio, camera, display, image, nn, sys, time, touchscreen


HAND_MODEL = "/root/models/hand_landmarks.mud"
WIDTH = 320
HEIGHT = 240
FINGER_NAMES = ("Index", "Middle", "Ring")
INSTRUMENT_NAME = "Piano Demo"


class PianoDemo:
    def __init__(self):
        self.hand_detector = nn.HandLandmarks(model=HAND_MODEL)
        self.gesture_recognizer = GestureRecognizer()
        self.cam = camera.Camera(WIDTH, HEIGHT)
        self.disp = display.Display()
        self.tone_player = PcmTonePlayer(audio_module=audio, duration_ms=150)
        hud_height = 44
        key_height = 86
        key_y = HEIGHT - hud_height - key_height
        white_keys, black_keys = create_piano_layout(WIDTH, HEIGHT, key_height=key_height, y=key_y)
        self.piano = PianoGesturePlayer(white_keys, black_keys, debounce_frames=1, release_frames=2)
        self.ts = touchscreen.TouchScreen()
        self.img_exit = image.load("./assets/exit.jpg").resize(40, 40)
        self.img_exit_touch = image.load("./assets/exit_touch.jpg").resize(40, 40)
        self.exit_box = [0, 0, self.img_exit.width(), self.img_exit.height()]
        self.need_exit = False
        self.last_notes = []
        self.last_gesture = None

    def run(self):
        while not self.need_exit and not app.need_exit():
            start_ms = time.ticks_ms()
            img = mirror_camera_frame(self.cam.read(), image)
            points, gesture = self._read_hand(img)
            frame = self.piano.update(points)

            for midi in frame.notes_on:
                self.tone_player.play_midi(midi)
            if frame.notes_on:
                self.last_notes = [midi_to_name(midi) for midi in frame.notes_on]
            self.last_gesture = gesture

            self._draw_piano(img, frame.active_midi)
            self._draw_hud(img, frame.active_midi)
            self._exit_listener(img)
            self.disp.show(img)
            used_ms = max(1, time.ticks_ms() - start_ms)
            print(
                f"used time:{used_ms}ms, fps:{round(1000 / used_ms, 2)}, "
                f"gesture:{gesture}, notes:{self.last_notes}"
            )

    def _read_hand(self, img):
        hand_objs = self.hand_detector.detect(img, conf_th=0.7, iou_th=0.45, conf_th2=0.8)
        fingertip_points = []
        gesture = None
        for obj in hand_objs:
            self.hand_detector.draw_hand(img, obj.class_id, obj.points, 4, 10, box=True)
            landmarks = obj.points[8:8 + 21 * 3]
            if gesture is None:
                gesture = self.gesture_recognizer.classify(landmarks)
            fingertip_points.extend(active_fingertips(landmarks, FINGER_NAMES))
        return fingertip_points, gesture

    def _draw_piano(self, img, active_midi):
        active = set(active_midi)
        for key in self.piano.white_keys:
            color = image.COLOR_YELLOW if key.midi in active else image.COLOR_WHITE
            img.draw_rect(key.x, key.y, key.w, key.h, color, -1)
            img.draw_rect(key.x, key.y, key.w, key.h, image.COLOR_BLACK, 1)
            img.draw_string(key.x + 2, key.y + key.h - 16, key.name, image.COLOR_BLACK)

        for key in self.piano.black_keys:
            color = image.COLOR_RED if key.midi in active else image.COLOR_BLACK
            img.draw_rect(key.x, key.y, key.w, key.h, color, -1)

    def _draw_hud(self, img, active_midi):
        notes = ", ".join(midi_to_name(midi) for midi in active_midi) or ", ".join(self.last_notes) or "-"
        img.draw_rect(0, HEIGHT - 44, WIDTH, 44, image.COLOR_BLACK, -1)
        img.draw_string(46, HEIGHT - 40, f"{INSTRUMENT_NAME}", image.COLOR_WHITE)
        img.draw_string(46, HEIGHT - 24, f"Note: {notes}", image.COLOR_WHITE)

    def _exit_listener(self, img):
        touch = self.ts.read()
        if self._touch_in_box(touch, self.exit_box, 20):
            img.draw_image(self.exit_box[0], self.exit_box[1], self.img_exit_touch)
            self.need_exit = True
        else:
            img.draw_image(self.exit_box[0], self.exit_box[1], self.img_exit)

    def _touch_in_box(self, touch, box, offset=0):
        return (
            touch[2]
            and touch[0] + offset > box[0]
            and touch[0] < box[0] + box[2] + offset
            and touch[1] + offset > box[1]
            and touch[1] < box[1] + box[3] + offset
        )


if __name__ == "__main__":
    print(f"device:{sys.device_name()}, running {INSTRUMENT_NAME}")
    PianoDemo().run()

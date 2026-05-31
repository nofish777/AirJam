from face_tracking import servos
from face_tracking.air_drum import SnareDrumController, hand_center
from face_tracking.gestures import GestureName, GestureRecognizer, GestureTrackingController, TrackingMode, hand_covers_face
from face_tracking.frame_ops import mirror_camera_frame
from face_tracking.guitar import ACOUSTIC_GUITAR_CHORDS, GuitarModeController
from face_tracking.instrument_select import InstrumentReturnController, InstrumentSelectionController, default_instrument_zones
from face_tracking.note_output import UdpInstrumentOutput
from face_tracking.piano import PianoModeController
from face_tracking.scale_gestures import NumericGestureRecognizer, is_right_hand
from maix import image, camera, display, time, nn, touchscreen, sys, app

### model path
if sys.device_name().lower() == "maixcam2":
    MODEL = "/root/models/yolo11s_face.mud"
else:
    MODEL = "/root/models/retinaface.mud"

HAND_MODEL = "/root/models/hand_landmarks.mud"
OK_PITCH_DROP = 8.34
INDEX_DOWN_PITCH_STEP = 0.8
PC_SYNTH_HOST = "10.183.31.100"
PC_DRUM_PORT = 5020


class Target:
    """Obtain the error value between the target and the center point.
       Need to modify __init__() and __get_target().
    Args:
        out_range (float): output range
        ignore_limit (float): dead zone
        path (str): model path
    """
    def __init__(self, out_range:float, ignore_limit:float, path:str, hand_path:str):
        """Constructor
            Initialization of the recognition model class or other classes needs to be implemented here.
        """
        self.pitch = 0
        self.roll = 0
        self.out_range = out_range
        self.ignore = ignore_limit

        ### Self.w and self.h must be initialized.
        if sys.device_name().lower() == "maixcam2":
            self.detector = nn.YOLO11(model=path)
            self.hand_detector = nn.HandLandmarks(model=hand_path)
        else:
            self.detector = nn.Retinaface(model=path)
            self.hand_detector = None
        self.gesture_recognizer = GestureRecognizer()
        self.numeric_gesture_recognizer = NumericGestureRecognizer()
        self.w = self.detector.input_width()
        self.h = self.detector.input_height()
        self.snare_controller = SnareDrumController()
        self.instrument_zones = default_instrument_zones(self.w, self.h)
        self.instrument_selector = InstrumentSelectionController(self.instrument_zones)
        self.instrument_return_controller = InstrumentReturnController()
        self.selected_instrument = None
        self.pending_selection = None
        self.piano_controller = PianoModeController(self.w, self.h - 48)
        self.guitar_controller = GuitarModeController()
        self.acoustic_guitar_controller = GuitarModeController(chords=ACOUSTIC_GUITAR_CHORDS)
        self.last_note_midi = None
        self.last_guitar_chord = None
        self.last_guitar_strum = None
        self.last_hand_visible = False
        self.face_recent_until_ms = 0
        self.drum_mode_enabled = False
        self.last_drum_hit = None
        self.last_drum_trigger_time_ms = None
        self.last_hand_center = None
        self.cam = camera.Camera(self.w, self.h)
        self.disp = display.Display()

        ### The following section is used as an opt-out and normally you do not need to modify it.
        self.ts = touchscreen.TouchScreen()
        self.img_exit = image.load("./assets/exit.jpg").resize(40, 40)
        self.img_exit_touch = image.load("./assets/exit_touch.jpg").resize(40, 40)
        self.box = [0, 0, self.img_exit.width(), self.img_exit.height()]
        self.need_exit = False

    def __return_to_instrument_selection(self):
        self.selected_instrument = None
        self.pending_selection = None
        self.instrument_selector.reset()
        self.instrument_return_controller.reset()
        self.snare_controller = SnareDrumController()
        self.piano_controller = PianoModeController(self.w, self.h - 48)
        self.guitar_controller = GuitarModeController()
        self.acoustic_guitar_controller = GuitarModeController(chords=ACOUSTIC_GUITAR_CHORDS)
        self.last_note_midi = None
        self.last_guitar_chord = None
        self.last_guitar_strum = None
        self.last_drum_hit = None
        self.last_drum_trigger_time_ms = None

    def __check_touch_box(self, t, box, oft = 0):
        """This method is used for exiting and you normally do not need to modify or call it.
            You usually don't need to modify it.
        """
        if t[2] and t[0] + oft > box[0] and t[0] < box[0] + box[2] + oft and t[1] + oft > box[1] and t[1] < box[1] + box[3] + oft:
            return True
        else:
            return False

    def __exit_listener(self, img):
        """Exit case detection methods.
            It also draws the Exit button in the upper left corner.
            You usually don't need to modify it.

        Args:
            img (image.Image): The image that needs to be drawn.
        """
        t = self.ts.read()
        if self.__check_touch_box(t, self.box, 20):
            img.draw_image(self.box[0], self.box[1], self.img_exit_touch)
            self.need_exit = True
        else:
            img.draw_image(self.box[0], self.box[1], self.img_exit)

    def is_need_exit(self):
        """Queries whether the exit button has been pressed.
            You usually don't need to modify it.

        Returns:
            bool: Returns true if the exit button has been pressed, false otherwise.
        """
        return self.need_exit

    def __get_target(self, track_faces=True):
        """Get the coordinate value of the target.
            The behavior of this function needs to be customized.
        Returns:
            int, int, str|None: If no face is found, return -1,-1 plus any gesture.
                                If the face is found, return face center x,y plus any gesture.
        """
        ltime = time.ticks_ms()
        img = mirror_camera_frame(self.cam.read(), image)               # Reads an image frame.
        self.drum_mode_enabled = not track_faces
        cent_x, cent_y = -1, -1
        if track_faces:
            objs = self.detector.detect(img, conf_th = 0.4, iou_th = 0.45)  # Recognition.
            face_boxes = []
            for obj in objs:                    # Find objects.
                face_boxes.append((obj.x, obj.y, obj.w, obj.h))
                img.draw_rect(obj.x, obj.y, obj.w, obj.h, image.COLOR_RED, 2)
                if cent_x == -1:
                    cent_x = obj.x + round(obj.w/2) # Calculate the x-coordinate of the target center point.
                    cent_y = obj.y + round(obj.h/2) # Calculate the y-coordinate of the target center point.
                    img.draw_rect(cent_x-1, cent_y-1, 2, 2, image.COLOR_GREEN)
            if cent_x != -1:
                self.face_recent_until_ms = ltime + 800

        else:
            face_boxes = []

        self.current_face_boxes = face_boxes if track_faces else None
        gesture = self.__get_gesture(img)
        if (
            track_faces
            and cent_x == -1
            and self.last_hand_visible
            and ltime <= getattr(self, "face_recent_until_ms", 0)
        ):
            gesture = GestureName.FACE_COVERED
        rtime = time.ticks_ms()
        # print(f"find target used time:{round(rtime-ltime,2)}ms")
        self.__draw_status(img)
        self.__exit_listener(img)
        self.disp.show(img)
        return cent_x, cent_y, gesture

    def __get_gesture(self, img):
        if not self.hand_detector:
            return None
        hand_objs = self.hand_detector.detect(img, conf_th=0.7, iou_th=0.45, conf_th2=0.8)
        self.last_hand_visible = bool(hand_objs)
        gesture = None
        self.last_drum_hit = None
        self.last_hand_center = None
        self.last_note_midi = None
        self.last_guitar_strum = None
        face_boxes = getattr(self, "current_face_boxes", None)
        detected_hands = []
        for obj in hand_objs:
            self.hand_detector.draw_hand(img, obj.class_id, obj.points, 4, 10, box=True)
            landmarks = obj.points[8:8 + 21 * 3]
            detected_hands.append((obj, landmarks))
            if face_boxes:
                for face_box in face_boxes:
                    if hand_covers_face(landmarks, face_box):
                        gesture = GestureName.FACE_COVERED
                        break

        if self.drum_mode_enabled:
            now_ms = time.ticks_ms()
            return_hands = [(obj.class_id, landmarks) for obj, landmarks in detected_hands]
            if self.selected_instrument and self.instrument_return_controller.update(return_hands, now_ms):
                self.__return_to_instrument_selection()
            else:
                for obj, landmarks in detected_hands:
                    try:
                        self.last_hand_center = hand_center(landmarks)
                        if self.selected_instrument is None:
                            selection = self.instrument_selector.update(landmarks, now_ms)
                            if selection:
                                self.pending_selection = selection
                                self.selected_instrument = selection.instrument
                        elif self.selected_instrument == "drums":
                            hit = self.snare_controller.update(landmarks, now_ms, hand_id=obj.class_id)
                            if hit:
                                self.last_drum_hit = hit
                                self.last_drum_trigger_time_ms = now_ms
                        elif self.selected_instrument == "piano":
                            is_right = is_right_hand(obj, getattr(self.hand_detector, "labels", None), mirrored=True)
                            if is_right:
                                self.last_note_midi = self.piano_controller.update_right(landmarks, now_ms)
                            else:
                                number = self.numeric_gesture_recognizer.classify(landmarks)
                                self.piano_controller.update_left(number)
                        elif self.selected_instrument in ("electric_guitar", "acoustic_guitar"):
                            guitar_controller = (
                                self.acoustic_guitar_controller
                                if self.selected_instrument == "acoustic_guitar"
                                else self.guitar_controller
                            )
                            is_right = is_right_hand(obj, getattr(self.hand_detector, "labels", None), mirrored=True)
                            if is_right:
                                self.last_guitar_strum = guitar_controller.update_right(landmarks, now_ms)
                            else:
                                number = self.numeric_gesture_recognizer.classify(landmarks)
                                chord = guitar_controller.update_left(number)
                                if chord:
                                    self.last_guitar_chord = chord
                    except Exception as exc:
                        print(f"instrument update error: {exc}")

        for obj, landmarks in detected_hands:
            if gesture is None:
                try:
                    gesture = self.gesture_recognizer.classify(landmarks)
                except Exception as exc:
                    print(f"gesture update error: {exc}")
        return gesture

    def __draw_status(self, img):
        if not getattr(self, "drum_mode_enabled", False):
            return
        if not hasattr(self, "snare_controller"):
            return
        now = time.ticks_ms()
        hand = getattr(self, "last_hand_center", None)
        if hand:
            img.draw_circle(hand[0], hand[1], 4, image.COLOR_RED, -1)
        if self.selected_instrument is None:
            self.__draw_instrument_zones(img)
            return
        if self.selected_instrument == "piano":
            self.__draw_piano_keyboard(img)
        hit = getattr(self, "last_drum_hit", None) or getattr(self.snare_controller, "last_hit", None)
        img.draw_rect(0, self.h - 48, self.w, 48, image.COLOR_BLACK, -1)
        drum = hit.drum if hit else "-"
        articulation = hit.articulation if hit else "-"
        velocity = hit.velocity if hit else "-"
        trigger_time = getattr(self, "last_drum_trigger_time_ms", None) or "-"
        if self.selected_instrument == "drums":
            img.draw_string(8, self.h - 42, "Instrument: Pearl Snare", image.COLOR_WHITE)
            img.draw_string(8, self.h - 24, f"Stroke:{velocity} Power:{hit.power if hit else '-'} T:{trigger_time}", image.COLOR_WHITE)
        else:
            img.draw_string(8, self.h - 42, f"Instrument: {self.selected_instrument}", image.COLOR_WHITE)
            if self.selected_instrument in ("electric_guitar", "acoustic_guitar"):
                direction = self.last_guitar_strum.direction if self.last_guitar_strum else "-"
                img.draw_string(8, self.h - 24, f"Chord:{self.last_guitar_chord or '-'} Strum:{direction}", image.COLOR_WHITE)
            else:
                img.draw_string(
                    8,
                    self.h - 24,
                    f"Oct:{self.piano_controller.selected_octave} Note:{self.last_note_midi or '-'}",
                    image.COLOR_WHITE,
                )

    def __draw_instrument_zones(self, img):
        hover = getattr(self.instrument_selector, "hover_instrument", None)
        for zone in self.instrument_zones:
            color = image.COLOR_YELLOW if zone.name == hover else image.COLOR_WHITE
            img.draw_rect(zone.x, zone.y, zone.w, zone.h, color, 2)
            number = self.instrument_zones.index(zone) + 1
            img.draw_string(zone.x + 8, zone.y + 12, f"{number}. {zone.name}", color)
        img.draw_rect(0, self.h - 48, self.w, 48, image.COLOR_BLACK, -1)
        img.draw_string(8, self.h - 42, "Select: 1 drums | 2 electric | 3 acoustic | 4 piano", image.COLOR_WHITE)
        img.draw_string(8, self.h - 24, "Move hand into box, show matching number", image.COLOR_WHITE)

    def __draw_melodic_regions(self, img, instrument):
        count = 7 if instrument == "piano" else 8
        region_w = self.w // count
        for index in range(count):
            x = index * region_w
            w = self.w - x if index == count - 1 else region_w
            img.draw_rect(x, 0, w, self.h - 48, image.COLOR_WHITE, 1)
            img.draw_string(x + 4, 8, str(index + 1), image.COLOR_WHITE)

    def __draw_piano_keyboard(self, img):
        layout = self.piano_controller.layout
        for key in layout.white_keys:
            img.draw_rect(key.x, key.y, key.w, key.h, image.COLOR_WHITE, 1)
            img.draw_string(key.x + 4, key.y + key.h - 20, key.degree, image.COLOR_WHITE)
        for key in layout.black_keys:
            img.draw_rect(key.x, key.y, key.w, key.h, image.COLOR_BLACK, -1)
            img.draw_rect(key.x, key.y, key.w, key.h, image.COLOR_WHITE, 1)
            img.draw_string(key.x + 2, key.y + key.h - 18, key.degree, image.COLOR_WHITE)

    def get_target_err(self, track_faces=True):
        """Obtain the error value between the target and the center point.
            You usually don't need to modify it.

        Returns:
            int, int, bool, str|None: y-axis error value, x-axis error value, face visible, gesture.
        """
        cent_x, cent_y, gesture = self.__get_target(track_faces=track_faces)
        if cent_x == -1:
            return (0, 0, False, gesture)
        self.pitch = cent_y / self.h * self.out_range * 2 - self.out_range
        self.roll = cent_x / self.w * self.out_range * 2 - self.out_range
        if abs(self.pitch) < self.out_range*self.ignore:
            self.pitch = 0
        if abs(self.roll) < self.out_range*self.ignore:
            self.roll = 0
        return self.pitch, self.roll, True, gesture


if __name__ == '__main__':
    PITCH_PWM_PIN_NAME = "B2"
    ROLL_PWM_PIN_NAME = "B3"
    init_pitch = 71.67          # 15 degrees higher than 80, value: [0, 100]
    init_roll = 50              # 50 means middle
    PITCH_DUTY_MIN  = 3.5       # The minimum duty cycle corresponding to the range of motion of the y-axis servo.
    PITCH_DUTY_MAX  = 9.5       # Maximum duty cycle corresponding to the y-axis servo motion range.
    ROLL_DUTY_MIN   = 2.5       # Minimum duty cycle for x-axis servos.
    ROLL_DUTY_MAX   = 12.5      # Maxmum duty cycle for x-axis servos.

    pitch_pid = [0.15, 0.00005, 0.0009, 0]  # [P I D I_max], half speed for smoother tracking
    roll_pid  = [0.15, 0.00005, 0.0009, 0]  # [P I D I_max], half speed for smoother tracking
    target_err_range = 10                   # target error output range, default [0, 10]
    target_ignore_limit = 0.08              # when target error < target_err_range*target_ignore_limit , set target error to 0
    pitch_reverse = False                   # reverse out value direction
    roll_reverse = False                    # reverse out value direction

    target = Target(target_err_range, target_ignore_limit, MODEL, HAND_MODEL)
    try:
        roll = servos.Servos(ROLL_PWM_PIN_NAME, init_roll, ROLL_DUTY_MIN, ROLL_DUTY_MAX)
        pitch = servos.Servos(PITCH_PWM_PIN_NAME, init_pitch, PITCH_DUTY_MIN, PITCH_DUTY_MAX)
    except RuntimeError as e:
        print(f"!!!!!!!!!!!!!!!! ERROR: {e} !!!!!!!!!!!!!!!!!!!!!!")
        wait_time_s = 10
        while wait_time_s:
            eimg = image.Image(target.w, target.h)
            eimg.draw_string(10, 10, "Error: "+str(e)+
                             f".   This program will exit after {wait_time_s}s.")
            target.disp.show(eimg)
            time.sleep(1)
            wait_time_s -= 1
        exit(-1)

    pid_pitch = servos.PID(p=pitch_pid[0], i=pitch_pid[1], d=pitch_pid[2], imax=pitch_pid[3])
    pid_roll = servos.PID(p=roll_pid[0], i=roll_pid[1], d=roll_pid[2], imax=roll_pid[3])
    gimbal = servos.Gimbal(pitch, pid_pitch, roll, pid_roll)
    gesture_controller = GestureTrackingController(OK_PITCH_DROP, INDEX_DOWN_PITCH_STEP)
    instrument_output = UdpInstrumentOutput(PC_SYNTH_HOST, PC_DRUM_PORT)

    total_uesd_time = 0
    total_fps = 0
    t0 = time.ticks_ms()
    while not target.is_need_exit() and not app.need_exit():
        ltime = time.ticks_ms()

        # get target error
        track_faces = gesture_controller.mode is not TrackingMode.LOCKED
        err_pitch, err_roll, face_visible, gesture = target.get_target_err(track_faces=track_faces)
        # interval limit to >= 10ms
        if time.ticks_ms() - t0 < 10:
            continue
        t0 = time.ticks_ms()
        gesture_command = gesture_controller.update(gesture, face_visible)
        # run
        if gesture_command.should_track:
            gimbal.run(err_pitch, err_roll, pitch_reverse = pitch_reverse, roll_reverse=roll_reverse)
        else:
            pid_pitch.reset_I()
            pid_roll.reset_I()
            if gesture_command.pitch_delta:
                pitch.drive(gesture_command.pitch_delta)
            if gesture_command.locked:
                selection = target.pending_selection
                if selection:
                    instrument_output.set_mode(selection.instrument)
                    target.pending_selection = None
                if target.selected_instrument == "drums" and target.last_drum_hit:
                    instrument_output.play_hit(
                        target.last_drum_hit.drum,
                        target.last_drum_hit.articulation,
                        target.last_drum_hit.velocity,
                        target.last_drum_hit.power,
                    )
                elif target.selected_instrument in ("electric_guitar", "acoustic_guitar") and target.last_guitar_strum:
                    instrument_output.play_guitar_chord(
                        target.selected_instrument,
                        target.last_guitar_strum.chord,
                        target.last_guitar_strum.direction,
                    )
                elif target.selected_instrument == "piano" and target.last_note_midi:
                    instrument_output.play_note(target.selected_instrument, target.last_note_midi)

        # Calculate FPS.
        rtime = time.ticks_ms()
        utime = rtime-ltime
        total_uesd_time += utime
        total_fps += 1
        print(f"used time:{utime}ms, fps:{round(1000/(utime),2)}, avg_fps:{round(total_fps*1000/total_uesd_time, 2)}, gesture:{gesture}, mode:{gesture_controller.mode.value}")

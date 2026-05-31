import ast
from pathlib import Path


def _main_assignments():
    main_path = Path(__file__).resolve().parents[1] / "main.py"
    tree = ast.parse(main_path.read_text(encoding="utf-8"))
    assignments = {}
    names = {
        "ROLL_PWM_PIN_NAME",
        "PITCH_PWM_PIN_NAME",
        "pitch_reverse",
        "roll_reverse",
        "pitch_pid",
        "roll_pid",
        "init_pitch",
        "HAND_MODEL",
        "OK_PITCH_DROP",
        "INDEX_DOWN_PITCH_STEP",
        "PC_SYNTH_HOST",
        "PC_DRUM_PORT",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    assignments[target.id] = ast.literal_eval(node.value)

    return assignments


def _main_tree():
    main_path = Path(__file__).resolve().parents[1] / "main.py"
    return ast.parse(main_path.read_text(encoding="utf-8"))


def test_servo_direction_matches_camera_error():
    assignments = _main_assignments()

    assert assignments["pitch_reverse"] is False
    assert assignments["roll_reverse"] is False


def test_servo_pwm_pins_match_wiring():
    assignments = _main_assignments()

    assert assignments["PITCH_PWM_PIN_NAME"] == "B2"
    assert assignments["ROLL_PWM_PIN_NAME"] == "B3"


def test_pitch_starts_15_degrees_higher():
    assignments = _main_assignments()

    assert assignments["init_pitch"] == 71.67


def test_servo_speed_is_half_of_default_pid_gain():
    assignments = _main_assignments()

    assert assignments["pitch_pid"] == [0.15, 0.00005, 0.0009, 0]
    assert assignments["roll_pid"] == [0.15, 0.00005, 0.0009, 0]


def test_hand_landmark_model_path_matches_maixpy_default():
    assignments = _main_assignments()

    assert assignments["HAND_MODEL"] == "/root/models/hand_landmarks.mud"


def test_gesture_stop_pitch_steps_are_configured():
    assignments = _main_assignments()

    assert assignments["OK_PITCH_DROP"] == 8.34
    assert assignments["INDEX_DOWN_PITCH_STEP"] == 0.8


def test_pc_synth_udp_target_is_configured():
    assignments = _main_assignments()

    assert assignments["PC_SYNTH_HOST"] == "10.183.31.100"
    assert assignments["PC_DRUM_PORT"] == 5020

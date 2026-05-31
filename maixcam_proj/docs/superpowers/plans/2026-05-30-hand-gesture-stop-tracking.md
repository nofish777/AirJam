# Hand Gesture Stop Tracking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the existing MaixCAM face tracking behavior, add 21-point hand landmark gesture recognition, and permanently stop tracking when OK or index-down commands are seen.

**Architecture:** Add a pure Python module for gesture geometry and tracking-stop state so local tests can validate behavior without Maix hardware. Keep Maix-specific camera, display, detector, and servo code in `main.py`, wiring hand landmarks into the existing frame loop.

**Tech Stack:** Python, MaixPy `nn.HandLandmarks`, existing `servos.PID/Gimbal`, pytest.

---

### Task 1: Gesture Geometry

**Files:**
- Create: `face_tracking/gestures.py`
- Test: `tests/test_gestures.py`

- [ ] Write failing tests for `GestureRecognizer.classify()` returning `"ok"`, `"index_down"`, or `None` from 21 `(x, y, z)` points.
- [ ] Run `pytest tests/test_gestures.py -v` and confirm the tests fail because `face_tracking.gestures` does not exist.
- [ ] Implement a minimal `GestureRecognizer` with finger extension checks and thumb/index pinch checks.
- [ ] Run `pytest tests/test_gestures.py -v` and confirm the tests pass.

### Task 2: Tracking State Machine

**Files:**
- Modify: `face_tracking/gestures.py`
- Test: `tests/test_gesture_tracking_state.py`

- [ ] Write failing tests for state transitions: OK enters permanent lock with one pitch drop, index-down enters lowering, no-face during lowering enters permanent lock, and locked state ignores later gestures.
- [ ] Run `pytest tests/test_gesture_tracking_state.py -v` and confirm expected failures.
- [ ] Implement `TrackingMode`, `GestureCommand`, and `GestureTrackingController`.
- [ ] Run `pytest tests/test_gesture_tracking_state.py -v` and confirm tests pass.

### Task 3: Main Loop Integration

**Files:**
- Modify: `main.py`
- Test: `tests/test_tracking_config.py`

- [ ] Add configuration constants for hand model path, OK pitch drop, and index-down lowering speed.
- [ ] Instantiate `nn.HandLandmarks` on MaixCAM2 and reuse each camera frame for face and hand detection.
- [ ] Draw the 21-point hand skeleton using `draw_hand()` when available.
- [ ] Apply controller actions in the loop: normal tracking runs PID, OK drives pitch down once then locks, index-down drives pitch down until face is absent then locks.
- [ ] Preserve touch exit and existing MaixCAM/non-MaixCAM face model selection.
- [ ] Run `pytest -q` and confirm all local tests pass.

### Task 4: Manual Device Check

**Files:**
- No additional file changes.

- [ ] Deploy to MaixCAM2 with `/root/models/yolo11s_face.mud` and `/root/models/hand_landmarks.mud` present.
- [ ] Confirm normal face tracking still works before any command gesture.
- [ ] Show OK gesture and confirm tracking stops, pitch drops about 10 degrees, and future faces/gestures are ignored.
- [ ] Show index-down gesture and confirm tracking stops, pitch keeps moving downward until no face is detected, then remains locked.

### Plan Review

This covers all requested behavior while keeping the current face-tracking code path. There are no placeholders. This workspace is not a git repository, so commit steps are intentionally omitted.

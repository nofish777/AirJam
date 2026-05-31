def mirror_camera_frame(frame, image_module):
    return frame.flip(image_module.FlipDir.Y)

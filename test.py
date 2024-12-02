
    
from random_video_effect import random_video_effect

image_path = r"3.png"  # Set image path
out_path = "video_screen/caches.mp4"  # Set output path
duration = 10  # Video duration (seconds)
fps = 30  # Frames per second
width = 1920  # Video width
height = 1080  # Video height
# create_parallax_left_video(image_path, out_path, duration, fps, width, height)
# create_parallax_right_video(image_path, out_path, duration, fps, width, height)
# create_scrolling_image_video(image_path, out_path, duration, fps, width, height)
# create_zoom_in_video(image_path, out_path, duration, fps, width, height)
# create_zoom_out_video(image_path, out_path, duration, fps, width, height)
# create_zoom_in_video_with_background(image_path, out_path, duration, fps, width, height)
# create_zoom_out_video_with_background(image_path, out_path, duration, fps, width, height)
random_video_effect(image_path, out_path, duration, fps, width, height)
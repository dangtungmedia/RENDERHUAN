# from random_video_effect import random_video_effect_cython

image_path = "3.png"  # Set image path
out_path = "caches.mp4"  # Set output path
duration = 7.752  # Video duration (seconds)
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
# random_video_effect_cython(image_path, out_path, duration, fps, width, height)


import psutil

# Số lõi logic (bao gồm cả những lõi ảo nếu có Hyper-Threading)
logical_cores = psutil.cpu_count(logical=True)
# Số lõi vật lý
physical_cores = psutil.cpu_count(logical=False)

print(f"Số lõi vật lý: {physical_cores}")
from random_video_effect import random_video_effect_cython
import os
# image_path = "media/95571/image/view-castle-with-nature-landscape_23-2150984811.jpg"  # Set image path
# out_path = "caches.mp4"  # Set output path
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

list_image = os.listdir("image")

for index, image in enumerate(list_image):  # Sử dụng enumerate để lấy cả chỉ số và tên tệp
    if image.endswith(('.jpg', '.jpeg', '.png', '.gif')):  # Kiểm tra xem tệp có phải là ảnh không
        image_path = f"image/{image}"  # Đường dẫn đến ảnh
        out_path = f"video/{index}.mp4"  # Đường dẫn video đầu ra, sử dụng chỉ số cho tên file

        # Gọi hàm random_video_effect_cython để xử lý video
        random_video_effect_cython(image_path, out_path, duration, fps, width, height)
        print(f"Đã tạo video: {out_path}")
    else:
        print(f"Bỏ qua tệp không phải ảnh: {image}")

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

# list_image = os.listdir("image")

# for index, image in enumerate(list_image):  # Sử dụng enumerate để lấy cả chỉ số và tên tệp
#     if image.endswith(('.jpg', '.jpeg', '.png', '.gif')):  # Kiểm tra xem tệp có phải là ảnh không
#         image_path = f"image/{image}"  # Đường dẫn đến ảnh
#         out_path = f"video/{index}.mp4"  # Đường dẫn video đầu ra, sử dụng chỉ số cho tên file

#         # Gọi hàm random_video_effect_cython để xử lý video
#         random_video_effect_cython(image_path, out_path, duration, fps, width, height)
#         print(f"Đã tạo video: {out_path}")
#     else:
#         print(f"Bỏ qua tệp không phải ảnh: {image}")

import subprocess
import json

def get_docker_network_subnet(network_name):
    """
    Lấy dải IP của một mạng Docker cụ thể.
    :param network_name: Tên mạng Docker (vd: 'bridge', 'custom-net').
    :return: Dải IP (Subnet) hoặc None nếu không tìm thấy.
    """
    try:
        # Chạy lệnh `docker network inspect` để lấy thông tin mạng Docker
        result = subprocess.check_output(["docker", "network", "inspect", network_name], text=True)
        network_data = json.loads(result)
        
        # Kiểm tra và trả về dải IP (Subnet) nếu có
        if network_data and "IPAM" in network_data[0] and "Config" in network_data[0]["IPAM"]:
            subnet = network_data[0]["IPAM"]["Config"][0].get("Subnet")
            return subnet
        else:
            return None
    except subprocess.CalledProcessError as e:
        print(f"Command error: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

if __name__ == "__main__":
    # Tên mạng Docker cần lấy dải IP (vd: 'bridge')
    network_name = "bridge"
    
    # Lấy dải IP
    subnet = get_docker_network_subnet(network_name)
    
    if subnet:
        print(f"Dải IP của mạng Docker '{network_name}': {subnet}")
    else:
        print(f"Không tìm thấy dải IP của mạng Docker '{network_name}' hoặc mạng không tồn tại.")

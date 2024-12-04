import cv2
cimport cv2
import random

import cv2
import numpy as np

import cv2
import numpy as np

def resize_and_crop(image_path: str, target_width: int=1920, target_height: int=1080):
    # Đọc ảnh từ đường dẫn
    image = cv2.imread(image_path)
    print(f"Đang đọc ảnh từ: {image_path}")
    
    # Kiểm tra nếu ảnh không tồn tại
    if image is None:
        raise ValueError(f"Không thể đọc hình ảnh từ {image_path}. Vui lòng kiểm tra lại đường dẫn.")
    
    try:
        # Lấy kích thước gốc của ảnh
        original_height, original_width = image.shape[:2]
        print(f"Kích thước gốc: {original_width} x {original_height}")

        # Tính tỷ lệ resize sao cho một chiều đạt kích thước mục tiêu
        scale_width = target_width / float(original_width)
        scale_height = target_height / float(original_height)

        # Làm tròn tỷ lệ lên để đảm bảo ảnh đủ lớn
        scale_width = np.ceil(scale_width)  # Làm tròn lên tỷ lệ chiều rộng
        scale_height = np.ceil(scale_height)  # Làm tròn lên tỷ lệ chiều cao

        # Chọn tỷ lệ phóng to lớn hơn (đảm bảo ảnh không thiếu pixel)
        scale = max(scale_width, scale_height)

        # Phóng to ảnh theo tỷ lệ đã làm tròn
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)

        # Resize ảnh
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        print(f"Kích thước sau khi thay đổi: {new_width} x {new_height}")

        # Tính toán crop (canh giữa)
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        # Đảm bảo crop không vượt quá kích thước ảnh
        left = max(0, left)
        top = max(0, top)
        right = min(new_width, right)
        bottom = min(new_height, bottom)

        cropped_image = resized_image[top:bottom, left:right]
        print(f"Kích thước sau khi crop: {cropped_image.shape[1]} x {cropped_image.shape[0]}")

        return cropped_image

    except Exception as e:
        print(f"Lỗi xảy ra trong quá trình thay đổi kích thước và crop ảnh: {e}")



def create_parallax_left_video(image_path: str, output_path: str, duration: float=10, fps: int=30, width: int=1920, height: int=1080):
    # Initialize frame variables
    cdef int total_frames = int(duration * fps)  # Tổng số frame
    cdef int current_x_bg, current_x_img  # Movement variables
    cdef int total_1, total_2  # For background cropping
    cdef object cropped_background, result  # Frame objects
    cdef object image_1, image_2  # Resized images
    cdef float move_per_frame_bg, move_per_frame_img,  # Movement rates for background and image
    # Video writing setup
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Định dạng video MP4
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))  # Video output
    
    # Call functions to resize images
    image_1 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh lớn (resize cho phù hợp với video)
    image_2 = resize_and_crop(image_path, target_width=int(width * 0.6), target_height=int(height * 0.6))  # Ảnh nhỏ
    
    scale_factor = 1.4  # Tỷ lệ phóng to cho ảnh nền, điều này có thể thay đổi để điều chỉnh hiệu ứng
    blur_strength = 41  # Độ mạnh của Gaussian blur
    
    # Resize ảnh lớn và tạo nền mờ
    image_resized = cv2.resize(image_1, (int(width * scale_factor), int(height * scale_factor)))
    blurred_background = cv2.GaussianBlur(image_resized, (blur_strength, blur_strength), 0)
    
    # Thêm border cho ảnh nhỏ
    image_2_with_border = cv2.copyMakeBorder(image_2, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    
    # Kích thước của ảnh lớn và ảnh nhỏ sau khi border
    cdef int height_1, width_1, height_2, width_2
    height_1, width_1 = blurred_background.shape[:2]
    height_2, width_2 = image_2_with_border.shape[:2]
    
    # Tính toán quãng đường di chuyển của nền mờ
    total_move = width_1 - width
    move_per_frame_bg = total_move / total_frames  # Di chuyển mỗi frame cho nền mờ
    
    # Tính toán quãng đường di chuyển của ảnh nhỏ
    total_move_img = width - width_2
    move_per_frame_img = total_move_img / total_frames  # Di chuyển mỗi frame cho ảnh nhỏ
    
    # Loop over each frame
    for frame in range(total_frames):
        # Tính toán vị trí di chuyển của nền mờ (lúc này di chuyển ngược lại - từ trái sang phải)
        current_x_bg = int(frame * move_per_frame_bg)  # Vị trí X của nền mờ
        
        # Tính toán vị trí di chuyển của ảnh nhỏ
        current_x_img = int(frame * move_per_frame_img)  # Vị trí X của ảnh nhỏ
        
        # Tính toán vị trí cắt nền mờ sao cho vừa với video
        total_1 = (height_1 - height) // 2  # Để căn giữa ảnh lớn
        cropped_background = blurred_background[total_1:total_1 + height, current_x_bg:current_x_bg + width]
        
        # Tính toán vị trí ảnh nhỏ trên nền mờ (căn giữa trên nền)
        total_2 = (height - height_2) // 2  # Để căn giữa ảnh nhỏ trên nền
        
        result = cropped_background.copy()
        # Lồng ảnh nhỏ vào nền mờ
        result[total_2: total_2 + height_2, current_x_img:current_x_img + width_2] = image_2_with_border
        
        # Ghi frame vào video
        out.write(result)
    
    # Giải phóng video writer và đóng cửa sổ OpenCV
    out.release()
    cv2.destroyAllWindows()


def create_parallax_right_video(image_path: str, output_path: str, duration: float=10, fps: int=30, width: int=1920, height: int=1080):
    cdef int total_frames = int(duration * fps)  # Tổng số frame
    cdef int current_x_bg, current_x_img  # Movement variables
    cdef int total_1, total_2  # For background cropping
    cdef object cropped_background, result  # Frame objects
    cdef object image_1, image_2  # Resized images
    cdef float move_per_frame_bg, move_per_frame_img  # Movement rates for background and image
    

    total_frames = int(duration * fps)  # Tổng số frame
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Định dạng video MP4
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))  # Video output
    
    # Giả sử bạn có hàm resize_and_crop và resize_and_limit đã được định nghĩa
    image_1 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh lớn (resize cho phù hợp với video)
    image_2 = resize_and_crop(image_path, target_width=int(width * 0.6), target_height=int(height * 0.6))  # Ảnh nhỏ
    
    scale_factor = 1.4  # Tỷ lệ phóng to cho ảnh nền, điều này có thể thay đổi để điều chỉnh hiệu ứng
    blur_strength = 41  # Độ mạnh của Gaussian blur
    
    # Resize ảnh lớn và tạo nền mờ
    image_resized = cv2.resize(image_1, (int(width * scale_factor), int(height * scale_factor)))
    blurred_background = cv2.GaussianBlur(image_resized, (blur_strength, blur_strength), 0)
    
    # Thêm border cho ảnh nhỏ
    image_2_with_border = cv2.copyMakeBorder(image_2, 5, 5, 5, 5, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    
    # Kích thước của ảnh lớn và ảnh nhỏ sau khi border
    height_1, width_1 = blurred_background.shape[:2]
    height_2, width_2 = image_2_with_border.shape[:2]
    
    # Tính toán quãng đường di chuyển của nền mờ
    total_move = width_1 - width
    move_per_frame_bg = total_move / total_frames  # Di chuyển mỗi frame cho nền mờ
    
    # Tính toán quãng đường di chuyển của ảnh nhỏ
    total_move_img = width - width_2
    move_per_frame_img = total_move_img / total_frames  # Di chuyển mỗi frame cho ảnh nhỏ
    
    for frame in range(total_frames):
        # Tính toán vị trí di chuyển của nền mờ (di chuyển từ phải qua trái)
        current_x_bg = int((total_frames - frame) * move_per_frame_bg)  # Vị trí X của nền mờ từ phải qua trái
        
        # Tính toán vị trí di chuyển của ảnh nhỏ (di chuyển từ phải qua trái)
        current_x_img = int((total_frames - frame) * move_per_frame_img)  # Vị trí X của ảnh nhỏ từ phải qua trái
        
        # Tính toán vị trí cắt nền mờ sao cho vừa với video
        total_1 = (height_1 - height) // 2  # Để căn giữa ảnh lớn
        cropped_background = blurred_background[total_1:total_1 + height, current_x_bg:current_x_bg + width]
        
        # Tính toán vị trí ảnh nhỏ trên nền mờ (căn giữa trên nền)
        total_2 = (height - height_2) // 2  # Để căn giữa ảnh nhỏ trên nền
        
        result = cropped_background.copy()
        # Lồng ảnh nhỏ vào nền mờ
        result[total_2: total_2 + height_2, current_x_img:current_x_img + width_2] = image_2_with_border
        
        # Ghi frame vào video
        out.write(result)
    
    # Giải phóng video writer và đóng cửa sổ OpenCV
    out.release()
    cv2.destroyAllWindows()

#trượt ảnh
def create_scrolling_image_video(image_path: str, output_path: str, duration: float=10, fps: int=30, width: int=1920, height: int=1080):
    """
    Creates a scrolling video from an image. The image will scroll in either horizontal or vertical direction
    based on its aspect ratio and the video target resolution.
    """
    # Declare types for variables
    cdef int total_frames, orig_height, orig_width, new_width, new_height
    cdef int current_x, current_y, total_move
    cdef float scale_factor, move_per_frame  # Declare move_per_frame as float to handle division
    cdef object image, resized_image, cropped_image, fourcc, out
    cdef str direction
    cdef int target_width = width
    cdef int target_height = height

    # Calculate total frames
    total_frames = int(duration * fps)

    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Cannot read image from {image_path}. Please check the path.")

    # Get the original dimensions of the image
    orig_height, orig_width = image.shape[:2]

    # Determine scale factor based on the smaller dimension
    if orig_width < orig_height:
        scale_factor = target_width / orig_width
    else:
        scale_factor = target_height / orig_height

    # Calculate the new resized dimensions
    new_width = int(orig_width * scale_factor)
    new_height = int(orig_height * scale_factor)
    
    resized_image = cv2.resize(image, (new_width, new_height))

    # Set up video writer codec
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_width, target_height))

    # Check if the resized image is the same as the target dimensions
    if new_width == target_width:  # Vertical scrolling
        direction = random.choice(['up_down', 'down_up'])
        print(f"Scrolling direction: {direction}")

        if direction == 'up_down':
            total_move = new_height - target_height
            move_per_frame = total_move / total_frames  # This will now be a float
            for frame in range(total_frames):
                current_y = int(frame * move_per_frame)
                cropped_image = resized_image[current_y:current_y + target_height, 0:target_width]
                out.write(cropped_image)

        elif direction == 'down_up':
            total_move = new_height - target_height
            move_per_frame = total_move / total_frames  # This will now be a float
            for frame in range(total_frames):
                current_y = int(total_move - (frame * move_per_frame))
                cropped_image = resized_image[current_y:current_y + target_height, 0:target_width]
                out.write(cropped_image)

    elif new_height == target_height:  # Horizontal scrolling
        direction = random.choice(['left_right', 'right_left'])
        print(f"Scrolling direction: {direction}")

        if direction == 'left_right':
            total_move = new_width - target_width
            move_per_frame = total_move / total_frames  # This will now be a float
            for frame in range(total_frames):
                current_x = int(frame * move_per_frame)
                cropped_image = resized_image[0:target_height, current_x:current_x + target_width]
                out.write(cropped_image)

        elif direction == 'right_left':
            total_move = new_width - target_width
            move_per_frame = total_move / total_frames  # This will now be a float
            for frame in range(total_frames):
                current_x = int(total_move - (frame * move_per_frame))
                cropped_image = resized_image[0:target_height, current_x:current_x + target_width]
                out.write(cropped_image)
    else:
        # If image doesn't match any of the target dimensions, just write the whole resized image
        out.write(resized_image)

    # Release the video writer and finalize the video
    out.release()
    print(f"Video created successfully at: {output_path}")


def create_zoom_in_video(image_path: str, output_path: str, duration: float=10, fps: int=30, width: int=1920, height: int=1080):
    """
    Creates a zoom-in video from an image.
    
    :param image_path: Path to the source image
    :param output_path: Path to save the output video
    :param duration: Duration of the video in seconds
    :param fps: Frames per second of the video
    :param width: Width of the video
    :param height: Height of the video
    """
    # Resize and crop the image (this should return an image that is the right size)
    cdef object image = resize_and_crop(image_path, target_width=width, target_height=height)
    
    # Set up the codec and video writer
    cdef object fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    cdef object out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Total number of frames in the video
    cdef int total_frames = int(duration * fps)
    
    # Zoom effect scaling parameters
    cdef float start_scale = 1.0  # Start from 1.0 (original size)
    cdef float end_scale = 1.6    # Zoom in to 1.6 times the original size
    
    # Declare variables once before the loop
    cdef int frame, new_width, new_height, start_x, start_y
    cdef float current_scale
    cdef object resized_image, cropped_image
    
    # Write each frame with the zoom-in effect
    for frame in range(total_frames):
        # Calculate the current scale factor
        current_scale = start_scale + (end_scale - start_scale) * (frame / (total_frames - 1))
        
        # Calculate the new dimensions
        new_width = int(width * current_scale)
        new_height = int(height * current_scale)
        
        # Resize the image
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # Calculate the center crop position
        start_x = (new_width - width) // 2
        start_y = (new_height - height) // 2
        
        # Crop the image to the target size
        cropped_image = resized_image[start_y:start_y + height, start_x:start_x + width]
        
        # Write the frame to the video
        out.write(cropped_image)
    
    # Release the video writer
    out.release()
    
    print(f"Zoom-in video created successfully at: {output_path}")

def create_zoom_out_video(image_path: str, output_path: str, duration: float=10, fps: int=30, width: int=1920, height: int=1080):
    cdef object image = resize_and_crop(image_path, target_width=width, target_height=height)
    
    # Set up the codec and video writer
    cdef object fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    cdef object out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Total number of frames in the video
    cdef int total_frames = int(duration * fps)
    
    # Zoom effect scaling parameters
    cdef float start_scale = 1.6  # Start from 1.0 (original size)
    cdef float end_scale = 1.0    # Zoom in to 1.6 times the original size
    
    # Declare variables once before the loop
    cdef int frame, new_width, new_height, start_x, start_y
    cdef float current_scale
    cdef object resized_image, cropped_image
    # Ghi từng khung hình với hiệu ứng zoom out
    for frame in range(total_frames):
        # Tính toán tỷ lệ thu phóng (giảm dần từ 1.4 đến 1.0)
        current_scale = start_scale - (start_scale - end_scale) * (frame / (total_frames - 1))
        
        # Tính kích thước mới
        new_width = int(width * current_scale)
        new_height = int(height * current_scale)
        
        # Resize hình ảnh
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
        
        # Tính toán vị trí để căn giữa
        start_x = (new_width - width) // 2
        start_y = (new_height - height) // 2
        
        # Cắt hình ảnh để giữ nguyên kích thước video
        cropped_image = resized_image[start_y:start_y+height, start_x:start_x+width]
        
        # Ghi khung hình
        out.write(cropped_image)
    
    # Giải phóng đối tượng VideoWriter
    out.release()
    
    print(f"Video zoom out đã được tạo thành công tại: {output_path}")


# Hàm tạo video với hiệu ứng zoom và background
def create_zoom_in_video_with_background(image_path: str, output_path: str, duration: float=10, fps: int=30, width: int=1920, height: int=1080):
    """
    Tạo video với hiệu ứng zoom cho ảnh nền và ảnh nhỏ, di chuyển theo các hiệu ứng ngược chiều.
    """
    cdef object image_1, image_2, blurred_background, image_2_with_border, frame_result
    cdef int total_frames, start_x_bg, start_y_bg, start_x_small, start_y_small
    cdef float scale_bg, scale_img
    cdef int blur_strength = 41  # Độ mạnh của Gaussian blur
    
    # Resize ảnh lớn và ảnh nhỏ
    image_1 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh nền
    image_2 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh nhỏ
    
    # Thiết lập codec và đối tượng VideoWriter
    cdef object fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    cdef object out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Tổng số khung hình trong video
    total_frames = int(duration * fps)
    
    # Hiệu ứng zoom cho nền (từ 1.4 về 1.0)
    start_scale_bg = 1.5
    end_scale_bg = 1.0
    
    # Hiệu ứng zoom cho ảnh nhỏ (từ 0.8 về 0.5)
    start_scale_img = 0.5
    end_scale_img = 0.8

    # Mờ ảnh nền để làm nền mờ
    blurred_background = cv2.GaussianBlur(image_1, (blur_strength, blur_strength), 0)
    
    # Thêm border trắng cho ảnh nhỏ
    image_2_with_border = cv2.copyMakeBorder(image_2, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    
    # Kích thước của ảnh lớn và ảnh nhỏ sau khi border
    cdef int height_1 = blurred_background.shape[0]
    cdef int width_1 = blurred_background.shape[1]
    cdef int height_2 = image_2_with_border.shape[0]
    cdef int width_2 = image_2_with_border.shape[1]
    
    for frame in range(total_frames):
        # Tính tỷ lệ zoom cho ảnh nền và ảnh nhỏ tại frame hiện tại
        scale_bg = start_scale_bg - (frame / total_frames) * (start_scale_bg - end_scale_bg)  # Zoom out cho nền
        scale_img = start_scale_img + (frame / total_frames) * (end_scale_img - start_scale_img)  # Zoom in cho ảnh nhỏ
        
        # Thay đổi kích thước ảnh nền và ảnh nhỏ theo tỷ lệ
        resized_bg = cv2.resize(blurred_background, (int(width_1 * scale_bg), int(height_1 * scale_bg)))
        resized_small = cv2.resize(image_2_with_border, (int(width_2 * scale_img), int(height_2 * scale_img)))
        
        # Cắt phần trung tâm của ảnh nền để phù hợp với kích thước video
        start_x_bg = (resized_bg.shape[1] - width) // 2
        start_y_bg = (resized_bg.shape[0] - height) // 2
        cropped_bg = resized_bg[start_y_bg:start_y_bg + height, start_x_bg:start_x_bg + width]
        
        # Cắt phần ảnh nhỏ để căn giữa
        start_x_small = (width - resized_small.shape[1]) // 2
        start_y_small = (height - resized_small.shape[0]) // 2
        
        # Tạo frame kết hợp giữa ảnh nền và ảnh nhỏ
        frame_result = cropped_bg.copy()
        frame_result[start_y_small:start_y_small + resized_small.shape[0], start_x_small:start_x_small + resized_small.shape[1]] = resized_small
        
        # Ghi frame vào video
        out.write(frame_result)
    
    # Giải phóng đối tượng VideoWriter
    out.release()
    print(f"Video đã được tạo thành công tại: {output_path}")


def create_zoom_out_video_with_background(image_path: str, output_path: str, duration: float=10, fps: int=30, width: int=1920, height: int=1080):
    """
    Tạo video với hiệu ứng zoom cho ảnh nền và ảnh nhỏ, di chuyển theo các hiệu ứng ngược chiều.
    """
    cdef object image_1, image_2, blurred_background, image_2_with_border, frame_result
    cdef int total_frames, start_x_bg, start_y_bg, start_x_small, start_y_small
    cdef float scale_bg, scale_img
    cdef int blur_strength = 41  # Độ mạnh của Gaussian blur
    
    # Resize ảnh lớn và ảnh nhỏ
    image_1 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh nền
    image_2 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh nhỏ
    
    # Thiết lập codec và đối tượng VideoWriter
    cdef object fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    cdef object out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Tổng số khung hình trong video
    total_frames = int(duration * fps)
    
    # Hiệu ứng zoom cho nền (từ 1.4 về 1.0)
    start_scale_bg = 1.0
    end_scale_bg = 1.5
    
    # Hiệu ứng zoom cho ảnh nhỏ (từ 0.8 về 0.5)
    start_scale_img = 0.8
    end_scale_img = 0.6

    # Mờ ảnh nền để làm nền mờ
    blurred_background = cv2.GaussianBlur(image_1, (blur_strength, blur_strength), 0)
    
    # Thêm border trắng cho ảnh nhỏ
    image_2_with_border = cv2.copyMakeBorder(image_2, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    
    # Kích thước của ảnh lớn và ảnh nhỏ sau khi border
    cdef int height_1 = blurred_background.shape[0]
    cdef int width_1 = blurred_background.shape[1]
    cdef int height_2 = image_2_with_border.shape[0]
    cdef int width_2 = image_2_with_border.shape[1]
    
    for frame in range(total_frames):
        # Tính tỷ lệ zoom cho ảnh nền và ảnh nhỏ tại frame hiện tại
        scale_bg = start_scale_bg - (frame / total_frames) * (start_scale_bg - end_scale_bg)  # Zoom out cho nền
        scale_img = start_scale_img + (frame / total_frames) * (end_scale_img - start_scale_img)  # Zoom in cho ảnh nhỏ
        
        # Thay đổi kích thước ảnh nền và ảnh nhỏ theo tỷ lệ
        resized_bg = cv2.resize(blurred_background, (int(width_1 * scale_bg), int(height_1 * scale_bg)))
        resized_small = cv2.resize(image_2_with_border, (int(width_2 * scale_img), int(height_2 * scale_img)))
        
        # Cắt phần trung tâm của ảnh nền để phù hợp với kích thước video
        start_x_bg = (resized_bg.shape[1] - width) // 2
        start_y_bg = (resized_bg.shape[0] - height) // 2
        cropped_bg = resized_bg[start_y_bg:start_y_bg + height, start_x_bg:start_x_bg + width]
        
        # Cắt phần ảnh nhỏ để căn giữa
        start_x_small = (width - resized_small.shape[1]) // 2
        start_y_small = (height - resized_small.shape[0]) // 2
        
        # Tạo frame kết hợp giữa ảnh nền và ảnh nhỏ
        frame_result = cropped_bg.copy()
        frame_result[start_y_small:start_y_small + resized_small.shape[0], start_x_small:start_x_small + resized_small.shape[1]] = resized_small
        
        # Ghi frame vào video
        out.write(frame_result)
    
    # Giải phóng đối tượng VideoWriter
    out.release()
    print(f"Video đã được tạo thành công tại: {output_path}")


def check_image_ratio(image_path: str):
    """
    Kiểm tra tỷ lệ ảnh và trả về True hoặc False dựa trên các điều kiện:
    - Ảnh dọc sẽ luôn trả về True.
    - Ảnh ngang sẽ chỉ trả về True nếu chiều rộng ít nhất là 1.3 lần chiều cao.

    :param image_path: Đường dẫn tới ảnh cần kiểm tra.
    :return: True nếu thỏa mãn điều kiện, False nếu không.
    """
    # Đọc ảnh
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Không thể đọc hình ảnh từ {image_path}. Vui lòng kiểm tra lại đường dẫn.")
    
    # Lấy kích thước của ảnh
    height, width = image.shape[:2]
    
    # Kiểm tra điều kiện ảnh dọc
    if height > width:
        return True
    
    # Kiểm tra điều kiện ảnh ngang (chiều rộng phải ít nhất lớn hơn 1.3 lần chiều cao)
    if width >= height * 1.3:
        return True
    
    return False

def random_video_effect_cython(image_path: str, output_path: str, duration: float=10, fps: int=30, width: int=1920, height: int=1080):
    # Danh sách các hàm cần chọn
    functions = [
        create_zoom_in_video_with_background,
        create_zoom_out_video_with_background,
        create_zoom_in_video,
        create_zoom_out_video,
        create_parallax_left_video,
        create_parallax_right_video
    ]
    try:
        # Chọn ngẫu nhiên một hàm từ danh sách
        selected_function = random.choice(functions)
    
        # Gọi hàm được chọn ngẫu nhiên với các tham số đã định nghĩa
        selected_function(image_path, output_path, duration, fps, width, height)
        return True
    except Exception as e:
        print(f"Error occurred while executing the selected function: {e}")
        return False
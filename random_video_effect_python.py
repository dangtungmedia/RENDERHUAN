import random
import cv2

def resize_and_crop(image_path, target_width=1920, target_height=1080):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Không thể đọc hình ảnh từ {image_path}. Vui lòng kiểm tra lại đường dẫn.")
    
    orig_height, orig_width = image.shape[:2]
    
    if orig_width < orig_height:
        scale_factor = target_width / orig_width
    else:
        scale_factor = target_height / orig_height
    
    new_width = int(orig_width * scale_factor)
    new_height = int(orig_height * scale_factor)
    
    resized_image = cv2.resize(image, (new_width, new_height))
    
    start_x = (new_width - target_width) // 2
    start_y = (new_height - target_height) // 2
    
    cropped_image = resized_image[start_y:start_y + target_height, start_x:start_x + target_width]
    
    return cropped_image

def resize_and_limit(image_path, target_width=1920, target_height=1080):
    """
    Thay đổi kích thước hình ảnh sao cho một trong hai cạnh không vượt quá kích thước mục tiêu.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Không thể đọc hình ảnh từ {image_path}. Vui lòng kiểm tra lại đường dẫn.")
    
    orig_height, orig_width = image.shape[:2]
    
    scale_width = target_width / orig_width
    scale_height = target_height / orig_height
    scale_factor = min(scale_width, scale_height)  # Chọn tỷ lệ nhỏ nhất để không vượt quá kích thước

    new_width = int(orig_width * scale_factor)
    new_height = int(orig_height * scale_factor)
    
    resized_image = cv2.resize(image, (new_width, new_height))

    return resized_image

    
def create_parallax_left_video(image_path, output_path, duration=10, fps=30, width=1920, height=1080):
    total_frames = int(duration * fps)  # Tổng số frame
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Định dạng video MP4
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))  # Video output
    
    # Giả sử bạn có hàm resize_and_crop và resize_and_limit đã được định nghĩa
    image_1 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh lớn (resize cho phù hợp với video)
    image_2 = resize_and_limit(image_path, target_width=int(width * 0.6), target_height=int(height * 0.6))  # Ảnh nhỏ
    
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

def create_parallax_right_video(image_path, output_path, duration=10, fps=30, width=1920, height=1080):
    total_frames = int(duration * fps)  # Tổng số frame
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Định dạng video MP4
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))  # Video output
    
    # Giả sử bạn có hàm resize_and_crop và resize_and_limit đã được định nghĩa
    image_1 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh lớn (resize cho phù hợp với video)
    image_2 = resize_and_limit(image_path, target_width=int(width * 0.6), target_height=int(height * 0.6))  # Ảnh nhỏ
    
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
    
def create_scrolling_image_video(image_path, output_path, duration=10, fps=30, target_width=1920, target_height=1080):
    # Đọc hình ảnh
    image = cv2.imread(image_path)
    
    if image is None:
        raise ValueError(f"Không thể đọc hình ảnh từ {image_path}. Vui lòng kiểm tra lại đường dẫn.")
    
    # Lấy kích thước ban đầu của hình ảnh
    orig_height, orig_width = image.shape[:2]
    
    # Xác định chiều nhỏ nhất và tính tỷ lệ thay đổi kích thước
    if orig_width < orig_height:
        scale_factor = target_width / orig_width
    else:
        scale_factor = target_height / orig_height
    
    # Thay đổi kích thước hình ảnh
    new_width = int(orig_width * scale_factor)
    new_height = int(orig_height * scale_factor)
    resized_image = cv2.resize(image, (new_width, new_height))
    
    # Thiết lập codec và đối tượng VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (target_width, target_height))
    
    # Tổng số khung hình trong video
    total_frames = duration * fps
    
    # Kiểm tra nếu chiều rộng hoặc chiều cao của hình ảnh bằng kích thước video
    if new_width == target_width:
        # Di chuyển từ trên xuống dưới hoặc từ dưới lên trên
        direction = random.choice(['up_down', 'down_up'])
        print(f"Di chuyển theo hướng: {direction}")
        
        if direction == 'up_down':
            total_move = new_height - target_height  # Quãng đường di chuyển
            move_per_frame = total_move / total_frames  # Di chuyển mỗi frame
            
            for frame in range(total_frames):
                current_y = int(frame * move_per_frame)  # Tính vị trí Y
                cropped_image = resized_image[current_y:current_y + target_height, 0:target_width]
                out.write(cropped_image)
        
        elif direction == 'down_up':
            total_move = new_height - target_height  # Quãng đường di chuyển
            move_per_frame = total_move / total_frames  # Di chuyển mỗi frame
            
            for frame in range(total_frames):
                current_y = int(total_move - (frame * move_per_frame))  # Di chuyển ngược lại
                cropped_image = resized_image[current_y:current_y + target_height, 0:target_width]
                out.write(cropped_image)
    
    elif new_height == target_height:
        # Di chuyển từ trái qua phải hoặc từ phải qua trái
        direction = random.choice(['left_right', 'right_left'])
        print(f"Di chuyển theo hướng: {direction}")
        
        if direction == 'left_right':
            total_move = new_width - target_width  # Quãng đường di chuyển
            move_per_frame = total_move / total_frames  # Di chuyển mỗi frame
            
            for frame in range(total_frames):
                current_x = int(frame * move_per_frame)  # Tính vị trí X
                cropped_image = resized_image[0:target_height, current_x:current_x + target_width]
                out.write(cropped_image)
        
        elif direction == 'right_left':
            total_move = new_width - target_width  # Quãng đường di chuyển
            move_per_frame = total_move / total_frames  # Di chuyển mỗi frame
            
            for frame in range(total_frames):
                current_x = int(total_move - (frame * move_per_frame))  # Di chuyển ngược lại
                cropped_image = resized_image[0:target_height, current_x:current_x + target_width]
                out.write(cropped_image)
    else:
        # Nếu không có chiều nào khớp, chỉ ghi hình ảnh vào video
        out.write(resized_image)
    
    # Giải phóng đối tượng VideoWriter
    out.release()
    print(f"Video đã được tạo thành công tại: {output_path}")

def create_zoom_in_video(image_path, output_path, duration=10, fps=30, width=1920, height=1080):
    """
    Tạo video với hiệu ứng zoom in từ nhỏ đến lớn.
    
    :param image_path: Đường dẫn đến hình ảnh nguồn
    :param output_path: Đường dẫn lưu video đầu ra
    :param duration: Thời gian video (giây)
    :param fps: Số khung hình trên giây
    :param width: Chiều rộng video
    :param height: Chiều cao video
    """
    # Resize và crop hình ảnh
    image = resize_and_crop(image_path, target_width=width, target_height=height)
    
    # Thiết lập codec và đối tượng VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Số lượng khung hình
    total_frames = duration * fps
    
    # Tính toán kích thước phóng to ban đầu (1.0) và lớn dần (1.4)
    start_scale = 1.0  # Bắt đầu từ 1.0 (kích thước gốc)
    end_scale = 1.6  # Phóng to đến 1.4
    
    # Ghi từng khung hình với hiệu ứng zoom in
    for frame in range(total_frames):
        # Tính toán tỷ lệ thu phóng (tăng dần từ 1.0 đến 1.4)
        current_scale = start_scale + (end_scale - start_scale) * (frame / (total_frames - 1))
        
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
    
    print(f"Video zoom in đã được tạo thành công tại: {output_path}")

def create_zoom_out_video(image_path, output_path, duration=10, fps=30, width=1920, height=1080):
    """
    Tạo video với hiệu ứng zoom out từ lớn đến nhỏ.
    
    :param image_path: Đường dẫn đến hình ảnh nguồn
    :param output_path: Đường dẫn lưu video đầu ra
    :param duration: Thời gian video (giây)
    :param fps: Số khung hình trên giây
    :param width: Chiều rộng video
    :param height: Chiều cao video
    """
    # Resize và crop hình ảnh
    image = resize_and_crop(image_path, target_width=width, target_height=height)
    
    # Thiết lập codec và đối tượng VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Số lượng khung hình
    total_frames = duration * fps
    
    # Tính toán kích thước phóng to ban đầu (1.4) và thu nhỏ cuối (1.0)
    start_scale = 1.6  # Bắt đầu từ 1.4 (phóng to)
    end_scale = 1.0  # Thu nhỏ đến 1.0
    
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

def create_zoom_in_video_with_background(image_path, output_path, duration=10, fps=30, width=1920, height=1080):
    """
    Tạo video với hiệu ứng zoom cho ảnh nền và ảnh nhỏ, di chuyển theo các hiệu ứng ngược chiều.

    :param image_path: Đường dẫn tới hình ảnh đầu vào.
    :param output_path: Đường dẫn lưu video đầu ra.
    :param duration: Thời gian video (giây).
    :param fps: Số khung hình trên giây.
    :param width: Chiều rộng video.
    :param height: Chiều cao video.
    :return: Tạo video với hiệu ứng zoom.
    """
    # Resize ảnh lớn (resize cho phù hợp với video)
    image_1 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh lớn
    image_2 = resize_and_limit(image_path, target_width=width, target_height=height)  # Ảnh nhỏ
    
    # Thiết lập codec và đối tượng VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Tổng số khung hình trong video
    total_frames = duration * fps
    
    # Hiệu ứng zoom cho nền (từ 1.4 về 1.0)
    start_scale_bg = 1.4
    end_scale_bg = 1.0
    
    # Hiệu ứng zoom cho ảnh nhỏ (từ 0.8 về 0.5)
    start_scale_img = 0.5
    end_scale_img = 0.8
    blur_strength = 41  # Độ mạnh của Gaussian blur

    blurred_background = cv2.GaussianBlur(image_1, (blur_strength, blur_strength), 0)
    image_2_with_border = cv2.copyMakeBorder(image_2, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))


    # Kích thước của ảnh lớn và ảnh nhỏ sau khi border
    height_1, width_1 = blurred_background.shape[:2]
    height_2, width_2 = image_2_with_border.shape[:2]



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
    
def create_zoom_out_video_with_background(image_path, output_path, duration=10, fps=30, width=1920, height=1080):
    """
    Tạo video với hiệu ứng zoom cho ảnh nền và ảnh nhỏ, di chuyển theo các hiệu ứng ngược chiều.

    :param image_path: Đường dẫn tới hình ảnh đầu vào.
    :param output_path: Đường dẫn lưu video đầu ra.
    :param duration: Thời gian video (giây).
    :param fps: Số khung hình trên giây.
    :param width: Chiều rộng video.
    :param height: Chiều cao video.
    :return: Tạo video với hiệu ứng zoom.
    """
    # Resize ảnh lớn (resize cho phù hợp với video)
    image_1 = resize_and_crop(image_path, target_width=width, target_height=height)  # Ảnh lớn
    image_2 = resize_and_limit(image_path, target_width=width, target_height=height)  # Ảnh nhỏ
    
    # Thiết lập codec và đối tượng VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Tổng số khung hình trong video
    total_frames = duration * fps
    
    # Hiệu ứng zoom cho nền (từ 1.4 về 1.0)
    start_scale_bg = 1.0
    end_scale_bg = 1.4
    
    # Hiệu ứng zoom cho ảnh nhỏ (từ 0.8 về 0.5)
    start_scale_img = 0.8
    end_scale_img = 0.6
    blur_strength = 41  # Độ mạnh của Gaussian blur

    blurred_background = cv2.GaussianBlur(image_1, (blur_strength, blur_strength), 0)
    image_2_with_border = cv2.copyMakeBorder(image_2, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))


    # Kích thước của ảnh lớn và ảnh nhỏ sau khi border
    height_1, width_1 = blurred_background.shape[:2]
    height_2, width_2 = image_2_with_border.shape[:2]



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
    
def check_image_ratio(image_path):
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


def random_video_effect(image_path, output_path="videos.mp4", duration=10, fps=30, width=1920, height=1080):
    # Danh sách các hàm cần chọn
    functions = [
        create_zoom_in_video_with_background,
        create_zoom_out_video_with_background,
        create_zoom_in_video,
        create_zoom_out_video,
        create_parallax_left_video,
        create_parallax_right_video
    ]
    
    if check_image_ratio(image_path):
        functions.append(create_scrolling_image_video)
        
    # Chọn ngẫu nhiên một hàm từ danh sách
    selected_function = random.choice(functions)
    
    # Gọi hàm được chọn ngẫu nhiên với các tham số đã định nghĩa
    selected_function(image_path, output_path, duration, fps, width, height)

# Example usage
image_path = "image.jpg"  # Set image path
out_path = "videos/caches.mp4"  # Set output path
duration = 10  # Video duration (seconds)
fps = 30  # Frames per second
width = 1920  # Video width
height = 1080  # Video height
random_video_effect(image_path, output_path=out_path,)


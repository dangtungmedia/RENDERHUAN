import cv2
import os

def resize_and_crop(image_path: str, target_width: int=1920, target_height: int=1080):
    # Đọc ảnh
    image = cv2.imread(image_path)
    
    if image is None:
        raise ValueError(f"Không thể đọc hình ảnh từ {image_path}. Vui lòng kiểm tra lại đường dẫn.")
    
    orig_height, orig_width = image.shape[:2]
    
    print(f"Kích thước ảnh gốc: {orig_width}x{orig_height}")
    
    # Tính tỷ lệ phóng to sao cho một trong các cạnh bằng target_width hoặc target_height
    scale_w = target_width / orig_width
    scale_h = target_height / orig_height
    
    # Chọn tỷ lệ phóng to lớn nhất để phóng to ảnh mà không bị thiếu
    scale_factor = max(scale_w, scale_h)
    
    # Tính kích thước mới sau khi phóng to
    new_width = int(orig_width * scale_factor)
    new_height = int(orig_height * scale_factor)
    
    print(f"Tỷ lệ phóng to: {scale_factor}")
    print(f"Kích thước mới sau khi phóng to: {new_width}x{new_height}")
    
    # Thay đổi kích thước ảnh
    resized_image = cv2.resize(image, (new_width, new_height))
    
    # Cắt căn giữa nếu ảnh sau khi phóng to vượt quá kích thước mục tiêu
    start_x = (new_width - target_width) // 2
    start_y = (new_height - target_height) // 2
    
    # Cắt ảnh để có kích thước target_width x target_height
    cropped_image = resized_image[start_y:start_y + target_height, start_x:start_x + target_width]
    
    return cropped_image

# Đường dẫn ảnh
image_path = "media/95571/image/view-castle-with-nature-landscape_23-2150984811.jpg"

# Kiểm tra xem ảnh có tồn tại không
if not os.path.exists(image_path):
    print(f"Ảnh không tồn tại: {image_path}")
else:
    # Gọi hàm resize_and_crop
    image = resize_and_crop(image_path, 1920, 1080)

    # Lưu ảnh sau khi phóng to và căn giữa
    cv2.imwrite("resized_and_cropped_image.jpg", image)
    print("Ảnh đã được lưu.")

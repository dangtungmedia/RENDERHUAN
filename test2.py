import os
import requests
from tqdm import tqdm

def download_file(url, output_path):
    # Gửi yêu cầu GET và lấy tệp
    response = requests.get(url, stream=True)
    # Kiểm tra nếu yêu cầu thành công
    if response.status_code == 200:
        # Lấy kích thước tệp
        total_size = int(response.headers.get('content-length', 0))
        
        # Mở tệp để ghi dữ liệu
        with open(output_path, 'wb') as file:
            # Tạo tiến độ với tqdm
            with tqdm(total=total_size, unit='B', unit_scale=True) as bar:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)  # Ghi chunk vào tệp
                        bar.update(len(chunk))  # Cập nhật tiến độ
        print(f"Tải xuống hoàn tất! Tệp được lưu tại {output_path}")
    else:
        print(f"Lỗi khi tải tệp: {response.status_code}")

# Sử dụng hàm
url = 'https://hrmedia89.com/render/down_load_screen/'  # Thay thế bằng đường dẫn tệp thực tế
output_path = 'video_screen.zip'  # Đường dẫn và tên tệp đầu ra

download_file(url, output_path)
import os
import shutil
import subprocess
from multiprocessing import Pool, cpu_count

# Định nghĩa đường dẫn thư mục
video_folder = "video"
chace_video_folder = "chace_video"

# Tạo thư mục chace_video nếu chưa tồn tại
os.makedirs(chace_video_folder, exist_ok=True)

# Di chuyển tất cả các tệp video từ video sang chace_video
for item in os.listdir(video_folder):
    source_path = os.path.join(video_folder, item)
    destination_path = os.path.join(chace_video_folder, item)
    
    shutil.move(source_path, destination_path)

print("✅ Đã di chuyển toàn bộ nội dung từ 'video' sang 'chace_video'.")

# Cấu hình thông số chuyển đổi
target_resolution = "1280x720"  # Độ phân giải mong muốn
target_fps = 24  # Số khung hình trên giây

# Danh sách file video cần xử lý
video_files = [f for f in os.listdir(chace_video_folder) if os.path.isfile(os.path.join(chace_video_folder, f))]

# Hàm chuyển đổi video dùng FFmpeg
def convert_video(file_name):
    input_path = os.path.join(chace_video_folder, file_name)
    output_path = os.path.join(video_folder, f"converted_{file_name}")

    # Lệnh FFmpeg để chuyển đổi video
    ffmpeg_command = [
        "ffmpeg",
        "-i", input_path,  # Đường dẫn video đầu vào
        "-vf", f"scale={target_resolution}",  # Độ phân giải
        "-r", str(target_fps),  # Frame rate
        "-c:v", "libx264",  # Codec video
        "-preset", "ultrafast",  # Chế độ mã hóa nhanh
        output_path  # Đường dẫn lưu video sau xử lý
    ]

    # Chạy FFmpeg
    subprocess.run(ffmpeg_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Xóa file gốc trong chace_video sau khi xử lý xong
    os.remove(input_path)
    print(f"✅ Đã xử lý xong: {file_name}")

# Sử dụng multiprocessing để xử lý song song nhiều video
if __name__ == "__main__":
    num_workers = 8
    with Pool(num_workers) as pool:
        pool.map(convert_video, video_files)

    # Sau khi xử lý xong, xóa thư mục chace_video
    shutil.rmtree(chace_video_folder)
    print("📂 Đã xóa thư mục 'chace_video' sau khi hoàn tất.")

    print("🎉 Hoàn thành quá trình chuyển đổi video với multiprocessing!")

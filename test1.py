import os
import subprocess

def check_video_integrity(video_path):
    """
    Kiểm tra tính toàn vẹn của video bằng cách sử dụng FFmpeg.
    Trả về True nếu video không bị lỗi, False nếu có lỗi.
    """
    try:
        # Lệnh FFmpeg để kiểm tra video
        command = [
            "ffmpeg", "-v", "error", "-i", video_path, "-f", "null", "-"
        ]
        result = subprocess.run(command, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        
        # Kiểm tra output của FFmpeg để xác định lỗi
        if result.stderr:
            errors = result.stderr.decode("utf-8")
            if "error" in errors.lower():
                print(f"Video lỗi: {video_path}")
                return False
        return True
    except Exception as e:
        print(f"Lỗi khi kiểm tra video {video_path}: {e}")
        return False

def clean_corrupted_videos(directory):
    """
    Xóa các video bị lỗi trong thư mục.
    """
    for filename in os.listdir(directory):
        video_path = os.path.join(directory, filename)

        # Kiểm tra nếu là file video
        if os.path.isfile(video_path) and filename.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.flv')):
            print(f"Đang kiểm tra: {video_path}")
            if not check_video_integrity(video_path):
                try:
                    os.remove(video_path)
                    print(f"Đã xóa video lỗi: {video_path}")
                except Exception as e:
                    print(f"Lỗi khi xóa video {video_path}: {e}")

# Đường dẫn đến thư mục chứa video
video_directory = "video"

# Thực hiện kiểm tra và dọn dẹp
clean_corrupted_videos(video_directory)

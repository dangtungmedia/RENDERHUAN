import subprocess


def check_video_integrity(video_path):
    """Kiểm tra xem video có thể phát được không bằng FFmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-f", "null",
            "-"
        ]
        subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
    
print(check_video_integrity("media\363030\video\6.mp4"))
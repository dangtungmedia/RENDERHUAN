import os
import requests

def get_public_ip():
    try:
        # Sử dụng ipify API để lấy địa chỉ IPv4 public
        response = requests.get("https://api.ipify.org")
        if response.status_code == 200:
            return response.text.strip()
        else:
            print(f"Failed to get public IP: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error getting public IP: {e}")
        return None

if __name__ == "__main__":
    # Lấy địa chỉ IP public
    ip_address = get_public_ip()
    
    # Chạy Celery worker với 2 worker và queue render_video
    os.system(f"celery -A celeryworker worker -l INFO --hostname={ip_address}-Content --concurrency=3 -Q render_video_content")
    
    

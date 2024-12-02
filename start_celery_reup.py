import os
import requests
import psutil

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

def get_cpu_cores():
    # Số lõi logic (bao gồm cả những lõi ảo nếu có Hyper-Threading)
    logical_cores = psutil.cpu_count(logical=True)
    # Số lõi vật lý
    physical_cores = psutil.cpu_count(logical=False)
    return physical_cores, logical_cores

if __name__ == "__main__":
    # Lấy địa chỉ IP public
    ip_address = get_public_ip()
    if ip_address:
        # Lấy số lượng lõi CPU vật lý
        physical_cores, logical_cores = get_cpu_cores()

        # Chạy Celery worker với số lượng worker là physical_cores - 1 (bớt 1 để tránh overload)
        os.system(f"celery -A celeryworker worker -l INFO --hostname={ip_address}-Reup --concurrency={physical_cores - 1} -Q render_video_reupload")
    else:
        print("Không thể lấy địa chỉ IP public.")

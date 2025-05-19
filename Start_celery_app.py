import os
import requests
import socket
import netifaces

import os
import random
import json
import requests
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import Set, List, Dict
import logging
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from threading import Lock
import sys
import shutil
from multiprocessing import Pool, cpu_count
import os
import requests
from tqdm import tqdm

import zipfile
import os
from dotenv import load_dotenv

# Nạp biến môi trường từ file .env
load_dotenv()


# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class VideoDownloader:
    def __init__(self, json_file: str, output_dir: str, max_videos: int = 5000):
        self.json_file = json_file
        self.output_dir = Path(output_dir)
        self.max_videos = max_videos
        self.selected_urls: Set[str] = set()
        self.downloaded_count = 0
        self.lock = Lock()  # Khóa để đảm bảo tính đồng bộ

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'video/webm,video/mp4,video/*;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://pixabay.com/'
        }

        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Ensure output_dir exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_urls(self) -> List[Dict]:
        with open(self.json_file, 'r') as file:
            data = json.load(file)
        valid_data = [item for item in data if 'url' in item and item['url'].startswith('http')]
        return random.sample(valid_data, len(valid_data))

    def is_file_downloaded(self, url: str) -> bool:
        file_name = os.path.basename(urlparse(url).path)
        return (self.output_dir / file_name).exists()

    def download_single_video(self, item: Dict, index: int, max_retries: int = 10) -> bool:
        temp_dir = "chace_video"
        os.makedirs(temp_dir, exist_ok=True)

        url = item['url']
        file_name = os.path.basename(urlparse(url).path)
        file_cache = Path(temp_dir) / file_name  # Sử dụng Path để kết hợp đường dẫn
        file_path = self.output_dir / file_name

        if file_path.exists():
            logging.info(f"[{index}] Video đã tồn tại: {file_name}, bỏ qua.")
            return True

        for attempt in range(1, max_retries + 1):
            try:
                time.sleep(2)
                logging.info(f"[{index}] Đang tải: {file_name} (Thử lần {attempt})")
                response = self.session.get(url, headers=self.headers, stream=True, timeout=30)
                response.raise_for_status()

                file_size = 0
                with open(file_cache, 'wb') as video_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            video_file.write(chunk)
                            file_size += len(chunk)

                if file_size > 0:
                    ffmpeg_command = [
                        "ffmpeg",
                        "-i", rf"{file_cache}",  # Đường dẫn video đầu vào
                        "-vf", f"scale=1280:720,fps=24",  # Độ phân giải
                        "-r", "24",
                        "-c:v", "hevc_nvenc",  # Codec video
                        "-c:a", "aac",  # Đảm bảo codec âm thanh là AAC
                        "-b:a", "192k",  # Bitrate âm thanh hợp lý
                        "-preset", "hq",
                        "-pix_fmt", "yuv420p",  # Định dạng pixel
                        "-y",
                        file_path  # Đường dẫn lưu video sau xử lý
                    ]
                    subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                    # Sau khi xử lý xong, xóa tệp tạm
                    os.remove(file_cache)

                    with self.lock:  # Đảm bảo cập nhật self.downloaded_count một cách an toàn
                        self.downloaded_count += 1
                    logging.info(f"[{index}] Tải thành công: {file_name} ({file_size/1024/1024:.2f}MB)")
                    logging.info(f"Đã tải {self.downloaded_count}/{self.max_videos} video.")
                    return True
                else:
                    logging.warning(f"[{index}] File rỗng: {file_name}")
                    return False

            except requests.exceptions.RequestException as e:
                logging.error(f"[{index}] Lỗi khi tải video (Lần {attempt}): {file_name} - {str(e)}")
                if attempt == max_retries:
                    logging.warning(f"[{index}] Đổi URL sau {max_retries} lần thử.")
        return False

    def download_videos(self, max_workers: int = 4):
        all_urls = self.load_urls()
        index = 1

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = set()

            while all_urls and self.downloaded_count < self.max_videos:
                item = all_urls.pop()
                if item['url'] in self.selected_urls or self.is_file_downloaded(item['url']):
                    continue

                future = executor.submit(self.download_single_video, item, index)
                futures.add(future)
                index += 1

                # Kiểm tra và dừng nếu đã đạt đủ số lượng
                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                for f in done:
                    if self.downloaded_count >= self.max_videos:
                        logging.info(f"Đã đạt số lượng yêu cầu {self.max_videos} video. Dừng tải.")
                        for future in futures:
                            future.cancel()
                        return
                    futures.remove(f)
        
        logging.info(f"Tải thành công {self.downloaded_count} video vào thư mục '{self.output_dir}'")


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


def download_file(output_path):
    url = os.getenv('url_web') + '/render/down_load_screen/'
    
    # Gửi yêu cầu GET và lấy tệp
    response = requests.get(url, stream=True,timeout=500)
    
    # Kiểm tra nếu yêu cầu thành công
    if response.status_code == 200:
        # Lấy kích thước tệp
        total_size = int(response.headers.get('content-length', 0))
        
        # Mở tệp để ghi dữ liệu
        with open(output_path, 'wb') as file:
            # Tạo tiến độ với tqdm
            with tqdm(total=total_size, unit='B', unit_scale=True) as bar:
                downloaded_size = 0  # Khởi tạo biến để theo dõi số byte đã tải
                previous_percent = 0  # Biến để lưu trữ phần trăm đã in trước đó
                
                for chunk in response.iter_content(chunk_size=20 * 1024 * 1024):
                    if chunk:
                        file.write(chunk)  # Ghi chunk vào tệp
                        downloaded_size += len(chunk)  # Cập nhật số byte đã tải
                        bar.update(len(chunk))  # Cập nhật tiến độ

                        # Tính toán phần trăm đã tải xuống và làm tròn về số nguyên
                        percent_done = (downloaded_size / total_size) * 100
                        percent_done_int = int(percent_done)  # Làm tròn phần trăm về số nguyên
                        
                        # Chỉ in nếu phần trăm thay đổi hoặc lớn hơn 1%
                        if percent_done_int - previous_percent >= 1:
                            print(f"Đang tải {output_path}... {percent_done_int}%")
                            previous_percent = percent_done_int  # Cập nhật giá trị phần trăm trước đó
        
        print(f"Tải xuống hoàn tất! Tệp được lưu tại {output_path}")
    else:
        print(f"Lỗi khi tải tệp: {response.status_code}")

def unzip_with_progress(zip_file_path):
    # Kiểm tra nếu thư mục đích không tồn tại thì tạo mới
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Mở file zip và giải nén
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        # Lấy danh sách các file trong zip
        total_files = len(zip_ref.namelist())
        
        # Giải nén từng file và hiển thị tiến độ
        for i, file in enumerate(zip_ref.namelist()):
            zip_ref.extract(file)
            
            # Tính toán phần trăm và hiển thị
            percent_done = (i + 1) / total_files * 100
            print(f"Đang giải nén {file}... {percent_done:.2f}%")

    print(f"Đã giải nén thành công vào thư mục {output_dir}")


def get_local_ip():
    try:
        for interface in netifaces.interfaces():
            addresses = netifaces.ifaddresses(interface)
            # Kiểm tra IPv4 trong các interface
            if netifaces.AF_INET in addresses:
                for addr in addresses[netifaces.AF_INET]:
                    ip = addr.get('addr')
                    # Kiểm tra nếu IP thuộc dải 192.168.x.x hoặc 10.x.x.x (mạng LAN)
                    if ip.startswith('192.168.') or ip.startswith('10.') or ip.startswith('172.'):
                        return ip
        return None
    except Exception as e:
        print(f"Error getting local IP: {e}")
        return None

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


# Main function
if __name__ == "__main__":
    print("đang xử lý ...")
    output_dir = 'video'
    json_file = 'filtered_data.json'
    directory_path = "media"
    ip_puplic = get_public_ip()
    local_ip = get_local_ip()
    if os.path.exists(directory_path):
        shutil.rmtree(directory_path)  # Xóa thư mục và tất cả nội dung bên trong, kể cả khi nó trống
        print(f"Đã xóa thư mục: {directory_path}")
    else:
        print(f"Thư mục {directory_path} không tồn tại.")

    # Tạo thư mục video nếu chưa tồn tại
    if not os.path.exists(output_dir):
        downloader = VideoDownloader(json_file=json_file, output_dir=output_dir, max_videos=3000)
        downloader.download_videos(max_workers=20)
        # Xóa thư mục tạm sau khi tải xong
        shutil.rmtree("chace_video", ignore_errors=True)
    else:
        print("Có video rồi không cần tải nữa !")
    
    os.system(f"celery -A celeryworker worker -l INFO --hostname=IPV4:{ip_puplic}/IP_LOCLAL:{local_ip} --concurrency={os.getenv('Luong_Render')} -Q {os.getenv('Task_Render')} --prefetch-multiplier=1")


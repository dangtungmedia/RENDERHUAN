import os
import json
import random
import requests
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import List, Dict
import logging
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from threading import Lock
import shutil
import zipfile
import sys
from tqdm import tqdm

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
        file_cache = Path(temp_dir) / file_name
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
                        "ffmpeg", "-hwaccel", "cuda", "-hwaccel_output_format", "cuda", "-i", str(file_cache),
                        "-vf", "scale_cuda=1280:720", "-r", "24", "-c:v", "hevc_nvenc", "-preset", "fast", str(file_path)
                    ]
                    subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    os.remove(file_cache)

                    with self.lock:
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

                done, _ = wait(futures, return_when=FIRST_COMPLETED)
                for f in done:
                    if self.downloaded_count >= self.max_videos:
                        logging.info(f"Đã đạt số lượng yêu cầu {self.max_videos} video. Dừng tải.")
                        for future in futures:
                            future.cancel()
                        return
                    futures.remove(f)

        logging.info(f"Tải thành công {self.downloaded_count} video vào thư mục '{self.output_dir}'")

# Hàm tải tệp và giải nén
def download_file(url, output_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        total_size = int(response.headers.get('content-length', 0))
        with open(output_path, 'wb') as file:
            with tqdm(total=total_size, unit='B', unit_scale=True) as bar:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        file.write(chunk)
                        bar.update(len(chunk))
        print(f"Tải xuống hoàn tất! Tệp được lưu tại {output_path}")
    else:
        print(f"Lỗi khi tải tệp: {response.status_code}")

def unzip_with_progress(zip_file_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        total_files = len(zip_ref.namelist())
        for i, file in enumerate(zip_ref.namelist()):
            zip_ref.extract(file, output_dir)
            percent_done = (i + 1) / total_files * 100
            print(f"Đang giải nén {file}... {percent_done:.2f}%")
    print(f"Đã giải nén thành công vào thư mục {output_dir}")

# Main function
if __name__ == "__main__":
    output_dir = 'video'
    json_file = 'filtered_data.json'
    
    if not os.path.exists(output_dir):
        downloader = VideoDownloader(json_file=json_file, output_dir=output_dir, max_videos=1)
        downloader.download_videos(max_workers=20)
        shutil.rmtree("chace_video", ignore_errors=True)
    else:
        print("Có video rồi không cần tải nữa !")

    video_screen = "video_screen"
    if not os.path.exists(video_screen):
        download_file("URL_CỦA_BẠN", video_screen)  # Gọi đúng URL để tải tệp
        unzip_with_progress('video_screen.zip', video_screen)
        os.remove('video_screen.zip')
    else:
        print("Có video Screen rồi không cần tải nữa !")

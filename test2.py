import requests
import os
from urllib.parse import urlparse
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def download_video(url, max_retries=3):
    # Headers giả lập trình duyệt
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'video/webm,video/mp4,video/*;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://pixabay.com/'
    }

    # Cấu hình retry
    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=1,  # Tăng thời gian chờ giữa các lần retry
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    try:
        file_name = os.path.basename(urlparse(url).path)
        print(f"Đang tải: {file_name}")

        # Thêm delay trước khi request
        time.sleep(2)  

        response = session.get(url, headers=headers, stream=True)
        response.raise_for_status()

        os.makedirs('videos', exist_ok=True)
        file_path = os.path.join('videos', file_name)

        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print(f"Đã tải xong: {file_name}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi tải video: {str(e)}")
        if response.status_code == 429:
            print("Đang chờ 60 giây trước khi thử lại...")
            time.sleep(60)  # Chờ 60 giây nếu gặp lỗi 429
        return False

# URL video
url = "https://cdn.pixabay.com/video/2019/05/24/23914-338327820_tiny.mp4"

# Thử tải với retry
attempt = 1
while attempt <= 3:
    print(f"\nLần thử {attempt}:")
    if download_video(url):
        break
    attempt += 1
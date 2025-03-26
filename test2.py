from threading import Lock  # Thay asyncio.Lock bằng threading.Lock
import logging
import time
import requests

class HttpClient:
    def __init__(self, url, min_delay=1.0):
        self.url = url  # Endpoint API URL
        self.lock = Lock()  # Sử dụng threading.Lock thay vì asyncio.Lock
        self.last_send_time = 0
        self.min_delay = min_delay
        
        # Status messages that bypass rate limiting
        self.important_statuses = [
            "Render Thành Công : Đang Chờ Upload lên Kênh",
            "Đang Render : Upload file File Lên Server thành công!",
            "Đang Render : Đang xử lý video render",
            "Đang Render : Đã lấy thành công thông tin video reup",
            "Đang Render : Đã chọn xong video nối",
            "Render Lỗi"
        ]
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Setup logging configuration"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        return logger
        
    def should_send(self, status):
        """Check if message should be sent based on status and rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_send_time

        # Check if status contains any important keywords
        if status and any(keyword in status for keyword in self.important_statuses):
            return True
            
        # Apply rate limiting for other statuses
        return time_since_last >= self.min_delay
        
    def send(self, data, file_data=None, max_retries=3):
        """Send data through HTTP request with rate limiting and retries."""
        with self.lock:  # threading.Lock hỗ trợ with trong ngữ cảnh đồng bộ
            try:
                status = data.get('status')
                
                if not self.should_send(status):
                    return True
                    
                for attempt in range(max_retries):
                    try:
                        if file_data:
                            response = requests.post(self.url, data=data, files=file_data, timeout=10)
                        else:
                            response = requests.post(self.url, json=data, timeout=10)

                        if response.status_code == 200:
                            self.last_send_time = time.time()
                            self.logger.info(f"Successfully sent message: {status}")
                            return True
                        else:
                            self.logger.error(f"Failed to send message: {response.status_code} - {response.text}")
                        
                    except requests.Timeout:
                        self.logger.error(f"Timeout on attempt {attempt + 1}")
                    except requests.RequestException as e:
                        self.logger.error(f"Request failed: {str(e)}")
                        
                    sleep_time = min(2 ** attempt, 10)  # Exponential backoff
                    time.sleep(sleep_time)
                
                self.logger.error(f"Failed to send after {max_retries} attempts")
                return False
                
            except Exception as e:
                self.logger.error(f"Error in send method: {str(e)}")
                return False

http_client = HttpClient(url="http://127.0.0.1:8000" + "/api/")
def update_status_video(status_video, video_id, task_id, worker_id, url_thumnail=None, url_video=None, title=None, id_video_google=None):
    data = {
        'action': 'update_status',
        'video_id': video_id,
        'status': status_video,
        'task_id': task_id,
        'worker_id': worker_id,
        'title': title,
        'url_video': url_video,
        'id_video_google': id_video_google,
        "secret_key": "ugz6iXZ.fM8+9sS}uleGtIb,wuQN^1J%EvnMBeW5#+CYX_ej&%"
    }
    
    if url_thumnail:
        try:
            with open(url_thumnail, 'rb') as f:
                data_file = {'thumbnail': f}  # Sửa key từ 'thumnail' thành 'thumbnail'
                http_client.send(data, file_data=data_file)
        except FileNotFoundError:
            logging.error(f"File not found: {url_thumnail}")
    else:
        http_client.send(data)

# Test
status_video = "Đang Render : Đã chọn xong video nối"
video_id = 410537
task_id = 456
worker_id = 789
url_thumnail = "anh-co-gai-xinh-dep-4.jpg"
url_video = "https://drive.google.com/file/d/1Oa-NYcoC6maEJ6ff0mfPF6N2ebSfLPe1/view"
title = "Video Title"
id_video_google = "abc123"
update_status_video(
    "Đang Render : Upload file File Lên Server thành công!", 
    video_id, 
    task_id, 
    worker_id,
    url_video=url_video,
    id_video_google=id_video_google
)
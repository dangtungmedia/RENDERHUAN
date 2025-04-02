from celery import Celery
import os
from dotenv import load_dotenv
load_dotenv()

# Tạo ứng dụng Celery với tên 'celeryworker'
app = Celery('celeryworker')

# Tự động tìm kiếm và nạp các task từ các module chỉ định trong package 'celeryworker'
app.autodiscover_tasks(['celeryworker'])

# Thiết lập timezone cho Celery
app.conf.timezone = 'Asia/Ho_Chi_Minh'  # Sử dụng đúng cú pháp với chữ hoa
broker_url  =  os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0' )
result_backend  = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')

# Các cấu hình khác
app.conf.worker_timeout = 120
#thời gian chờ giữa các lần kiểm tra worker
app.conf.worker_heartbeat_interval = 30
app.conf.broker_connection_retry_on_startup = True
app.conf.accept_content = ['json']
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'

app.conf.task_track_started = True
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late=True,  # Xác nhận task khi hoàn thành
app.conf.task_reject_on_worker_lost=True,  # Từ chối task nếu worker bị mất kết nối
app.conf.worker_cancel_long_running_tasks_on_exit=True,  # Hủy task nếu worker bị dừng
app.conf.broker_connection_retry_on_startup = True

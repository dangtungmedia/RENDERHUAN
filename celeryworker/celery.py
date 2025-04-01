from celery import Celery
import os
from dotenv import load_dotenv

# Nạp biến môi trường từ file .env
load_dotenv()

# Tạo ứng dụng Celery với tên 'celeryworker'
app = Celery('celeryworker')

app.conf.broker_url= os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
app.conf.result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
app.conf.accept_content= ['json']
app.conf.task_serializer= 'json'
app.conf.result_serializer='json'
app.conf.timezone='Asia/Ho_Chi_Minh'
app.conf.enable_utc=True
app.conf.task_track_started=True
app.conf.task_ignore_result=False
app.conf.task_result_extended=True
app.conf.cache_backend='default'
app.conf.broker_connection_retry_on_startup=True
app.conf.worker_prefetch_multiplier = 1

# Tự động tìm kiếm và nạp các task từ các module chỉ định trong package 'celeryworker'
app.autodiscover_tasks(['celeryworker'])
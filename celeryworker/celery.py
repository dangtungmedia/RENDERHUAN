from celery import Celery
import os
from dotenv import load_dotenv
load_dotenv()

# Tạo ứng dụng Celery với tên 'celeryworker'
app = Celery('celeryworker')

# Tự động tìm kiếm và nạp các task từ các module chỉ định trong package 'celeryworker'
app.autodiscover_tasks(['celeryworker'])
app.conf.broker_url = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0' )
app.conf.result_backend = os.environ.get('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
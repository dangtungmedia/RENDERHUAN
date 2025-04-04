import os
import ssl
from celery import shared_task, Celery
import os, shutil, urllib
import time
import requests
import websocket
import json
from PIL import Image, ImageDraw, ImageFont
import asyncio
import math
import urllib
import edge_tts, random, subprocess
import asyncio, json, shutil
from googletrans import Translator
import math
from datetime import timedelta, datetime
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
import re
from datetime import datetime, timedelta
import re
import yt_dlp
import os
import random, subprocess
from decimal import Decimal
from proglog import ProgressBarLogger
from tqdm import tqdm
from celery.signals import task_failure,task_revoked
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from dotenv import load_dotenv
import psutil
import boto3
import threading
from threading import Lock
import logging
import urllib.parse
from urllib.parse import urlparse
import asyncio
import aiohttp
from typing import Dict, Set, List, Tuple, Optional
import os
import asyncio
import aiofiles
import aioboto3
import botocore
import os
import re
import time
from urllib import request
from urllib.error import URLError, HTTPError

from urllib.parse import urlparse
from time import sleep
# Nạp biến môi trường từ file .env
load_dotenv()

SECRET_KEY=os.environ.get('SECRET_KEY')
SERVER=os.environ.get('SERVER')
ACCESS_TOKEN = None
failed_accounts: Set[str] = set()
valid_tokens: Dict[str, str] = {}


def delete_directory(video_id):
    directory_path = f'media/{video_id}'
    
    # Kiểm tra nếu thư mục tồn tại
    if os.path.exists(directory_path):
        # Kiểm tra xem thư mục có trống không
        if not os.listdir(directory_path):
            try:
                # Nếu thư mục trống, dùng os.rmdir để xóa
                # os.rmdir(directory_path)
                print(f"Đã xóa thư mục trống: {directory_path}")
            except Exception as e:
                print(f"Lỗi khi xóa thư mục {directory_path}: {e}")
        else:
            try:
                # Nếu thư mục không trống, dùng shutil.rmtree để xóa toàn bộ
                shutil.rmtree(directory_path)
                print(f"Đã xóa thư mục cùng với các tệp: {directory_path}")
            except Exception as e:
                print(f"Lỗi khi xóa thư mục {directory_path}: {e}")
    else:
        print(f"Thư mục {directory_path} không tồn tại.")

# Xử lý khi task gặp lỗi
@task_failure.connect
def task_failure_handler(sender, task_id, exception, args, kwargs, traceback, einfo, **kw):
    video_id = args[0].get('video_id')
    worker_id = "None"
    update_status_video(f"Render Lỗi : {os.getenv('name_woker')}{os.getenv('name_woker')} Xử Lý Video Không Thành Công!", video_id, task_id, worker_id)
    delete_directory(video_id)
# Xử lý khi task bị hủy

@task_revoked.connect
def clean_up_on_revoke(sender, request, terminated, signum, expired, **kw):
    task_id = request.id
    worker_id = "None"
    print(f"Task {task_id} bị hủy.")
    print(kw)
    if request.args:
        video_id = request.args[0].get('video_id')
        delete_directory(video_id)
    else:
        print(f"Không thể tìm thấy video_id cho task {task_id} vì không có args.")
    update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  dừng render!", video_id, task_id, worker_id)

@shared_task(bind=True, priority=0,name='render_video',time_limit=14200,queue='render_video_content')
def render_video(self, data):
    task_id = self.request.id  # Sử dụng self.request thay vì render_video_reupload.request
    worker_id = self.request.hostname 
    video_id = data.get('video_id')
    
    update_status_video("Đang Render : Đang xử lý video render", data['video_id'], task_id, worker_id)
    success = create_or_reset_directory(f'media/{video_id}')
    
    if not os.path.exists("video")  and not os.path.exists("video_screen") :
        update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  Thiếu các tệp video  và  video_screen ", data['video_id'], task_id, worker_id)
        return

    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  Không thể tạo thư mục", data['video_id'], task_id, worker_id)
        return
    update_status_video("Đang Render : Tạo thư mục thành công", data['video_id'], task_id, worker_id)

    # Tải xuống hình ảnh
    success = download_image(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  Không thể tải xuống hình ảnh", data['video_id'], task_id, worker_id)
        return

    update_status_video("Đang Render : Tải xuống hình ảnh thành công", data['video_id'], task_id, worker_id)
    #THử
    if not data.get('url_audio'):
        # Tải xuống âm thanh oki
        success = download_audio(data, task_id, worker_id)
        if not success:
            shutil.rmtree(f'media/{video_id}')
            return
        print(f"Tải xuống âm thanh thành công {success}!")
        print(f"Tải xuống âm thanh thành công {success}!")
    time.sleep(1)
    update_status_video("Đang Render : Nối giọng đọc và chèn nhạc nền thành công", data['video_id'], task_id, worker_id)
    # Tạo video
    success = create_video_lines(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    
    # Tạo phụ đề cho video
    success = create_subtitles(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    
    # Tạo file
    success = create_video_file(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    
    success = upload_video(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  Không thể upload video", data['video_id'], task_id, worker_id)
        return
    shutil.rmtree(f'media/{video_id}')
    update_status_video(f"Render Thành Công : Đang Chờ Upload lên Kênh", data['video_id'], task_id, worker_id)

@shared_task(bind=True, priority=1,name='render_video_reupload',time_limit=140000,queue='render_video_reupload')
def render_video_reupload(self, data):
    task_id = self.request.id  # Sử dụng self.request thay vì render_video_reupload.request
    worker_id = self.request.hostname 
    video_id = data.get('video_id')
    # Kiểm tra xem task có bị hủy không ngay từ đầu
    update_status_video("Đang Render : Đang xử lý video render", data['video_id'], task_id, worker_id)
    
    if not os.path.exists("video")  and not os.path.exists("video_screen") :
        update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  Thiếu các tệp video  và  video_screen ", data['video_id'], task_id, worker_id)
        return
    
    success = create_or_reset_directory(f'media/{video_id}')
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    
    success = update_info_video(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    
    success = cread_test_reup(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    
    success = upload_video(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    shutil.rmtree(f'media/{video_id}')
    update_status_video(f"Render Thành Công : Đang Chờ Upload lên Kênh", data['video_id'], task_id, worker_id)

def seconds_to_hms(seconds):
    hours = seconds // 3600  # Tính giờ
    minutes = (seconds % 3600) // 60  # Tính phút
    seconds = seconds % 60  # Tính giây
    return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"  # Định dạng: HH:MM:SS

def cread_test_reup(data, task_id, worker_id):
    video_dir = "video"
    video_id = data.get('video_id')
    video_path = f'media/{video_id}/cache.mp4'

    time_video = get_video_duration(video_path)
    speed = data.get('speed_video_crop', 1.0)
    if isinstance(speed, Decimal):
        speed = float(speed)
    duration = time_video / speed  # Thời gian video sau khi thay đổi tốc độ
    video_files = [os.path.join(video_dir, f) for f in os.listdir(video_dir) if f.endswith(('.mp4', '.mkv', '.avi'))]
    
    if not video_files:
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} không có video để render ", video_id, task_id, worker_id)
        return None

    selected_videos = []
    total_duration = 0
    remaining_videos = set(video_files)
    update_status_video("Đang Render: Đang Chọn video random", video_id, task_id, worker_id)

    while total_duration < duration and remaining_videos:
        video = random.choice(list(remaining_videos))  # Chọn ngẫu nhiên video
        remaining_videos.remove(video)  # Loại khỏi danh sách chưa chọn
        try:
            video_duration = get_video_duration(video)
            selected_videos.append(video)
            total_duration += video_duration
            # Chuyển đổi tổng thời gian từ giây thành giờ:phút:giây
            formatted_duration = seconds_to_hms(total_duration)
            formatted_limit = seconds_to_hms(duration)
            update_status_video(f"Đang Render: Thời lượng videos {formatted_duration}/{formatted_limit}", video_id, task_id, worker_id)
        except Exception as e:
            print(f"Lỗi khi đọc thời gian video {video}: {e}")

    if total_duration < duration:
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} Không thể chọn đủ video để vượt qua thời lượng yêu cầu.", video_id, task_id, worker_id)
        return None
    update_status_video("Đang Render: Đã chọn xong video nối", video_id, task_id, worker_id)
    
    # Tạo tệp danh sách video để nối
    output_file_list = f'media/{video_id}/output_files.txt'
    os.makedirs(os.path.dirname(output_file_list), exist_ok=True)
    
    try:
        with open(output_file_list, 'w') as f:
            for video in selected_videos:
                full_path = os.path.abspath(video)
                if os.path.exists(full_path):
                    f.write(f"file '{full_path}'\n")
                else:
                    print(f"Warning: Video không tồn tại - {full_path}")
    except Exception as e:
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} Không thể tạo danh sách video {str(e)}", video_id, task_id, worker_id)
        return False

    # Lấy dữ liệu crop từ tham số
    video_path_audio = f'media/{video_id}/cache.mp4'
    crop_data_str = data.get('location_video_crop')
    crop_data = parse_crop_data(crop_data_str)
    original_resolution = (640, 360)  # Độ phân giải gốc
    target_resolution = (1280, 720)  # Độ phân giải mục tiêu
    left, top, width, height = calculate_new_position(crop_data, original_resolution, target_resolution)
    opacity = 0.6
    speed = data.get('speed_video_crop', 1.0)
    pitch = data.get('pitch_video_crop', 1.0)
    name_video = data.get('name_video')
    output_path = f'media/{video_id}/{name_video}.mp4'

    # Lệnh ffmpeg để nối video và áp dụng các hiệu ứng
    ffmpeg_command = [
        "ffmpeg",
        "-f", "concat",
        "-safe", "0",
        "-i", output_file_list,
        "-i", video_path_audio,
        "-filter_complex", (
            f"[1:v]fps=24,scale=1280:720,setpts={1/speed}*PTS,crop={width}:{height}:{left}:{top},format=rgba,colorchannelmixer=aa={opacity}[blurred];"
            f"[1:a]asetrate={44100 * pitch},atempo={speed}[a];"
            f"[0:v][blurred]overlay={left}:{top}[outv]"
        ),
        "-map", "[outv]",
        "-map", "[a]",
        "-c:v", "libx265",
        "-c:a", "aac",  # Đảm bảo codec âm thanh là AAC
        "-b:a", "192k",  # Bitrate âm thanh hợp lý
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    
    try:
        # Khởi tạo lệnh ffmpeg và đọc output
        with subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            total_duration = None
            progress_bar = None

            # Read the stderr output line by line
            for line in process.stderr:
                print(f"ffmpeg output: {line.strip()}")  # Log the ffmpeg output for debugging
                if "Duration" in line:
                    try:
                        duration_str = line.split(",")[0].split("Duration:")[1].strip()
                        h, m, s = map(float, duration_str.split(":"))
                        total_duration = int(h * 3600 + m * 60 + s)
                        progress_bar = tqdm(total=total_duration, desc="Rendering", unit="s")
                    except ValueError as e:
                        print(f"Error parsing duration: {e}")
                        continue

                if "time=" in line and progress_bar:
                    time_str = line.split("time=")[1].split(" ")[0].strip()
                    if time_str != 'N/A':
                        try:
                            h, m, s = map(float, time_str.split(":"))
                            current_time = int(h * 3600 + m * 60 + s)
                            progress_bar.n = current_time
                            progress_bar.refresh()
                            percentage = int((current_time / total_duration) * 100)
                            if percentage <= 100:
                                update_status_video(f"Đang Render: xuất video thành công {percentage}%", data['video_id'], task_id, worker_id)
                        except ValueError as e:
                            print(f"Skipping invalid time format: {time_str}, error: {e}")
                            print(f"Lỗi khi chạy lệnh ffmpeg: {str(e)}")
            process.wait()
    except Exception as e:
        print(f"Lỗi khi chạy lệnh ffmpeg: {str(e)}")
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} Lỗi khi thực hiện lệnh ffmpeg - {str(e)}", video_id, task_id, worker_id)
        return False
    
    # Kiểm tra tệp kết quả
    if os.path.exists(output_path) and os.path.getsize(output_path) > 0 and get_video_duration(output_path):
        update_status_video("Đang Render: Xuất video xong ! chuẩn bị upload lên sever", data['video_id'], task_id, worker_id)
        return True
    else:
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} Lỗi xuất video bằng ffmpeg vui lòng chạy lại ,file xuất lỗi", data['video_id'], task_id, worker_id)
        return False

def select_videos_by_total_duration(file_path, min_duration):
    # Đọc dữ liệu từ tệp JSON
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    total_duration = 0
    selected_urls = []

    # Tiến hành chọn ngẫu nhiên các video cho đến khi tổng duration lớn hơn min_duration
    while total_duration <= min_duration:
        # Chọn ngẫu nhiên một video từ danh sách
        
        video = random.choice(data)
        
        # Cộng thêm duration vào tổng duration
        total_duration += video['duration']
        
        # Thêm url vào danh sách các URL
        selected_urls.append(video['url'])  # Lấy URL của video
        
        # Loại bỏ video đã chọn khỏi danh sách để không chọn lại
        data.remove(video)
    
    return selected_urls


async def upload_video_async(data, task_id, worker_id):
    video_id = data.get('video_id')
    name_video = data.get('name_video')
    video_path = f'media/{video_id}/{name_video}.mp4'
    
    class ProgressPercentage:
        def __init__(self, filename):
            self._filename = filename
            self._size = float(os.path.getsize(filename))
            self._seen_so_far = 0
            self._lock = threading.Lock()

        def __call__(self, bytes_amount):
            with self._lock:
                self._seen_so_far += bytes_amount
                percentage = (self._seen_so_far / self._size) * 100
                # Format size thành MB
                total_mb = self._size / (1024 * 1024)
                uploaded_mb = self._seen_so_far / (1024 * 1024)
                update_status_video(
                    f"Đang Render : Đang Upload File Lên Server ({percentage:.1f}%) - {uploaded_mb:.1f}MB/{total_mb:.1f}MB", 
                    video_id, 
                    task_id, 
                    worker_id
                )
    
    max_retries = 5  # Số lần thử lại tối đa
    attempt = 0
    success = False

    while attempt < max_retries and not success:
        try:
            # Sử dụng aioboto3 để upload không đồng bộ
            session = aioboto3.Session()
            async with session.client(
                's3',
                endpoint_url=os.environ.get('S3_ENDPOINT_URL'),
                aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
            ) as s3:
                
                bucket_name = os.environ.get('S3_BUCKET_NAME')
                
                # Kiểm tra file tồn tại
                if not os.path.exists(video_path):
                    error_msg = f"Không tìm thấy file {video_path}"
                    update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  {error_msg}", video_id, task_id, worker_id)
                    return False

                object_name = f'data/{video_id}/{name_video}.mp4'
                
                # Tạo progress callback
                progress_callback = ProgressPercentage(video_path)
                
                # Upload file không đồng bộ
                with open(video_path, 'rb') as file:
                    await s3.upload_fileobj(
                        file, 
                        bucket_name, 
                        object_name,
                        Callback=progress_callback,
                        ExtraArgs={
                            'ContentType': 'video/mp4',
                            'ContentDisposition': 'inline'
                        }
                    )
                
                # Tạo URL có thời hạn 1 năm và cấu hình để xem trực tiếp
                expiration = 365 * 24 * 60 * 60
                url = await s3.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket_name,
                        'Key': object_name,
                        'ResponseContentType': 'video/mp4',
                        'ResponseContentDisposition': 'inline'
                    },
                    ExpiresIn=expiration
                )
                print(f"Uploaded video to {url}")
                update_status_video(
                    "Đang Render : Upload file File Lên Server thành công!", 
                    video_id, 
                    task_id, 
                    worker_id,
                    url_video=url,
                    id_video_google=object_name
                )
                success = True
                return True

        except asyncio.CancelledError:
            # Xử lý khi task bị hủy
            update_status_video(
                "Render Dừng : Upload file bị hủy", 
                video_id, 
                task_id, 
                worker_id
            )
            return False
        
        except FileNotFoundError as e:
            error_msg = str(e)
            update_status_video(f"Render Lỗi : {os.getenv('name_woker')} File không tồn tại - {error_msg[:20]}", video_id, task_id, worker_id)
            break  # Nếu file không tồn tại, dừng thử
        
        except Exception as e:
            error_msg = str(e)
            update_status_video(f"Render Lỗi : {os.getenv('name_woker')} Lỗi khi upload {error_msg[:20]}", video_id, task_id, worker_id)
            attempt += 1
            
            if attempt < max_retries:
                # Nếu còn lượt thử lại, đợi một chút rồi thử lại
                update_status_video(f"Render Lỗi : {os.getenv('name_woker')} Thử lại lần {attempt + 1}", video_id, task_id, worker_id)
                await asyncio.sleep(3)  # Đợi 3 giây trước khi thử lại
    return False

# Hàm wrapper để chạy upload không đồng bộ
async def run_async_upload(data, task_id, worker_id):
    try:
        return await upload_video_async(data, task_id, worker_id)
    except Exception as e:
        print(f"Async upload error: {e}")
        return False

# Hàm đồng bộ để tương thích với mã cũ
def upload_video(data, task_id, worker_id):
    return asyncio.run(run_async_upload(data, task_id, worker_id))

def get_total_duration_from_ass(ass_file_path):
    """Lấy tổng thời gian từ file .ass dựa trên thời gian kết thúc của dòng Dialogue cuối cùng"""
    total_duration = 0
    time_pattern = re.compile(r"Dialogue:.*?,(\d{1,2}:\d{2}:\d{2}\.\d{2}),(\d{1,2}:\d{2}:\d{2}\.\d{2})")

    try:
        with open(ass_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            for line in reversed(lines):  # Đọc từ dưới lên để tìm dòng Dialogue cuối cùng
                match = time_pattern.search(line)
                if match:
                    _, end_time = match.groups()
                    print(f"End Time Found: {end_time}")  # In giá trị end_time để kiểm tra
                    # Chuyển đổi thời gian kết thúc (End) thành giây
                    time_parts = end_time.split(':')
                    if len(time_parts) == 3:
                        h, m, s = time_parts
                        # Tách phần giây thập phân từ giây
                        s, ms = s.split('.')
                        h, m, s = map(float, (h, m, s))
                        ms = float(f"0.{ms}")  # Giới hạn phần thập phân của giây
                        total_duration = h * 3600 + m * 60 + s + ms
                        break  # Thoát ngay sau khi tìm thấy dòng Dialogue cuối cùng
                    else:
                        print(f"Unexpected end_time format: {end_time}")
                        return 0  # Trả về 0 nếu định dạng không hợp lệ
    except Exception as e:
        print(f"Error reading .ass file: {e}")
        return 0
    
    return total_duration

def create_video_file(data, task_id, worker_id):
    video_id = data.get('video_id')
    name_video = data.get('name_video')
    text = data.get('text_content')

    update_status_video("Đang Render : Đang nghép video và phụ đề", data['video_id'], task_id, worker_id)

    # Tạo file subtitles.ass
    ass_file_path = f'media/{video_id}/subtitles.ass'
    # Tạo file input_files_video.txt
    input_files_video_path = f'media/{video_id}/input_files_video.txt'
    os.makedirs(os.path.dirname(input_files_video_path), exist_ok=True)
    
    with open(input_files_video_path, 'w') as file:
        for item in json.loads(text):
            file.write(f"file 'video/{item['id']}.mp4'\n")
            # Thêm thông tin về hiệu ứng chuyển cảnh

    duration = get_total_duration_from_ass(ass_file_path)

    ffmpeg_command = [
        'ffmpeg',
        '-f', 'concat',                    # Chế độ kết hợp video
        '-safe', '0',                       # Cho phép đường dẫn không an toàn (chẳng hạn như file với đường dẫn tuyệt đối)
        '-i', input_files_video_path,       # Đường dẫn tệp video đầu vào (danh sách video)
        '-vf', f"subtitles={ass_file_path}",# Đường dẫn tệp phụ đề ASS
        "-c:v", "libx265",
        "-y",
        f"media/{video_id}/{name_video}.mp4" # Đường dẫn và tên file đầu ra
    ]
    # Chạy lệnh ffmpeg và xử lý đầu ra
    with subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
        for line in process.stderr:
            if "time=" in line:
                try:
                    time_str = line.split("time=")[1].split(" ")[0].strip()
                    if time_str == "N/A":
                        continue  # Bỏ qua nếu không có thông tin thời gian
                    h, m, s = map(float, time_str.split(":"))
                    current_time = int(h * 3600 + m * 60 + s)
                    percentage = (current_time / duration) * 100
                    update_status_video(f"Đang Render: Đã xuất video {percentage:.2f}%", video_id, task_id, worker_id)
                except Exception as e:
                    print(f"Error parsing time: {e}")
                    update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  Không thể tính toán hoàn thành", data['video_id'], task_id, worker_id)
        process.wait()
            
    if process.returncode != 0:
        print("FFmpeg encountered an error.")
        stderr_output = ''.join(process.stderr)
        print(f"Error log:\n{stderr_output}")
        update_status_video(f"Render Lỗi : {os.getenv('name_woker')} không thể render video hoàn thành ", data['video_id'], task_id, worker_id)
        return False
    else:
        print("Lồng nhạc nền thành công.")
        update_status_video(f"Đang Render: Đã xuất video và chèn nhạc nền thành công , chuẩn bị upload lên sever", video_id, task_id, worker_id)
        return True

def find_font_file(font_name, font_dir, extensions=[".ttf", ".otf", ".woff", ".woff2"]):
    print(f"Searching for font '{font_name}' in directory '{font_dir}' with extensions {extensions}")
    for root, dirs, files in os.walk(font_dir):
        print(f"Checking directory: {root}")
        for file in files:
            print(f"Found file: {file}")
            if any(file.lower() == f"{font_name.lower()}{ext}" for ext in extensions):
                print(f"Matched font file: {file}")
                return os.path.join(root, file)
    print(f"Font '{font_name}' not found in directory '{font_dir}'")
    return None

def get_text_lines(data, text,width=1920):
    current_line = ""
    wrapped_text = ""
    font = data['font_name']
    # font_text = find_font_file(font, r'fonts')

    font_size = data.get('font_size')

    font = ImageFont.truetype(font,font_size)

    img = Image.new('RGB', (1, 1), color='black')

    draw = ImageDraw.Draw(img)

    for char in text:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        # Kiểm tra nếu thêm dấu câu vào dòng mới vẫn giữ cho chiều rộng trên 50%
        if text_width <= width:
            current_line = test_line
        else:
            # Nếu chiều rộng vượt quá giới hạn, tìm vị trí của dấu câu cuối cùng
            last_punctuation_index = find_last_punctuation_index(current_line)
            if last_punctuation_index != -1:
                text_1 = current_line[:last_punctuation_index + 1]
                text_2 = current_line[last_punctuation_index + 1:]

                bbox_1 = draw.textbbox((0, 0), text_1, font=font)
                text_width_1 = bbox_1[2] - bbox_1[0]

                if text_width_1 <= int(width / 2):
                    text_count = find_last_punctuation_index(text_2)

                    if text_count != -1:
                        wrapped_text += text_1 + text_2[:text_count + 1] + "\\n"
                        current_line = text_2[text_count + 1:]
                    else:
                        wrapped_text += current_line + "\\n"
                        current_line = char
                else:
                    wrapped_text += text_1 + "\\n"
                    current_line = text_2
            else:
                # Nếu không tìm thấy dấu câu, thêm toàn bộ dòng vào danh sách
                wrapped_text += current_line + "\\n"
                current_line = char

    wrapped_text += current_line
    return wrapped_text

def find_last_punctuation_index(line):
    punctuation = "。、！？.,"  # Các dấu câu có thể xem xét
    last_punctuation_index = -1

    for i, char in enumerate(reversed(line)):
        if char in punctuation:
            last_punctuation_index = len(line) - i - 1
            break
    return last_punctuation_index

def format_timedelta_ass(ms):
    # Định dạng thời gian cho ASS
    total_seconds = ms.total_seconds()
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = int((seconds - int(seconds)) * 100)
    seconds = int(seconds)
    return "{:01}:{:02}:{:02}.{:02}".format(int(hours), int(minutes), seconds, milliseconds)

def create_subtitles(data, task_id, worker_id):
    try:
        update_status_video("Đang Render : Đang tạo phụ đề video ", data['video_id'], task_id, worker_id)
        video_id = data.get('video_id')
        subtitle_file = f'media/{video_id}/subtitles.ass'
        color = data.get('font_color')
        color_backrought = data.get('color_backrought')
        color_border = data.get('stroke')
        font_text = data.get("font_name")
        font_size = data.get('font_size')
        stroke_text = data.get('stroke_size')
        text  = data.get('text_content')

        with open(subtitle_file, 'w', encoding='utf-8') as ass_file:
            # Viết header cho file ASS
            ass_file.write("[Script Info]\n")
            ass_file.write("Title: Subtitles\n")
            ass_file.write("ScriptType: v4.00+\n")
            ass_file.write("WrapStyle: 0\n")
            ass_file.write("ScaledBorderAndShadow: yes\n")
            ass_file.write("YCbCr Matrix: TV.601\n")
            ass_file.write(f"PlayResX: 1920\n")
            ass_file.write(f"PlayResY: 1080\n\n")

            ass_file.write("[V4+ Styles]\n")
            ass_file.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            ass_file.write(f"Style: Default,{font_text},{font_size},{color},{color_backrought},&H00000000,{color_border},0,0,0,0,100,100,0,0,1,{stroke_text},0,2,10,10,40,0\n\n")

            ass_file.write("[Events]\n")
            ass_file.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect,WrapStyle,Text\n")

            start_time = timedelta(0)
            
            total_entries = len(json.loads(text))
            if  data.get('file-srt'):
                srt_path = f'media/{video_id}/cache.srt'
                # Đọc nội dung tệp SRT
                with open(srt_path, 'r', encoding='utf-8') as file:
                    srt_content = file.read()
                print("Nội dung của tệp SRT đã được tải và đọc thành công.")
                
                # Trích xuất thời gian các khung trong tệp SRT
                frame_times = extract_frame_times(srt_content)

                if len(frame_times) == 0:
                    return False
                elif len(frame_times) != total_entries:
                    return False

                elif len(frame_times) == total_entries:
                    for i,iteam in enumerate(json.loads(text)):
                        start_time, end_time = frame_times[i]
                        ass_file.write(f"Dialogue: 0,{start_time[:-1].replace(',', '.')},{end_time[:-1].replace(',', '.')},Default,,0,0,0,,2,{get_text_lines(data,iteam['text'])}\n")
                    return True

            for i,iteam in enumerate(json.loads(text)):
                duration = get_video_duration(f'media/{video_id}/video/{iteam["id"]}.mp4')
                duration_milliseconds = duration * 1000
                end_time = start_time + timedelta(milliseconds=duration_milliseconds)
                start_time_delay =  start_time + timedelta(milliseconds=100)  # Adjust start time
                end_time_delay = start_time + timedelta(milliseconds=duration_milliseconds - 100)
                # end_time = start_time + duration
                # Viết phụ đề
                ass_file.write(f"Dialogue: 0,{format_timedelta_ass(start_time_delay)},{format_timedelta_ass(end_time_delay)},Default,,0,0,0,,2,{get_text_lines(data,iteam['text'])}\n")
                start_time = end_time
                
                process = i / len(json.loads(text)) * 100
                update_status_video(f"Đang Render : Đang tạo phụ đề video {process:.2f} ", data['video_id'], task_id, worker_id)
            time.sleep(1)
            update_status_video("Đang Render : Tạo phụ đề thành công", data['video_id'], task_id, worker_id)
            return True
    except Exception as e:
        print(e)
        update_status_video(f"Render Lỗi : {os.getenv('name_woker')}  Không thể tạo phụ đề", data['video_id'], task_id, worker_id)
        return False
        
def get_video_duration(video_path):
    # Lệnh ffprobe để lấy thông tin video dưới dạng JSON
    command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=duration",
        "-of", "json",
        video_path
    ]
    
    # Chạy lệnh ffprobe và lấy đầu ra
    result = subprocess.run(command, capture_output=True, text=True)
    
    # Chuyển đổi đầu ra từ JSON thành dictionary
    result_json = json.loads(result.stdout)
    
    # Lấy thời lượng từ dictionary
    duration = float(result_json['streams'][0]['duration'])
    
    return duration

def get_audio_duration(file_path):
    try:
        # Gọi lệnh ffprobe để lấy thông tin về file âm thanh
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
        duration = subprocess.check_output(cmd, stderr=subprocess.STDOUT).strip()
        return float(duration)
    except Exception as e:
        print(f"Lỗi khi lấy thông tin từ file âm thanh: {e}")
        return None

def format_time(seconds):
    """Chuyển đổi thời gian từ giây thành định dạng hh:mm:ss.sss"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:06.3f}"

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

def translate_text(text, src_lang='auto', dest_lang='en'):
    translator = Translator()
    translation = translator.translate(text, src=src_lang, dest=dest_lang)
    return translation.text

# lấy thời gian của các file srt
def extract_frame_times(srt_content):
    time_pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')
    matches = time_pattern.findall(srt_content)
    return matches

def download_and_read_srt(data, video_id):
    if data.get('file-srt'):
        max_retries = 30
        retries = 0
        srt_url = data.get('file-srt')  # URL của tệp SRT
        url = f'{SERVER}{srt_url}'
        while retries < max_retries:
            try:
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    os.makedirs(f'media/{video_id}', exist_ok=True)
                    srt_path = f'media/{video_id}/cache.srt'
                    with open(srt_path, 'wb') as file:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:  # Lọc bỏ các keep-alive chunks mới
                                file.write(chunk)
                    print("Tải xuống thành công.")
                    
                    # Đọc nội dung tệp SRT
                    with open(srt_path, 'r', encoding='utf-8') as file:
                        srt_content = file.read()
                    print("Nội dung của tệp SRT đã được tải và đọc thành công.")
                    
                    # Trích xuất thời gian các khung trong tệp SRT
                    frame_times = extract_frame_times(srt_content)
                    print("Thời gian của các khung trong tệp SRT:")
                    for start, end in frame_times:
                        print(f"Bắt đầu: {start}, Kết thúc: {end}")
                    
                    return frame_times
                else:
                    print(f"Lỗi {response.status_code}: Không thể tải xuống tệp.")
            except requests.RequestException as e:
                print(f"Lỗi tải xuống: {e}")

            retries += 1
            print(f"Thử lại {retries}/{max_retries}")
            time.sleep(5)  # Chờ một khoảng thời gian trước khi thử lại

        print("Không thể tải xuống tệp sau nhiều lần thử.")
        return []
    
def convert_to_seconds(time_str):
    time_format = '%H:%M:%S,%f'
    dt = datetime.strptime(time_str, time_format)
    delta = timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second, microseconds=dt.microsecond)
    return delta.total_seconds()

async def check_file_type_async(file_name):
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
    
    # Lấy phần mở rộng của file
    file_extension = os.path.splitext(file_name)[1].lower()
    
    # Kiểm tra loại file dựa trên phần mở rộng
    if file_extension in video_extensions:
        return "video"
    else:
        return "image"

async def process_video_segment_async(data, text_entry, data_sub, i, video_id, task_id, worker_id):
    try:
        # Tính thời lượng của đoạn video
        if data.get('file-srt'):
            start_time, end_time = data_sub[i]
            duration = convert_to_seconds(end_time) - convert_to_seconds(start_time)
        else:
            # duration = get_audio_duration(f'media/{video_id}/voice/{text_entry["id"]}.wav')
            path_audio = f'media/{video_id}/voice/{text_entry["id"]}.wav'
        out_file = f'media/{video_id}/video/{text_entry["id"]}.mp4'
        file = get_filename_from_url(text_entry.get('url_video', ''))
        
        # Kiểm tra đường dẫn file
        if not file:
            update_status_video(
                f"Render Lỗi : {os.getenv('name_woker')} Đường dẫn url không hợp lệ",
                video_id, task_id, worker_id
            )
            raise FileNotFoundError(f"File not found for URL: {text_entry.get('url_video')}")
        
        path_file = f'media/{video_id}/image/{file}'

        print(f"Input file: {path_file}")
        # Kiểm tra loại file
        file_type = await check_file_type_async(path_file)
        if file_type not in ["video", "image"]:
            update_status_video(
                f"Render Lỗi : {os.getenv('name_woker')} Loại file không hợp lệ",
                video_id, task_id, worker_id
            )
            raise ValueError(f"Unsupported file type: {file_type} for {path_file}")
        
        # Xử lý video hoặc ảnh
        if file_type == "video":
            print("cut and scale video")
            await cut_and_scale_video_random_async(path_file, out_file, path_audio, 1920, 1080, 'video_screen')
        elif file_type == "image":
            random_choice = random.choice([True,False])
            if random_choice:
                print("Zoom in")
                await image_to_video_zoom_in_async(path_file, out_file, path_audio, 1920, 1080, 'video_screen')
            else:
                print("Zoom out")
                await image_to_video_zoom_out_async(path_file, out_file, path_audio, 1920, 1080, 'video_screen')
        return True
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        update_status_video(f"Render Lỗi : lỗi xử lý tổng quát video {e}", video_id, task_id, worker_id)
        return False
    
async def cut_and_scale_video_random_async(input_video, path_video, path_audio, scale_width, scale_height, overlay_video_dir):
    max_retries = 10
    attempt = 1
    while attempt <= max_retries:
        print(f"Thử lần {attempt}/{max_retries}: Đang cắt video {input_video} và thay đổi tốc độ.")
        video_length = get_video_duration(input_video)
        duration = get_audio_duration(path_audio)
        start_time = random.uniform(0, video_length - duration)
        start_time_str = format_time(start_time)
        print(f"Thời gian bắt đầu: {start_time_str}")
        print(f"Thời lượng video: {duration}")
        print(f"Độ dài video: {video_length}")
        
        # Kiểm tra xem video có ngắn hơn audio không và tính tỷ lệ tốc độ video cần thay đổi
        if video_length < duration:
            scale_factor = duration / video_length
        else:
            scale_factor = 1  # Giữ nguyên tốc độ video nếu video dài hơn hoặc bằng audio
            
        base_video = await get_random_video_from_directory(overlay_video_dir)
        is_overlay_video = random.choice([True, False, True])
        
        if is_overlay_video:
            ffmpeg_command = [
                "ffmpeg",
                "-ss", start_time_str,
                "-i", input_video,  # Video nền
                "-i", base_video,  # Video overlay
                "-i", path_audio,
                "-filter_complex",
                f"[0:v]scale={scale_width}:{scale_height},fps=24,setpts={scale_factor}*PTS,format=yuv420p[bg];[1:v]scale={scale_width}:{scale_height}[fg];[bg][fg]overlay=format=auto,format=yuv420p[outv]",
                "-r", "24",
                "-map", "[outv]",
                "-map", "2:a",
                "-t", str(duration),
                "-c:v", "libx265",
                "-c:a", "aac",  # Đảm bảo codec âm thanh là AAC
                "-b:a", "192k",  # Bitrate âm thanh hợp lý
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-y",
                path_video
            ]
        else:
            ffmpeg_command = [
                "ffmpeg",
                "-ss", start_time_str,  # Thời gian bắt đầu cắt
                "-i", input_video,  # Video đầu vào
                "-i", path_audio,  # Audio đầu vào
                "-vf", f"scale={scale_width}:{scale_height},fps=24,setpts={scale_factor}*PTS,format=yuv420p",  # Bộ lọc video
                "-map", "0:v",
                "-map", "1:a",
                "-t", str(duration),
                '-r', '24',
                "-c:v", "libx265",
                "-c:a", "aac",  # Đảm bảo codec âm thanh là AAC
                "-b:a", "192k",  # Bitrate âm thanh hợp lý
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",  # Ghi đè file đầu ra nếu đã tồn tại
                "-y",
                path_video  # File đầu ra
            ]

        # Thêm dòng này trước khi gọi process để in ra lệnh FFmpeg đầy đủ
        print("FFmpeg command:", " ".join(ffmpeg_command))
        # Thêm code kiểm tra file tồn tại
        # print(f"Image file exists: {os.path.exists(image_file)}")
        print(f"Base video exists: {os.path.exists(base_video) if base_video else 'No base video'}")
        print(f"Audio file exists: {os.path.exists(path_audio)}")

       
        for attempt in range(max_retries):
            path_cmd = " ".join(ffmpeg_command)
            print(f"Command: {path_cmd}")
            print("xxxxxxxxxxxxxxxxxxxxx")
            print(f"Attempt {attempt + 1}/{max_retries}: Creating video {path_video}")
            try:
                # Sử dụng asyncio.create_subprocess_shell để chạy FFmpeg bất đồng bộ
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    print(f"Video created successfully: {path_video}")
                    return True  # Thành công, thoát hàm
                else:
                    print(f"FFmpeg error: {stderr.decode()}")
                    raise Exception(f"FFmpeg process failed with return code {process.returncode}")
                    
            except Exception as e:
                print(f"Attempt {attempt + 1}/{max_retries} failed. Error: {e}")
                if attempt + 1 == max_retries:
                    print(f"Failed to create video after {max_retries} attempts: {path_video}")
                    return False
                else:
                    print("Retrying...")
                    await asyncio.sleep(2) 
        
    # Nếu hết max_attempts lần thử mà vẫn lỗi
    print(f"Lỗi: Không thể tạo video {path_video} sau {max_retries} lần thử.")
    raise Exception(f"Không thể tạo video sau {max_retries} lần thử.")

async def image_to_video_zoom_in_async(image_file, path_video, path_audio, scale_width, scale_height, overlay_video, max_retries=3, retry_delay=2):
    print("Zoom in Dang chay")
    """Tạo video từ hình ảnh với hiệu ứng zoom-in và thêm âm thanh."""
    import random
    import asyncio
    import os
    
    is_overlay_video = random.choice([True, False, True])
    base_video = await get_random_video_from_directory(overlay_video)
    
    # Lấy thời lượng audio
    duration = get_audio_duration(path_audio)

    if is_overlay_video and base_video:
        ffmpeg_command = [
            'ffmpeg',
            '-y', 
            '-loop', '1',
            '-framerate', '24',
            '-i', image_file,
            '-i', base_video,
            '-i', path_audio,  
            '-filter_complex',
            f"[0:v]format=yuv420p,scale=8000:-1,zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=240:s={scale_width}x{scale_height}:fps=24[bg];"
            f"[1:v]scale={scale_width}:{scale_height},fps=24[overlay_scaled];"
            f"[bg][overlay_scaled]overlay=format=auto,format=yuv420p[outv]",
            "-r", "24",
            "-map", "[outv]",
            "-map", "2:a",  # Ánh xạ tất cả stream âm thanh từ file audio thứ 3
            "-t", str(duration),  # Đặt thời lượng video bằng thời lượng audio
            "-c:v", "h264_nvenc",  # Codec video
            "-c:a", "aac",  # Đảm bảo codec âm thanh là AAC
            "-b:a", "192k",  # Bitrate âm thanh hợp lý
            "-preset", "p7",
            "-pix_fmt", "yuv420p",
            path_video
        ]
    else:
        ffmpeg_command = [
            'ffmpeg',
            '-y',      
            '-loop', '1',
            '-framerate', '24',
            '-i', image_file,
            '-i', path_audio,
            '-vf',
            f"format=yuv420p,scale=8000:-1,zoompan=z='min(zoom+0.001,1.5)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=240:s={scale_width}x{scale_height}:fps=24",
            '-r', '24',
            "-map", "0:v",  # Đơn giản hóa ánh xạ video
            "-map", "1:a",  # Đơn giản hóa ánh xạ audio
            "-t", str(duration),
            "-c:v", "libx265",
            "-c:a", "aac",
            "-b:a", "192k",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            path_video
        ]

    # Thêm code kiểm tra file tồn tại
    print(f"Image file exists: {os.path.exists(image_file)}")
    print(f"Base video exists: {os.path.exists(base_video) if base_video else 'No base video'}")
    print(f"Audio file exists: {os.path.exists(path_audio)}")

    print(f"Command: {' '.join(ffmpeg_command)}")
    
    # Thử tạo video, nếu lỗi thì thử lại
    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1}/{max_retries}: Creating video {path_video}")
        try:
            # Sử dụng asyncio.create_subprocess_exec để chạy FFmpeg bất đồng bộ
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print(f"Video created successfully: {path_video}")
                return True  # Thành công, thoát hàm
            else:
                stderr_output = stderr.decode()
                print(f"FFmpeg error: {stderr_output}")
                raise Exception(f"FFmpeg process failed with return code {process.returncode}: {stderr_output[:200]}")
                
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed. Error: {e}")
            if attempt + 1 == max_retries:
                print(f"Failed to create video after {max_retries} attempts: {path_video}")
                return False
            else:
                print("Retrying...")
                await asyncio.sleep(retry_delay)
    
async def image_to_video_zoom_out_async(image_file, path_video, path_audio, scale_width, scale_height, overlay_video, max_retries=3):
    print("Zoom out Dang chay")
    """Tạo video từ hình ảnh với hiệu ứng zoom-in và thêm âm thanh."""
    import random
    import asyncio
    import os
    import shlex
    
    is_overlay_video = random.choice([True,False,True])
    base_video = await get_random_video_from_directory(overlay_video)
    duration = get_audio_duration(path_audio)
    
    # Kiểm tra file tồn tại
    print(f"Image file exists: {os.path.exists(image_file)}")
    print(f"Base video exists: {os.path.exists(base_video) if base_video else 'No base video'}")
    print(f"Audio file exists: {os.path.exists(path_audio)}")
    
    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1}/{max_retries}: Creating video {path_video}")
        try:
            if is_overlay_video and base_video:
                # Trường hợp 1: Sử dụng overlay video
                ffmpeg_args = [
                    "ffmpeg", "-y", "-loop", "1", "-framerate", "24", 
                    "-i", image_file, "-i", base_video, "-i", path_audio,
                    "-filter_complex", 
                    f"[0:v]format=yuv420p,scale=8000:-1,zoompan=z='zoom+0.002':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=240:s={scale_width}x{scale_height}:fps=24[bg];[1:v]scale={scale_width}:{scale_height},fps=24[overlay_scaled];[bg][overlay_scaled]overlay=format=auto,format=yuv420p[outv]",
                    "-r", "24", "-map", "[outv]", "-map", "2:a", "-t", str(duration),
                    "-c:v", "libx265", "-c:a", "aac", "-b:a", "192k", "-preset", "ultrafast", "-pix_fmt", "yuv420p", path_video
                ]
            else:
                # Trường hợp 2: Không sử dụng overlay video, sử dụng file audio riêng biệt
                ffmpeg_args = [
                    "ffmpeg", "-y", "-loop", "1", "-framerate", "24", 
                    "-i", image_file, "-i", path_audio,  # Path audio làm input thứ 2
                    "-vf", f"format=yuv420p,scale=8000:-1,zoompan=z='zoom+0.005':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=240:s={scale_width}x{scale_height},fps=24",
                    "-r", "24", "-map", "0:v", "-map", "1:a", "-t", str(duration),
                    "-c:v", "libx265", "-c:a", "aac", "-b:a", "192k", "-preset", "ultrafast", "-pix_fmt", "yuv420p", path_video
                ]
            
            # Chỉ hiển thị lệnh để debug
            command_str = " ".join(shlex.quote(str(arg)) for arg in ffmpeg_args)
            print(f"Command: {command_str}")
            
            # Sử dụng asyncio.create_subprocess_exec thay vì shell
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print(f"Video created successfully: {path_video}")
                return True
            else:
                print(f"FFmpeg error: {stderr.decode()}")
                raise Exception(f"FFmpeg process failed with return code {process.returncode}")
                
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries} failed. Error: {e}")
            if attempt + 1 == max_retries:
                print(f"Failed to create video after {max_retries} attempts: {path_video}")
                return False
            else:
                print("Retrying...")
                await asyncio.sleep(2)
          
async def create_video_lines_async(data, task_id, worker_id, max_concurrent):
    try:
        print("Creating video lines...")
        update_status_video("Đang Render : Chuẩn bị tạo video", data['video_id'], task_id, worker_id)
        video_id = data.get('video_id')
        text = data.get('text_content')
        create_or_reset_directory(f'media/{video_id}/video')
        
        # Tải và kiểm tra nội dung văn bản
        text_entries = json.loads(text)
        total_entries = len(text_entries)
        processed_entries = 0
        
        # Xử lý phụ đề nếu có
        data_sub = []
        if data.get('file-srt'):
            data_sub = download_and_read_srt(data, video_id)
            if not data_sub or len(data_sub) != total_entries:
                print("Phụ đề không khớp hoặc bị thiếu.")
                update_status_video("Lỗi: Phụ đề không khớp", video_id, task_id, worker_id)
                return False  # Dừng quá trình nếu phụ đề không khớp
        
        # Sử dụng Semaphore để giới hạn số lượng tác vụ chạy đồng thời
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_process_segment(data, text_entry, data_sub, index, video_id, task_id, worker_id):
            async with semaphore:  # Đảm bảo không quá max_concurrent tác vụ chạy cùng lúc
                return await process_video_segment_async(data, text_entry, data_sub, index, video_id, task_id, worker_id)
        
        # Tạo danh sách các coroutine với giới hạn
        tasks = []
        for i, text_entry in enumerate(text_entries):
            task = bounded_process_segment(data, text_entry, data_sub, i, video_id, task_id, worker_id)
            tasks.append(asyncio.create_task(task))
        
        # Theo dõi và xử lý kết quả khi các tác vụ hoàn thành
        for task in asyncio.as_completed(tasks):
            try:
                result = await task
                if result:
                    processed_entries += 1
                    percent_complete = (processed_entries / total_entries) * 100
                    update_status_video(
                        f"Đang Render : Đang tạo video {processed_entries}/{total_entries} thành công", 
                        video_id, task_id, worker_id
                    )
                else:
                    # Nếu một task thất bại, hủy tất cả task còn lại
                    for remaining_task in tasks:
                        if not remaining_task.done():
                            remaining_task.cancel()
                    update_status_video("Lỗi: Không thể tạo một phân đoạn video", video_id, task_id, worker_id)
                    return False
            except asyncio.CancelledError:
                # Task đã bị hủy, bỏ qua
                pass
            except Exception as e:
                print(f"Lỗi khi tạo video: {e}")
                update_status_video(f"Render Lỗi: Lỗi khi tạo video - {e}", video_id, task_id, worker_id)
                # Hủy tất cả các tác vụ còn lại
                for remaining_task in tasks:
                    if not remaining_task.done():
                        remaining_task.cancel()
                return False
        
        update_status_video("Render Render: Tạo video thành công", video_id, task_id, worker_id)
        return True
        
    except Exception as e:
        print("xxxxxxxx{}".format(e))
        update_status_video(f"Render Lỗi : lỗi xử lý tổng quát video {e}", video_id, task_id, worker_id)
        return False  # Dừng quá trình nếu có lỗi tổng quát

async def get_random_video_from_directory(directory_path):
    video_files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
    return os.path.join(directory_path, random.choice(video_files))

def create_video_lines(data, task_id, worker_id):
    logical_cores = psutil.cpu_count(logical=True)
    max_concurrent=int(logical_cores /8)
    return asyncio.run(create_video_lines_async(data, task_id, worker_id,max_concurrent))

async def login_data_async(session, email, password):
    """ Đăng nhập để lấy idToken (async) """
    data = {
        "returnSecureToken": True,
        "email": email,
        "password": password,
        "clientType": "CLIENT_TYPE_WEB"
    }
    params = {"key": "AIzaSyBJN3ZYdzTmjyQJ-9TdpikbsZDT9JUAYFk"}
    url = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword'
    
    async with session.post(url, params=params, json=data) as response:
        if response.status != 200:
            response.raise_for_status()
        result = await response.json()
        return result['idToken']

async def get_access_token_async(session, idToken):
    """ Lấy access_token từ idToken (async) """
    async with session.post('https://typecast.ai/api/auth-fb/custom-token', json={"token": idToken}) as response:
        if response.status != 200:
            response.raise_for_status()
        result = await response.json()
        return result["result"]['access_token']

async def active_token_async(session, access_token):
    """ Lấy idToken từ access_token (async) """
    params = {"key": "AIzaSyBJN3ZYdzTmjyQJ-9TdpikbsZDT9JUAYFk"}
    async with session.post('https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken',
                          params=params, json={"token": access_token, "returnSecureToken": True}) as response:
        if response.status != 200:
            response.raise_for_status()
        result = await response.json()
        return result['idToken']

async def get_cookie_async(session, email, password):
    """ Lấy Access Token từ email/password (async) """
    try:
        Token_login = await login_data_async(session, email, password)
        idToken = await get_access_token_async(session, Token_login)
        ACCESS_TOKEN = await active_token_async(session, idToken)
        return ACCESS_TOKEN
    except Exception as e:
        print(f"Lỗi đăng nhập với tài khoản {email}: {str(e)}")
        return None

def load_accounts(filename="accounts.txt"):
    """ Đọc danh sách tài khoản từ file và xáo trộn """
    accounts = []
    with open(filename, "r") as file:
        for line in file:
            line = line.strip()
            if "|" in line:
                email, password = line.split("|", 1)
                accounts.append((email, password))
    random.shuffle(accounts)  # Xáo trộn tài khoản để tránh bị chặn theo thứ tự
    return accounts

async def get_audio_url_async(session, ACCESS_TOKEN, url_voice_text):
    """Hàm lấy URL audio từ API (async)."""
    max_retries = 40  # Số lần thử lại tối đa
    retry_delay = 5  # Thời gian chờ giữa các lần thử (giây)

    for attempt in range(max_retries):
        # Gửi yêu cầu POST đến API
        url = "https://typecast.ai/api/speak/batch/get"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}"
        }
        try:
            async with session.post(url, headers=headers, json=url_voice_text) as response:
                print(f"Response status code: {response.status}")
                # Xử lý phản hồi từ API
                if response.status == 200:
                    try:
                        result_json = await response.json()
                        result = result_json.get("result", [])[0]
                        audio_url = result.get("audio", {}).get("url")
                        if audio_url:
                            print("Audio URL found:", audio_url)
                            return audio_url
                    except (KeyError, IndexError, TypeError) as e:
                        print("Error parsing JSON response:", e)
        except Exception as e:
            print("Error occurred during API request:", e)
        # Chờ trước khi thử lại
        await asyncio.sleep(retry_delay)
    return False

async def get_voice_super_voice_async(session, data, text, file_name, semaphore): 
    """ Gửi request để lấy voice (async) """
    global failed_accounts, valid_tokens
    accounts = load_accounts()
    
    async with semaphore:  # Sử dụng semaphore để giới hạn số kết nối đồng thời
        for email, password in accounts:  
            if email in failed_accounts:  
                continue  # Bỏ qua tài khoản đã gặp lỗi trước đó
                
            # Sử dụng token đã lưu nếu có
            ACCESS_TOKEN = valid_tokens.get(email)
            if not ACCESS_TOKEN:
                ACCESS_TOKEN = await get_cookie_async(session, email, password)
                if not ACCESS_TOKEN:
                    failed_accounts.add(email)
                    continue
                valid_tokens[email] = ACCESS_TOKEN  # Lưu lại token hợp lệ

            print(f"Đang sử dụng token cho {email}: {ACCESS_TOKEN[:20]}...")
            
            style_name_data = json.loads(data.get("style"))
            style_name_data[0]["text"] = text

            for retry_count in range(2):  
                try:
                    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}', 'Content-Type': 'application/json'}
                    async with session.post('https://typecast.ai/api/speak/batch/post', 
                                          headers=headers, 
                                          json=style_name_data) as response:

                        if response.status == 200:
                            print(f"✅ Thành công với {email}")
                            response_json = await response.json()
                            url = response_json.get("result", {}).get("speak_urls", [])

                            url_voice = await get_audio_url_async(session, ACCESS_TOKEN, url)
                            print("xxxxxxxxxxxxxxxxxxx")
                            if url_voice:
                                async with session.get(url_voice, headers={'Authorization': f'Bearer {ACCESS_TOKEN}'}) as download_response:
                                    if download_response.status == 200:
                                        content = await download_response.read()
                                        with open(file_name, 'wb') as f:
                                            f.write(content)
                                        print(f"✅ Đã lưu file: {file_name}")
                                        return True
                                    else:
                                        print(f"⚠️ Lỗi tải file, status: {download_response.status}")
                            
                            failed_accounts.add(email)
                            break
                        else:
                            print(f"❌ Lỗi {response.status}, thử lại ({retry_count+1}/2)...")
                            await asyncio.sleep(1)

                except Exception as e:
                    print(f"⚠️ Lỗi: {str(e)}, thử lại ({retry_count+1}/2)...")
                    await asyncio.sleep(1)
                    
        print("🚫 Đã thử hết tài khoản nhưng vẫn thất bại!")
        return False

async def process_voice_entry_async(session, data, text_entry, video_id, task_id, worker_id, language, semaphore):
    """Hàm xử lý giọng nói cho từng trường hợp ngôn ngữ (async)."""
    file_name = f'media/{video_id}/voice/{text_entry["id"]}.wav'
    success = False
    
    print(f"Đang tạo giọng nói cho đoạn văn bản ID {text_entry['id']}")
    
    # Xử lý ngôn ngữ tương ứng và kiểm tra kết quả tải
    # Hiện tại chỉ hỗ trợ SUPER VOICE
    if language == 'SUPER VOICE':
        success = await get_voice_super_voice_async(session, data, text_entry['text'], file_name, semaphore)

    elif language == 'Japanese-VoiceVox':
        success = await get_voice_japanese(data, text_entry['text'], file_name)
    # Thêm các phương thức async cho các loại ngôn ngữ khác nếu cần
    
    # Trả về False nếu tải không thành công
    if not success:
        print(language)
        print(f"Lỗi: Không thể tạo giọng nói cho đoạn văn bản ID {text_entry['id']}")
        return False, None
    
    return text_entry['id'], file_name

async def display_active_downloads(active_tasks, total, stop_event):
    """Hiển thị trạng thái tải xuống hiện tại."""
    while not stop_event.is_set():
        completed = sum(1 for status in active_tasks.values() if status == "completed")
        active = sum(1 for status in active_tasks.values() if status == "active")
        
        print(f"\n--- TRẠNG THÁI TẢI XUỐNG ---")
        print(f"Đã hoàn thành: {completed}/{total} ({completed/total*100:.2f}%)")
        print(f"Đang xử lý: {active}")
        
        active_ids = [task_id for task_id, status in active_tasks.items() if status == "active"]
        if active_ids:
            print(f"ID đang xử lý: {', '.join(map(str, active_ids))}")
        
        await asyncio.sleep(3)

async def download_audio_async(data, task_id, worker_id):
    try:
        print("Đang tải giọng nói bất đồng bộ...")
        language = data.get('language')
        video_id = data.get('video_id')
        text = data.get('text_content')
        
        # Tải các đoạn văn bản từ `text_content`
        text_entries = json.loads(text)
        total_entries = len(text_entries)
        
        # Kiểm tra nếu không có entry nào
        if total_entries == 0:
            print("Không có đoạn văn bản nào để xử lý.")
            return True

        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(f'media/{video_id}/voice', exist_ok=True)

        # Danh sách giữ kết quả
        result_files = [None] * total_entries
        
        # Theo dõi trạng thái các tác vụ
        active_tasks = {}  # {task_id: status}
        for i in range(total_entries):
            active_tasks[text_entries[i]["id"]] = "pending"
        
        # Task hiển thị trạng thái
        stop_display_event = asyncio.Event()
        display_task = asyncio.create_task(display_active_downloads(active_tasks, total_entries, stop_display_event))
        
        # Giới hạn số lượng kết nối đồng thời
        max_concurrent = 10  # Điều chỉnh số lượng tải xuống đồng thời
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Tạo phiên HTTP chung cho tất cả các yêu cầu
        async with aiohttp.ClientSession() as session:
            # Hàm wrapper để cập nhật trạng thái
            async def process_entry_with_status(index, entry):
                entry_id = entry["id"]
                active_tasks[entry_id] = "active"
                
                try:
                    result = await process_voice_entry_async(session, data, entry, video_id, task_id, worker_id, language, semaphore)
                    
                    if result[0] is False:
                        active_tasks[entry_id] = "failed"
                        return False
                    
                    entry_id, file_name = result
                    result_files[index] = file_name
                    active_tasks[entry_id] = "completed"
                    
                    # Tính toán tiến độ
                    completed = sum(1 for status in active_tasks.values() if status == "completed")
                    percent_complete = (completed / total_entries) * 100
                    
                    # Cập nhật trạng thái
                    update_status_video(
                        f"Đang Render : Đang tạo giọng đọc ({completed}/{total_entries}) {percent_complete:.2f}%",
                        video_id, task_id, worker_id
                    )
                    return True
                except Exception as e:
                    print(f"Lỗi khi xử lý giọng đọc cho đoạn {entry_id}: {e}")
                    active_tasks[entry_id] = "failed"
                    return False
            
            # Tạo danh sách các tác vụ
            tasks = []
            for idx, entry in enumerate(text_entries):
                task = process_entry_with_status(idx, entry)
                tasks.append(task)
            
            # Thực thi tất cả các tác vụ và chờ kết quả
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Dừng hiển thị trạng thái
            stop_display_event.set()
            await display_task
            
            # Kiểm tra kết quả
            if False in results or any(isinstance(r, Exception) for r in results):
                update_status_video(
                    f"Render Lỗi : {os.getenv('name_woker')} Lỗi khi tạo giọng đọc",
                    video_id, task_id, worker_id
                )
                return False
            
            # Ghi vào input_files.txt theo đúng thứ tự
            with open(f'media/{video_id}/input_files.txt', 'w') as file:
                for file_name in result_files:
                    if file_name:
                        file.write(f"file 'voice/{os.path.basename(file_name)}'\n")
            
            # Cập nhật trạng thái hoàn thành
            update_status_video(
                f"Đang Render : Đã tạo xong giọng đọc",
                video_id, task_id, worker_id
            )
            return True
    except Exception as e:
        print(f"Lỗi tổng thể: {str(e)}")
        update_status_video(
            f"Render Lỗi : {os.getenv('name_woker')} Không thể tải xuống âm thanh - {str(e)}",
            video_id, task_id, worker_id
        )
        return False

# Hàm wrapper để gọi từ code đồng bộ
def download_audio(data, task_id, worker_id):
    # Đo thời gian
    start_time = time.time()
    
    # Gọi phiên bản bất đồng bộ
    result = asyncio.run(download_audio_async(data, task_id, worker_id))
    
    # Tính thời gian đã sử dụng
    end_time = time.time()
    elapsed_time = end_time - start_time
    
    # Hiển thị tổng kết
    print(f"\n=== TÓM TẮT ===")
    print(f"Thời gian xử lý: {elapsed_time:.2f} giây")
    print(f"Kết quả: {'Thành công' if result else 'Thất bại'}")

    print(f"{'-'*20}\n")
    print(result)
    print(f"{'-'*20}\n")
    
    return result

def format_timestamp(seconds):
    """Chuyển đổi thời gian từ giây thành định dạng SRT (hh:mm:ss,ms)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

async def get_voice_japanese(data, text, file_name):
    """Hàm chuyển văn bản thành giọng nói tiếng Nhật với VoiceVox, bao gồm chức năng thử lại khi gặp lỗi."""
    directory = os.path.dirname(file_name)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    voice_id = data.get('voice_id')
    success = False
    attempt = 0
    
    while not success and attempt < 10:
        try:
            # Tạo audio query với VoiceVox
            response_query = requests.post(
                            f'http://127.0.0.1:50021/audio_query?speaker={voice_id}',  # API để tạo audio_query
                            params={'text': text}  # Gửi văn bản cần chuyển thành giọng nói
                        )
            # Yêu cầu tạo âm thanh
            url_synthesis = f"http://127.0.0.1:50021/synthesis?speaker={voice_id}"
            response_synthesis = requests.post(url_synthesis,data=json.dumps(response_query.json()))
            # Ghi nội dung phản hồi vào tệp
            with open(file_name, 'wb') as f:
                f.write(response_synthesis.content)
            # Kiểm tra độ dài tệp âm thanh
            duration = get_audio_duration(file_name)
            if duration > 0:  # Đảm bảo rằng âm thanh có độ dài hợp lý
                success = True
                print(f"Tạo giọng nói thành công cho '{text}' tại {file_name}")
                break  
            else:
                print(f"Lỗi: Tệp âm thanh {file_name} không hợp lệ.")
        
        except requests.RequestException as e:
            print(f"Lỗi mạng khi gọi VoiceVox API: {e}. Thử lại...")
        except Exception as e:
            print(f"Lỗi không xác định: {e}. Thử lại...")

        attempt += 1
        if not success:
            time.sleep(1)  # Đợi 1 giây trước khi thử lại

    if not success:
        print(f"Không thể tạo giọng nói sau {attempt} lần thử.")
        return False
    
    return True

async def text_to_speech_async(text, voice, output_file):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_file)

def get_voice_korea(data, text, file_name):
    """Hàm xử lý TTS cho tiếng Hàn Quốc, tương tự get_voice_chat_gpt."""
    directory = os.path.dirname(file_name)
    name_langue = data.get('style')
    
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    success = False
    attempt = 0
    
    while not success and attempt < 10:
        try:
            # Chạy text_to_speech dưới dạng không đồng bộ
            asyncio.run(text_to_speech_async(text, name_langue, file_name))
            
            # Kiểm tra độ dài tệp âm thanh
            duration = get_audio_duration(file_name)
            if duration > 0:  # Đảm bảo rằng âm thanh có độ dài hợp lý
                success = True
                print(f"Tạo giọng nói thành công cho '{text}' tại {file_name}")
                break
            else:
                if os.path.exists(file_name):
                    os.remove(file_name)  # Xóa tệp nếu không hợp lệ
                print(f"Lỗi: Tệp âm thanh {file_name} không hợp lệ.")
        except Exception as e:
            print(f"Lỗi khi tạo giọng nói cho tiếng Hàn: {e}. Thử lại...")
        
        attempt += 1
        if not success:
            time.sleep(1)  # Đợi 1 giây trước khi thử lại
    
    if not success:
        print(f"Không thể tạo giọng nói sau {attempt} lần thử.")
        return False
    return True

def get_voice_chat_gpt(data, text, file_name):
    directory = os.path.dirname(file_name)
    name_langue = data.get('style')
    
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    url = "https://api.ttsopenai.com/api/v1/public/text-to-speech-stream"
    payload = {
        "model": "tts-1",
        "speed": 1,
        "input": text,
        "voice_id": name_langue
    }

    success = False
    attempt = 0
    
    while not success and attempt < 15:
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                with open(file_name, 'wb') as f:
                    f.write(response.content)
                
                # Kiểm tra độ dài của tệp âm thanh
                duration = get_audio_duration(file_name)
                if duration and duration > 0:
                    success = True
                    print(f"Tạo giọng nói thành công cho '{text}' tại {file_name}")
                    break
                else:
                    if os.path.exists(file_name):
                        os.remove(file_name)  # Xóa tệp nếu không hợp lệ
                    print(f"Lỗi: Tệp âm thanh {file_name} không hợp lệ.")
            else:
                print(f"Lỗi: API trả về trạng thái {response.status_code}. Thử lại...")
                
            attempt += 1
        except requests.RequestException as e:
            print(f"Lỗi mạng khi gọi API: {e}. Thử lại...")
            attempt += 1
            time.sleep(1)  # Đợi 1 giây trước khi thử lại
    
    if not success:
        print(f"Không thể tạo giọng nói sau {attempt} lần thử.")
    return success
                 
def get_voice_chat_ai_human(data, text, file_name):
    """Hàm xử lý TTS với AI Human Studio, bao gồm chức năng thử lại khi gặp lỗi."""
    
    # Tạo thư mục nếu chưa tồn tại
    directory = os.path.dirname(file_name)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    headers = {
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.eyJyb2xlIjoiUmp5ZWZuWWVHWl9idEZ2cUlqNDRNZyIsInNlcnZpY2VDb2RlIjoicmZUSUk2RURJZkE0dklvT3pxUUVqdyIsImVtYWlsIjoiV25YNGJiQTNGT1Qxdk5hbU9rMXhQU0Vwb1JDaEJLYmplM09TeDN5c19rdyIsIm1lbWJlcklkIjoiaXFCaHFFbTluTjhEUVdvUUdBalhXdyIsImlhdCI6MTcyOTU2OTYyNCwiZXhwIjoxNzI5NTc2ODI0fQ.JBiM-7532YiPAsaeCxo9Xg0jKRvO2LddpRJomTlTsdoSnHpLJEcXKUUBKez1gJd7RQJ1-YHWzMF6NgKiWIXc13JktWeL6XqtYLiIqOSglaWvJVMRgEmMuBmX6WpReh4nvnJZ3bils8X6Qnh3uqe9HKLtqLoi2K8EnrEw2aCpvSuf6_q8J8c9tyHuZNsQJQLbXoLEQLmIQRZnv0Eu91cE3IGs9694sIlrgD5pNkGJVqzdLFd0SRzq61SgBubAWGuY-Kk8vdypy-2QN8xCgoCzUPWs6LlLzLhlvzQJFaOF0WED2VBzg_hPgqgC_pxsxyLX0SdMXWv5giBUc0P84ler3w"
    }
    
    payload = {
        "model_name": data.get("style"),
        "emotion": "neutral",
        "language": "ko",
        "pitch": 10,
        "text": text,
        "speed": 10,
        "smart_words": "[[\"\",\"\"]]"
    }

    success = False
    attempt = 0
    
    while not success and attempt < 10:
        try:
            # Gửi yêu cầu đến API để lấy URL tệp âm thanh
            response = requests.post("https://aihumanstudio.ai/api/v1/TtsHumeloModel", headers=headers, json=payload)
            response.raise_for_status()  # Kiểm tra mã trạng thái HTTP
            
            response_json = response.json()
            tts_path = response_json.get('tts_path')
            
            if not tts_path:
                raise ValueError("Không nhận được đường dẫn tệp âm thanh từ API.")

            # Tải xuống tệp âm thanh từ URL trả về
            response_synthesis = requests.get(tts_path)
            response_synthesis.raise_for_status()  # Kiểm tra mã trạng thái HTTP

            # Lưu tệp âm thanh
            with open(file_name, 'wb') as f:
                f.write(response_synthesis.content)
            
            # Kiểm tra độ dài tệp âm thanh
            duration = get_audio_duration(file_name)
            if duration > 0:
                success = True
                print(f"Tạo giọng nói thành công cho '{text}' tại {file_name}")
                break  
            else:
                if os.path.exists(file_name):
                    os.remove(file_name)  # Xóa tệp nếu không hợp lệ
                print(f"Lỗi: Tệp âm thanh {file_name} không hợp lệ.")
        
        except requests.RequestException as e:
            print(f"Lỗi mạng khi gọi API AI Human Studio: {e}. Thử lại...")
        except Exception as e:
            print(f"Lỗi không xác định: {e}. Thử lại...")

        attempt += 1
        if not success:
            time.sleep(1)  # Đợi 1 giây trước khi thử lại

    if not success:
        print(f"Không thể tạo giọng nói sau {attempt} lần thử.")
        return False
    return True

def get_voice_ondoku3(data, text, file_name):
    directory = os.path.dirname(file_name)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    url = f"https://ondoku3.com/en/text_to_speech/"
    data = json.loads(data.get("style"))
    headers = {  
            "referer": "https://ondoku3.com/en/text_to_speech/",
            "x-csrftoken": "PE5podrc4l812OtM9HlfsxAONQudZOLkGD7MABvA2LWtSw4y2iw6HFh83NVJBACs",
            "cookie": "_gid=GA1.2.1148716843.1732981575; user=4528422; csrftoken=19cxmyey8AYC0SLW3Ll1piRuq7BGMW1i; sessionid=obz5r6tbjtjwswh6b5x4lzc2iiihcgi4; django_language=en; _gat_gtag_UA_111769414_6=1; _ga=GA1.1.31832820.1732272096; _ga_0MMKHHJ235=GS1.1.1733029892.5.1.1733036426.0.0.0"
            
        }
    data['text'] = text
    
    success = False
    attempt = 0
    while not success and attempt < 10:
        try:
            # Gửi yêu cầu đến API để lấy URL tệp âm thanh
            response = requests.post(url, data=data, headers=headers)
            response.raise_for_status()  # Kiểm tra mã trạng thái HTTP
            
            response_json = response.json()
            tts_path = response_json.get('url')
            print(tts_path)
            print(response_json)
            print("=========================================")
            if not tts_path:
                raise ValueError("Không nhận được đường dẫn tệp âm thanh từ API.")

            # Tải xuống tệp âm thanh từ URL trả về
            response_synthesis = requests.get(tts_path)
            response_synthesis.raise_for_status()  # Kiểm tra mã trạng thái HTTP

            # Lưu tệp âm thanh
            with open(file_name, 'wb') as f:
                f.write(response_synthesis.content)
            
            # Kiểm tra độ dài tệp âm thanh
            duration = get_audio_duration(file_name)
            if duration > 0:
                success = True
                print(f"Tạo giọng nói thành công cho '{text}' tại {file_name}")
                break  
            else:
                if os.path.exists(file_name):
                    os.remove(file_name)  # Xóa tệp nếu không hợp lệ
                print(f"Lỗi: Tệp âm thanh {file_name} không hợp lệ.")
        
        except requests.RequestException as e:
            print(f"Lỗi mạng khi gọi API AI Human Studio: {e}. Thử lại...")
        except Exception as e:
            print(f"Lỗi không xác định: {e}. Thử lại...")

        attempt += 1
        if not success:
            time.sleep(1)  # Đợi 1 giây trước khi thử lại

    if not success:
        print(f"Không thể tạo giọng nói sau {attempt} lần thử.")
        return False
    return True
      
def get_filename_from_url(url):
    parsed_url = urllib.parse.urlparse(url)
    path = parsed_url.path
    filename = path.split('/')[-1]
    return filename

async def download_single_image_async(session, url, local_directory, task_num):
    """Hàm bất đồng bộ tải xuống một hình ảnh từ URL và lưu vào thư mục đích."""
    filename = get_filename_from_url(url)
    file_path = os.path.join(local_directory, filename)
    
    # Kiểm tra xem tệp đã tồn tại trong thư mục hay chưa
    if os.path.exists(file_path):
        print(f"[Luồng {task_num}] Tệp {filename} đã tồn tại. Không cần tải lại.")
        return True, url, task_num  # Trả về True và URL nếu tệp đã tồn tại
    
    print(f"[Luồng {task_num}] Bắt đầu tải xuống hình ảnh từ: {url}")
    start_time = time.time()
    
    for attempt in range(5):  # Thử tải lại 5 lần nếu thất bại
        try:
            async with session.get(url, timeout=200) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(file_path, 'wb') as file:
                        file.write(content)
                    end_time = time.time()
                    duration = end_time - start_time
                    print(f"[Luồng {task_num}] Tải xuống thành công: {url} (Thời gian: {duration:.2f}s)")
                    return True, url, task_num  # Trả về True và URL nếu tải thành công
                else:
                    print(f"[Luồng {task_num}] Trạng thái không thành công - {response.status} - URL: {url}")
                    if attempt == 4:  # Nếu đây là lần thử cuối cùng
                        break
                    await asyncio.sleep(1)  # Chờ 1 giây trước khi thử lại
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f"[Luồng {task_num}] Lỗi yêu cầu khi tải xuống {url}: {e}")
            if attempt == 4:  # Nếu đây là lần thử cuối cùng
                break
            await asyncio.sleep(1)  # Chờ 1 giây trước khi thử lại
        except Exception as e:
            print(f"[Luồng {task_num}] Lỗi không xác định khi tải xuống {url}: {e}")
            if attempt == 4:  # Nếu đây là lần thử cuối cùng
                break
            await asyncio.sleep(1)  # Chờ 1 giây trước khi thử lại
    
    return False, url, task_num  # Trả về False và URL nếu không thể tải xuống

async def display_active_downloads_voice(active_tasks, stop_event):
    """Hiển thị các luồng đang hoạt động theo chu kỳ."""
    while not stop_event.is_set():
        active_count = sum(1 for task_id, status in active_tasks.items() if status == "active")
        active_ids = [task_id for task_id, status in active_tasks.items() if status == "active"]
        print(f"--- CÁC LUỒNG ĐANG HOẠT ĐỘNG: {active_count} luồng ---")
        if active_ids:
            print(f"IDs của các luồng đang hoạt động: {', '.join(map(str, active_ids))}")
        await asyncio.sleep(2)  # Cập nhật mỗi 2 giây

async def download_image_async(data, task_id, worker_id):
    video_id = data.get('video_id')
    update_status_video(f"Đang Render : Bắt đầu tải xuống hình ảnh", video_id, task_id, worker_id)
    
    local_directory = os.path.join('media', str(video_id), 'image')
    os.makedirs(local_directory, exist_ok=True)
    
    text = data.get('text_content')
    if not text:
        return True
    
    # Tải và kiểm tra nội dung văn bản
    text_entries = json.loads(text)
    images = []
    
    for item in text_entries:
        if item.get('url_video') == "":
            update_status_video(
                f"Render Lỗi : {os.getenv('name_woker')} item hình ảnh lỗi vui lòng xử lý lại",
                video_id, task_id, worker_id
            )
            return False
            
        parsed_url = urlparse(item.get('url_video'))
        if parsed_url.scheme in ['http', 'https']:
            images.append(item.get('url_video'))
        else:
            url = os.getenv('url_web') + item.get('url_video')
            images.append(url)
    
    print(f"Số lượng hình ảnh cần tải: {len(images)}")
    total_images = len(images)
    
    if total_images == 0:
        return True
    
    # Theo dõi các luồng đang hoạt động
    active_tasks = {}  # {task_num: status}
    
    # Tạo và sử dụng session chung cho tất cả các request
    async with aiohttp.ClientSession() as session:
        # Tạo đối tượng event để dừng hiển thị luồng
        stop_display_event = asyncio.Event()
        
        # Bắt đầu task hiển thị các luồng đang hoạt động
        display_task = asyncio.create_task(display_active_downloads_voice(active_tasks, stop_display_event))
        
        # Tạo một tác vụ để hiển thị tiến trình
        progress_counter = 0
        max_concurrent = 10  # Số lượng tải xuống đồng thời tối đa
        
        # Chạy tất cả các tác vụ đồng thời với semaphore để giới hạn số lượng tải xuống đồng thời
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(session, url, local_directory, task_num):
            nonlocal progress_counter
            
            # Đánh dấu task bắt đầu
            active_tasks[task_num] = "active"
            
            async with semaphore:
                result, url, _ = await download_single_image_async(session, url, local_directory, task_num)
                progress_counter += 1
                percent_complete = (progress_counter / total_images) * 100
                
                # Đánh dấu task hoàn thành
                active_tasks[task_num] = "completed"
                
                update_status_video(
                    f"Đang Render : Tải xuống file ({progress_counter}/{total_images}) - {percent_complete:.2f}%",
                    video_id, task_id, worker_id
                )
                return result, url
        
        # Tạo danh sách các coroutine với semaphore
        tasks = []
        for i, image in enumerate(images, 1):
            task = download_with_semaphore(session, image, local_directory, i)
            tasks.append(task)
        
        print(f"Đang bắt đầu {len(tasks)} tác vụ tải xuống với tối đa {max_concurrent} luồng đồng thời")
        
        # Chạy tất cả các tác vụ và chờ kết quả
        download_results = await asyncio.gather(*tasks)
        
        # Dừng hiển thị luồng
        stop_display_event.set()
        await display_task
        
        print(f"\nKết quả tải xuống: Hoàn thành {progress_counter}/{total_images} tệp")
        
        # Kiểm tra kết quả
        for result, url in download_results:
            if not result:
                print(f"Lỗi tải xuống hình ảnh từ {url}")
                update_status_video(
                    f"Render Lỗi : {os.getenv('name_woker')} Lỗi tải xuống hình ảnh {url}",
                    video_id, task_id, worker_id
                )
                return False
    
    return True

# Hàm wrapper để gọi hàm bất đồng bộ từ code đồng bộ
def download_image(data, task_id, worker_id):
    return asyncio.run(download_image_async(data, task_id, worker_id))

def create_or_reset_directory(directory_path):
    try:
        # Kiểm tra xem thư mục có tồn tại hay không
        if os.path.exists(directory_path):
            # Kiểm tra xem thư mục có trống hay không
            if os.listdir(directory_path):
                # Nếu không trống, xóa thư mục và toàn bộ nội dung bên trong
                shutil.rmtree(directory_path)
                print(f"Đã xóa thư mục '{directory_path}' và toàn bộ nội dung.")
            else:
                # Nếu trống, chỉ xóa thư mục
                os.rmdir(directory_path)
                print(f"Đã xóa thư mục trống '{directory_path}'.")
        # Tạo lại thư mục
        os.makedirs(directory_path)
        return True
    except Exception as e:
        print(f"Lỗi: {e}")
        return False
# Tính vị trí và kích thước mới của video crop
def parse_crop_data(crop_data_str):
    # Tách chuỗi thành các phần tử và chuyển thành dictionary
    data_pairs = crop_data_str.split(',')
    crop_data = {}
    
    for pair in data_pairs:
        key, value = pair.split('=')
        crop_data[key] = int(value)
    
    return crop_data

def calculate_new_position(crop_data, original_resolution=(640, 360), target_resolution=(1920, 1080)):
    original_top = crop_data.get('top')
    original_left = crop_data.get('left')
    original_width = crop_data.get('width')
    original_height = crop_data.get('height')
    
    # Tính tỷ lệ thay đổi theo chiều rộng và chiều cao
    original_width_res, original_height_res = original_resolution
    new_width_res, new_height_res = target_resolution

    width_ratio = new_width_res / original_width_res
    height_ratio = new_height_res / original_height_res

    # Tính toán vị trí và kích thước mới
    new_top = original_top * height_ratio
    new_left = original_left * width_ratio
    new_width = original_width * width_ratio
    new_height = original_height * height_ratio

    return round(new_left), round(new_top), round(new_width), round(new_height)

def get_video_info(data,task_id,worker_id):
    video_id = data.get('video_id')
    output_file = f'media/{video_id}/cache.mp4'
    video_url = data.get('url_video_youtube')
    # Đảm bảo thư mục đích tồn tại
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Thử phương thức 1: Sử dụng API
    try:
        api_url = "https://iloveyt.net/proxy.php"
        form_data = {"url": video_url}
        response = requests.post(api_url, data=form_data, timeout=10)
        api_data = response.json()
        
        if "api" not in api_data or "mediaItems" not in api_data["api"]:
            raise ValueError("Invalid API response format")
            
        title = api_data["api"]["title"]
        media_preview_url = api_data["api"]["previewUrl"]
        
        # Tải video với cập nhật % tải
        with requests.get(media_preview_url, stream=True) as response:
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 8192
            downloaded_size = 0

            with open(output_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)

                        # Tính % tải và cập nhật trạng thái
                        percent_complete = (downloaded_size / total_size) * 100
                        update_status_video(
                            f"Đang Render: Đang tải video {percent_complete:.2f}%",
                            video_id,
                            task_id,
                            worker_id
                        )
        update_status_video(f"Đang Render: Đã tải xong video", video_id, task_id, worker_id)
        return {"title": title}
        
    except (requests.RequestException, ValueError, KeyError, IOError) as e:
        print(f"Phương thức 1 thất bại: {str(e)}")
        update_status_video(f"Đang Render: Phương thức download 1 thất bại", video_id, task_id, worker_id)  
        
        
    # Thử phương thức 1: Sử dụng API
    try:
        api_url = "https://opendown.net/proxy.php"
        form_data = {"url": video_url}
        response = requests.post(api_url, data=form_data, timeout=10)
        api_data = response.json()
        
        if "api" not in api_data or "mediaItems" not in api_data["api"]:
            raise ValueError("Invalid API response format")
            
        title = api_data["api"]["title"]
        media_preview_url = api_data["api"]["previewUrl"]
        
        # Tải video với cập nhật % tải
        with requests.get(media_preview_url, stream=True) as response:
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 8192
            downloaded_size = 0

            with open(output_file, "wb") as file:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        file.write(chunk)
                        downloaded_size += len(chunk)

                        # Tính % tải và cập nhật trạng thái
                        percent_complete = (downloaded_size / total_size) * 100
                        update_status_video(
                            f"Đang Render: Đang tải video {percent_complete:.2f}%",
                            video_id,
                            task_id,
                            worker_id
                        )
        update_status_video(f"Đang Render: Đã tải xong video", video_id, task_id, worker_id)
        return {"title": title}
        
    except (requests.RequestException, ValueError, KeyError, IOError) as e:
        print(f"Phương thức 2 thất bại: {str(e)}")
        update_status_video(f"Đang Render: Phương thức download 2 thất bại", video_id, task_id, worker_id)  
        
        
    # Phương thức 3: Sử dụng yt-dlp
    try:
        url = data.get('url_video_youtube')
        if not url:
            raise ValueError("Không tìm thấy URL video YouTube")
            
        max_retries = 4
        retry_delay = 1
        ydl_opts = {
            'format': 'bestvideo[height=720]+bestaudio/best',
            'outtmpl': output_file,
            'merge_output_format': 'mp4',
            'quiet': False,
            'no_warnings': False
        }
        
    
        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    update_status_video(f"Đang Render: Đang thử tải video (lần {attempt + 1}/{max_retries})", 
                          data.get('video_id'), task_id, worker_id)
                    
                    # Lấy thông tin video trước
                    video_info = ydl.extract_info(url, download=False)
                    video_title = video_info.get('title', 'Không xác định')
                    print(f"Tiêu đề video: {video_title}")
                    # Tải video
                    ydl.download([url])
                    
                    if os.path.exists(output_file):
                        update_status_video(f"Đang Render: Đã tải xong video", video_id, task_id, worker_id)
                        return {"title": video_title}
                        
            except yt_dlp.DownloadError as e:
                print(f"Lỗi tải video (lần {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    print(f"Chờ {retry_delay} giây trước khi thử lại...")
                    time.sleep(retry_delay)
                    
            except Exception as e:
                print(f"Lỗi không xác định (lần {attempt + 1}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} Không thể tải video sau nhiều lần thử", 
                          data.get('video_id'), task_id, worker_id)
        return None
        
    except Exception as e:
        print(f"Lỗi không xác định trong quá trình xử lý: {str(e)}")
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} Phương thức download youtube thất bại",video_id, task_id, worker_id)
        return None
       
def update_info_video(data, task_id, worker_id):
    try:
        video_url = data.get('url_video_youtube')
        video_id = data.get('video_id')
        
        if not video_url :
            update_status_video(f"Render Lỗi: {os.getenv('name_woker')} lỗi không có url video", 
                          data.get('video_id'), task_id, worker_id)
            return False


        result = get_video_info(data,task_id,worker_id)
        if not result:
            update_status_video(f"Render Lỗi: {os.getenv('name_woker')} lỗi lấy thông tin video và tải video", 
                          data.get('video_id'), task_id, worker_id)
            return False
        
        
        thumnail = get_youtube_thumbnail(video_url,video_id)
        if not thumnail:
            update_status_video(f"Render Lỗi: {os.getenv('name_woker')} lỗi lấy ảnh thumbnail", 
                          data.get('video_id'), task_id, worker_id)
            return False
        update_status_video(f"Đang Render : {os.getenv('name_woker')} Đã lấy thành công thông tin video reup", 
                          video_id, task_id, worker_id,url_thumnail=thumnail,title=result["title"])
        return True

    except requests.RequestException as e:
        print(f"Network error: {e}")
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} Lỗi kết nối - {str(e)}", 
                          data.get('video_id'), task_id, worker_id)
        return False
        
    except ValueError as e:
        print(f"Value error: {e}")
        update_status_video(f"Render Lỗi: {str(e)}", 
                          data.get('video_id'), task_id, worker_id)
        return False
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        update_status_video(f"Render Lỗi: {os.getenv('name_woker')} Lỗi không xác định - {str(e)}", 
                          data.get('video_id'), task_id, worker_id)
        return False
    
def remove_invalid_chars(string):
    # Kiểm tra nếu đầu vào không phải chuỗi
    if not isinstance(string, str):
        return ''
    # Loại bỏ ký tự Unicode 4 byte
    return re.sub(r'[^\u0000-\uFFFF]', '', string)

def get_youtube_thumbnail(youtube_url, video_id):
    try:
        video_id = str(video_id)

        pattern = r'(?:https?:\/\/)?(?:www\.)?youtu(?:be)?\.(?:com|be)(?:\/watch\?v=|\/)([^\s&]+)'
        match = re.findall(pattern, youtube_url)

        if not match:
            print("❌ Invalid YouTube URL")
            return False

        video_id_youtube = match[0]

        thumbnails = {
            'max': f'https://i3.ytimg.com/vi/{video_id_youtube}/maxresdefault.jpg',
            'hq': f'https://i3.ytimg.com/vi/{video_id_youtube}/hqdefault.jpg',
            'mq': f'https://i3.ytimg.com/vi/{video_id_youtube}/mqdefault.jpg',
            'sd': f'https://i3.ytimg.com/vi/{video_id_youtube}/sddefault.jpg',
            'default': f'https://i3.ytimg.com/vi/{video_id_youtube}/default.jpg'
        }

        save_dir = os.path.join('media', video_id, 'thumbnail')
        os.makedirs(save_dir, exist_ok=True)

        for quality, url in thumbnails.items():
            try:
                response = request.urlopen(url)
                if response.status == 200:
                    file_path = os.path.join(save_dir, f"{video_id_youtube}_{quality}.jpg")
                    with open(file_path, 'wb') as f:
                        f.write(response.read())
                    print(f"✅ Tải thành công: {file_path}")
                    return file_path
            except (HTTPError, URLError) as e:
                print(f"❌ Lỗi khi tải ảnh {quality}: {e}")
                time.sleep(1)
                continue

        print("❌ Không tìm thấy ảnh nào tải được")
        return False

    except Exception as e:
        print(f"❌ Lỗi không xác định: {e}")
        return False


class HttpClient:
    def __init__(self, url, min_delay=1.0):
        self.url = url
        self.lock = Lock()
        self.last_send_time = 0
        self.min_delay = min_delay
        
        self.important_statuses = [
            "Render Thành Công : Đang Chờ Upload lên Kênh",
            "Đang Render : Upload file File Lên Server thành công!",
            "Đang Render : Đang xử lý video render",
            "Đang Render : Đã lấy thành công thông tin video reup",
            "Đang Render : Đã chọn xong video nối",
            "Render Lỗi"
        ]

    def should_send(self, status):
        current_time = time.time()
        time_since_last = current_time - self.last_send_time

        if status and any(keyword in status for keyword in self.important_statuses):
            return True
            
        return time_since_last >= self.min_delay

    def send(self, data, file_data=None, max_retries=3):
        with self.lock:
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
                            return True
                    except requests.Timeout:
                        pass
                    except requests.RequestException:
                        pass

                    time.sleep(min(2 ** attempt, 10))

                return False
            except Exception:
                return False


http_client = HttpClient(url=os.getenv('url_web') + "/api/")

def update_status_video(status_video, video_id, task_id, worker_id, url_thumnail=None, url_video=None, title=None, id_video_google=None):
    data = {
        'action': 'update_status',
        'video_id': video_id,
        'status': status_video,
        'task_id': task_id,
        'worker_id': worker_id,
        'title': remove_invalid_chars(title),
        'url_video': url_video,
        'id_video_google': id_video_google,
        "secret_key": os.environ.get('SECRET_KEY')
    }

    if url_thumnail:
        try:
            with open(url_thumnail, 'rb') as f:
                data_file = {'thumnail': f}
                http_client.send(data, file_data=data_file)
        except FileNotFoundError:
            pass
    else:
        http_client.send(data)
        

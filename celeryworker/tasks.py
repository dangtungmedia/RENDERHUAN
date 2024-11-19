import os
from celery import shared_task, Celery
import os, shutil, urllib
import time
import requests
import json
from PIL import Image, ImageDraw, ImageFont
import asyncio
import math
import urllib
import edge_tts, random, subprocess
import asyncio, json, shutil
from googletrans import Translator
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist
import math
from datetime import timedelta, datetime
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
import re
from datetime import datetime, timedelta
import re
import yt_dlp
import decimal
import os
import random, subprocess
import decimal
from proglog import ProgressBarLogger
from tqdm import tqdm
from celery.signals import task_failure,task_revoked
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
from dotenv import load_dotenv

# Nạp biến môi trường từ file .env
load_dotenv()

SECRET_KEY="ugz6iXZ.fM8+9sS}uleGtIb,wuQN^1J%EvnMBeW5#+CYX_ej&%"
# SERVER='http://daphne:5505'
SERVER=os.environ.get('SERVER')

def delete_directory(video_id):
    directory_path = f'media/{video_id}'
    
    # Kiểm tra nếu thư mục tồn tại
    if os.path.exists(directory_path):
        # Kiểm tra xem thư mục có trống không
        if not os.listdir(directory_path):
            try:
                # Nếu thư mục trống, dùng os.rmdir để xóa
                os.rmdir(directory_path)
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
    update_status_video("Render Lỗi : Quá Thời gian render videos", video_id, task_id, worker_id)
    delete_directory(video_id)
    
# Xử lý khi task bị hủy
@task_revoked.connect
def clean_up_on_revoke(sender, request, terminated, signum, expired, **kw):
    task_id = request.id
    print(f"Task {task_id} bị hủy.")
    print(kw)
    if request.args:
        video_id = request.args[0].get('video_id')
        delete_directory(video_id)
    else:
        print(f"Không thể tìm thấy video_id cho task {task_id} vì không có args.")


@shared_task(bind=True, priority=0,name='render_video',time_limit=14200,queue='render_video_content')
def render_video(self, data):
    task_id = render_video.request.id
    worker_id = render_video.request.hostname  # Lưu worker ID
    video_id = data.get('video_id')
    print(data)
    update_status_video("Đang Render : Đang lấy thông tin video render", data['video_id'], task_id, worker_id)
    success = create_or_reset_directory(f'media/{video_id}')

    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video("Render Lỗi : Không thể tạo thư mục", data['video_id'], task_id, worker_id)
        return
    update_status_video("Đang Render : Tạo thư mục thành công", data['video_id'], task_id, worker_id)

    # Tải xuống hình ảnh
    success = download_image(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video("Render Lỗi : Không thể tải xuống hình ảnh", data['video_id'], task_id, worker_id)
        return
    update_status_video("Đang Render : Tải xuống hình ảnh thành công", data['video_id'], task_id, worker_id)
    #THử
    if not data.get('url_audio'):
        # Tải xuống âm thanh oki
        success = download_audio(data, task_id, worker_id)
        if not success:
            update_status_video("Render Lỗi : Không thể tải xuống âm thanh", data['video_id'], task_id, worker_id)
            shutil.rmtree(f'media/{video_id}')
            return
        update_status_video("Đang Render : Tải xuống âm thanh thành công", data['video_id'], task_id, worker_id)

    #nối giọng đọc và chèn nhạc nền
    success = merge_audio_video(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video("Render Lỗi : Không thể nối giọng đọc và chèn nhạc nền", data['video_id'], task_id, worker_id)
        return
    update_status_video("Đang Render : Nối giọng đọc và chèn nhạc nền thành công", data['video_id'], task_id, worker_id)


    # Tạo video
    success = create_video_lines(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video("Render Lỗi : Không thể tạo video", data['video_id'], task_id, worker_id)
        return
    update_status_video("Đang Render : Tạo video thành công", data['video_id'], task_id, worker_id)


    # Tạo phụ đề cho video
    success = create_subtitles(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video("Render Lỗi : Không thể tạo phụ đề", data['video_id'], task_id, worker_id)
        return
    update_status_video("Đang Render : Tạo phụ đề thành công", data['video_id'], task_id, worker_id)

    # Tạo file
    success = create_video_with_retries(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video("Render Lỗi : Không thể tạo file", data['video_id'], task_id, worker_id)
        return
    
    update_status_video("Đang Render : Tạo file thành công", data['video_id'], task_id, worker_id)
    time.sleep(5)

    success = upload_video(data, task_id, worker_id)
    if not success:
        update_status_video("Render Lỗi : Không thể upload video", data['video_id'], task_id, worker_id)
        return
    update_status_video(f"Render Thành Công : Đang Chờ Upload lên Kênh", data['video_id'], task_id, worker_id)

@shared_task(bind=True, priority=10,name='render_video_reupload',time_limit=140000,queue='render_video_reupload')
def render_video_reupload(self, data):
    task_id = render_video.request.id
    worker_id = render_video.request.hostname 
    video_id = data.get('video_id')
    update_status_video("Đang Render : Đang lấy thông tin video render", data['video_id'], task_id, worker_id)
    
    success = update_info_video(data, task_id, worker_id)
    if not success:
        update_status_video("Render Lỗi : Không thể cập nhật thông tin video", data['video_id'], task_id, worker_id)
        return
    update_status_video("Đang Render : Cập nhật thông tin video thành công", data['video_id'], task_id, worker_id)
    
    
    success = create_or_reset_directory(f'media/{video_id}')
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video("Render Lỗi : Không thể tạo thư mục", data['video_id'], task_id, worker_id)
        return

    if data.get('url_reupload'):
        success = downdload_video_reup(data, task_id, worker_id)
        if not success:
            update_status_video("Render Lỗi : Không thể tải xuống video", data['video_id'], task_id, worker_id)
            shutil.rmtree(f'media/{video_id}')
            return
    update_status_video("Đang Render : Tải xuống video thành công", data['video_id'], task_id, worker_id)

    # Điều chỉnh tốc độ và cao độ của video
    success = adjust_video_speed_and_pitch(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    success = create_video_reup(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        return
    
    success = upload_video(data, task_id, worker_id)
    if not success:
        shutil.rmtree(f'media/{video_id}')
        update_status_video("Render Lỗi : Không thể upload video", data['video_id'], task_id, worker_id)
        return
    update_status_video(f"Render Thành Công : Đang Chờ Upload lên Kênh", data['video_id'], task_id, worker_id)

class UploadProgress:
    def __init__(self, data, task_id, worker_id):
        self.last_printed_percent = 0
        self.data = data
        self.task_id = task_id
        self.worker_id = worker_id

    def progress_callback(self, monitor):
        # Calculate percentage uploaded
        percent_complete = (monitor.bytes_read / monitor.len) * 100
        # Check if the percentage has increased by at least 1%
        if int(percent_complete) > self.last_printed_percent:
            self.last_printed_percent = int(percent_complete)
            # Print the percentage of upload completed
            print(f"Uploaded: {self.last_printed_percent}%")
            update_status_video(f"Đang Render : Đang Upload File Lên Server {self.last_printed_percent}%", self.data.get('video_id'), self.task_id, self.worker_id)

def upload_video(data, task_id, worker_id):
    video_id = data.get('video_id')
    name_video = data.get('name_video')
    video_path = f'media/{video_id}/{name_video}.mp4'
    url = f'{SERVER}/api/'

    update_status_video(f"Đang Render : Đang Upload File Lên Server", video_id, task_id, worker_id)
    
    payload = {
        'video_id': str(video_id),
        'action': 'upload',
        'secret_key': SECRET_KEY
    }

    try:
        with open(video_path, 'rb') as video_file:
            # Prepare the payload with the file and other fields
            encoder = MultipartEncoder(
                fields={
                    'video_id': str(payload['video_id']),
                    'action': payload['action'],
                    'secret_key': payload['secret_key'],
                    'file': (os.path.basename(video_path), video_file, 'application/octet-stream')
                }
            )
            
            # Create an instance of the UploadProgress class
            progress = UploadProgress(data, task_id, worker_id)
            
            # Create a monitor to use with the request
            monitor = MultipartEncoderMonitor(encoder, progress.progress_callback)
            
            # Make the POST request to upload the video with streaming data
            response = requests.post(
                url,
                data=monitor,
                headers={'Content-Type': monitor.content_type}
            )
        
        # Check if the request was successful
        if response.status_code == 200:
            print("\nUpload successful!")
            print("Response:", response.json())  # Print the response JSON for confirmation
            shutil.rmtree(f'media/{video_id}')
            return True
        else:
            print(f"\nUpload failed with status code: {response.status_code}")
            print("Response:", response.text)
            return False

    except FileNotFoundError:
        print(f"Error: The file {video_path} was not found.")
        return False
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

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

    audio_file = f'media/{video_id}/audio.wav'
    fonts_dir = r'font'

    # Kiểm tra sự tồn tại của file audio
    if not os.path.exists(audio_file):
        print(f"Audio file not found: {audio_file}")
        return False
    ffmpeg_command = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', input_files_video_path,
            '-i', audio_file,
            '-vf', f"subtitles={ass_file_path}:fontsdir={fonts_dir}",
            '-c:v', 'libx264',
            '-map', '0:v',
            '-map', '1:a',
            '-y',
            f"media/{video_id}/{name_video}.mp4"
        ]
    try:
        result = subprocess.run(ffmpeg_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg failed with error: {e.stderr}")
        return False
    return True

def create_video_with_retries(data, task_id, worker_id, max_retries=10):
    for attempt in range(max_retries):
        if create_video_file(data, task_id, worker_id):
            print(f"Video creation succeeded on attempt {attempt + 1}")
            return True
        else:
            print(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(1)  # Chờ một chút trước khi thử lại
    print("Max retries reached, video creation failed.")
    return False

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
    font_text = find_font_file(font, r'fonts')

    font_size = data.get('font_size')

    font = ImageFont.truetype(font_text,font_size)

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
                duration = get_audio_duration(f'media/{video_id}/voice/{iteam["id"]}.wav')
                duration_milliseconds = duration * 1000
                end_time = start_time + timedelta(milliseconds=duration_milliseconds)
                # end_time = start_time + duration
                # Viết phụ đề
                ass_file.write(f"Dialogue: 0,{format_timedelta_ass(start_time)},{format_timedelta_ass(end_time)},Default,,0,0,0,,2,{get_text_lines(data,iteam['text'])}\n")
                start_time = end_time
            return True
    except:
        return False

def merge_audio_video(data, task_id, worker_id):
    try:
        update_status_video("Đang Render: đang ghép giọng đọc", data['video_id'], task_id, worker_id)
        video_id = data.get('video_id')
        
        # Tải xuống tệp âm thanh nếu có URL âm thanh
        if data.get('url_audio'):
            max_retries = 30
            retries = 0
            url_audio = f"{SERVER}{data.get('url_audio')}"
            while retries < max_retries:
                try:
                    response = requests.get(url_audio, stream=True)
                    if response.status_code == 200:
                        os.makedirs(f'media/{video_id}', exist_ok=True)
                        with open(f'media/{video_id}/audio.wav', 'wb') as file:
                            for chunk in response.iter_content(chunk_size=1024):
                                if chunk:
                                    file.write(chunk)
                        print("Tải xuống thành công.")
                        break
                    else:
                        print(f"Lỗi {response.status_code}: Không thể tải xuống tệp.")
                except requests.RequestException as e:
                    print(f"Lỗi tải xuống: {e}")
                retries += 1
                time.sleep(5)
                print(f"Thử lại {retries}/{max_retries}")
            else:
                return False
        else:
            # Tạo audio.wav nếu không có tệp âm thanh
            ffmpeg_command = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', f'media/{video_id}/input_files.txt',
                '-c', 'copy',
                f'media/{video_id}/chace_audio.wav'
            ]
            subprocess.run(ffmpeg_command, check=True)

        # Xử lý nhạc nền nếu channel_music_active được bật
        if data.get('channel_music_active'):
            audio_duration = get_audio_duration(f'media/{video_id}/chace_audio.wav')
            if audio_duration:
                # Lấy ngẫu nhiên một file nhạc từ thư mục background_music_folder
                background_music_folder = "music_background"  # Thay đổi thành đường dẫn thư mục chứa nhạc của bạn
                music_files = [f for f in os.listdir(background_music_folder) if f.endswith(('.mp3', '.wav'))]
                
                if music_files:
                    background_music = os.path.join(background_music_folder, random.choice(music_files))
                    start_time = random.uniform(0, max(0, audio_duration - 10))  # Chọn ngẫu nhiên thời gian bắt đầu, ít nhất là 10s trước khi hết file.
                    output_audio_with_music = f"media/{video_id}/audio.wav"
                    
                    ffmpeg_bgm_command = [
                            'ffmpeg',
                            '-i', f'media/{video_id}/chace_audio.wav',           # Tệp âm thanh giọng đọc
                            '-i', background_music,                               # Tệp nhạc nền
                            '-filter_complex', f"[1]atrim=start={start_time}:duration={audio_duration},volume=0.15[bgm];[0][bgm]amix=inputs=2:duration=first",
                            '-y', output_audio_with_music                         # Đầu ra âm thanh đã lồng nhạc nền
                        ]
                    subprocess.run(ffmpeg_bgm_command, check=True)
                    print("Lồng nhạc nền thành công.")
                else:
                    print("Thư mục nhạc nền trống.")
                    return False
        else:
            shutil.move(f'media/{video_id}/chace_audio.wav', f'media/{video_id}/audio.wav')
            
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
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

def cut_and_scale_video_random(input_video, output_video, duration, scale_width, scale_height, overlay_video_dir):
    video_length = get_video_duration(input_video)
    start_time = random.uniform(0, video_length - duration)
    
    start_time_str = format_time(start_time)
    end_time = format_time(duration)
    
    base_video = get_random_video_from_directory(overlay_video_dir)
    is_overlay_video = random.choice([True, False])
    
    if is_overlay_video:
        cmd = [
            "ffmpeg",
            "-i", input_video,
            "-ss", start_time_str,  # Thời gian bắt đầu cắt của video đầu vào
            "-t", str(duration),    # Thời lượng video cần cắt
            "-i", base_video,
            "-ss", start_time_str,  # Thời gian bắt đầu cắt của video chồng
            "-t", str(duration),    # Thời lượng video cần cắt
            "-filter_complex", f"[0:v]scale={scale_width}:{scale_height}[bg];"
                            f"[1:v]scale={scale_width}:{scale_height}[overlay_scaled];"
                            f"[bg][overlay_scaled]overlay=format=auto,format=yuv420p[outv]",  # format=auto tự động xử lý alpha
            "-map", "[outv]",
            "-r", "24",            # Tốc độ khung hình đầu ra
            "-c:v", "libx264",     # Codec video
            "-crf", "18",          # Chất lượng video
            "-preset", "medium",   # Tốc độ mã hóa
            "-pix_fmt", "yuv420p", # Đảm bảo tương thích với đầu ra
            "-vsync", "2",         # Đồng bộ hóa video
            "-loglevel", "debug",  # Đặt mức log level để ghi chi tiết
            "-y",                  # Ghi đè file đầu ra nếu đã tồn tại
            output_video
        ]
    else:
        cmd = [
            "ffmpeg",
            "-i", input_video,
            "-ss", start_time_str,      # Thời gian bắt đầu cắt của video
            "-t", str(duration),        # Thời lượng video cần cắt
            "-vf", f"scale={scale_width}:{scale_height}",  # Thay đổi độ phân giải
            "-r", "24",                 # Tốc độ khung hình đầu ra
            "-c:v", "libx264",          # Codec video
            "-crf", "18",               # Chất lượng video
            "-preset", "medium",        # Tốc độ mã hóa
            "-pix_fmt", "yuv420p",      # Đảm bảo tương thích với đầu ra
            "-vsync", "2",              # Đồng bộ hóa video
            "-loglevel", "debug",       # Đặt mức log level để ghi chi tiết
            "-y",                       # Ghi đè file đầu ra nếu đã tồn tại
            output_video
        ]

    
    try:
        # Chạy lệnh FFmpeg
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

def translate_text(text, src_lang='auto', dest_lang='en'):
    translator = Translator()
    translation = translator.translate(text, src=src_lang, dest=dest_lang)
    return translation.text

def find_keywords(text, num_keywords=5):
    # Tokenize the text
    tokens = word_tokenize(text)
    # Remove stopwords
    stop_words = set(stopwords.words('english'))
    filtered_tokens = [word for word in tokens if word.lower() not in stop_words]
    # Compute the frequency distribution
    freq_dist = FreqDist(filtered_tokens)
    # Get the most common keywords
    keywords = [word for word, freq in freq_dist.most_common(num_keywords)]
    return keywords

def search_pixabay_videos(api_key, query, min_duration):
    filtered_videos = []
    for page in range(1,2):
        url = f"https://pixabay.com/api/videos/?key={api_key}&q={query}&per_page=200&page={page}"
        print(url)
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            for item in data['hits']:
                for video in item['videos'].values():
                    if video['height'] == 1080 and item['duration'] >= min_duration:
                        filtered_videos.append(video['url'])
    return filtered_videos

def get_video_random(data,duration,input_text,file_name):
    translated_text = translate_text(input_text)
    # Find the main keywords in the translated sentence
    keywords = find_keywords(translated_text)
    # Tìm video từ Pixabay
    api_key = "38396855-7183824f50d61fd232c569758" 

    list_url = []
    for keyword in keywords:
        result = search_pixabay_videos(api_key, keyword, duration)
        list_url.extend(result)
    list_url.extend(result)

    video_id = data.get('video_id')
    choice = random.choice(list_url)


    path = f'media/{video_id}/videodownload'
    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    
    response = requests.get(choice, stream=True)
    if response.status_code == 200:
        video_path = f'media/{video_id}/videodownload/{file_name}.mp4'
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        return video_path
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

def process_video_segment(data, text_entry, data_sub, i, video_id, task_id, worker_id):
    """Hàm tạo video cho một đoạn văn bản."""
    # Tính thời lượng của đoạn video
    if data.get('file-srt'):
        start_time, end_time = data_sub[i]
        duration = convert_to_seconds(end_time) - convert_to_seconds(start_time)
    else:
        duration = get_audio_duration(f'media/{video_id}/voice/{text_entry["id"]}.wav')

    out_file = f'media/{video_id}/video/{text_entry["id"]}.mp4'
    file = get_filename_from_url(text_entry.get('url_video', ''))
    
    if file == 'no-image-available.png' or not text_entry.get('url_video'):
        # Chọn video ngẫu nhiên có độ dài phù hợp từ API
        video_directory = f'media/{video_id}/video_backrought'
        os.makedirs(video_directory, exist_ok=True)

        max_retries = 10  # Giới hạn số lần thử tải video
        retries = 0

        while retries < max_retries:
            list_video = os.listdir(video_directory)
            data_request = {
                'secret_key': SECRET_KEY,
                'action': 'get-video-backrought',
                'task_id': task_id,
                'worker_id': worker_id,
                'list_video': list_video,
                'duration': duration,
            }
            url = f'{SERVER}/api/'
            response = requests.post(url, json=data_request)

            if response.status_code == 200:
                filename = response.headers.get('Content-Disposition').split('filename=')[1].strip('"')
                video_path = os.path.join(video_directory, filename)
                
                # Lưu video tải về
                with open(video_path, 'wb') as f:
                    f.write(response.content)
                
                # Kiểm tra và thoát khỏi vòng lặp nếu tải thành công
                if os.path.exists(video_path) and get_video_duration(video_path) >= duration:
                    cut_and_scale_video_random(video_path, out_file, duration, 1920, 1080, 'video_screen')
                    break
                else:
                    print("Video tải về không đạt độ dài yêu cầu.")
            else:
                print(f"Lỗi {response.status_code}: Không thể tải xuống tệp từ API.")
            
            retries += 1
            print(f"Thử lại {retries}/{max_retries}")

        # Kiểm tra nếu vòng lặp kết thúc mà không tải được video
        if retries == max_retries:
            print("Không thể tải video phù hợp sau nhiều lần thử.")
            return False  # Dừng lại nếu không thành công sau max_retries lần thử

    else:
        # Tạo video từ hình ảnh nếu có URL hình ảnh
        image_file = f'media/{video_id}/image/{file}'
        if os.path.exists(image_file):
            random_choice = random.choice([True, False])
            if random_choice:
                image_to_video_zoom_in(image_file, out_file, duration, 1920, 1080, 'video_screen')
            else:
                image_to_video_zoom_out(image_file, out_file, duration, 1920, 1080, 'video_screen')
        else:
            print(f"Hình ảnh không tồn tại: {image_file}")
            return False
    return True

def create_video(data, task_id, worker_id):
    try:
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
                return False

        # Sử dụng ThreadPoolExecutor với tối đa 4 luồng
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Tạo các công việc xử lý video đồng thời
            futures = {
                executor.submit(process_video_segment, data, text_entry, data_sub, i, video_id, worker_id): text_entry
                for i, text_entry in enumerate(text_entries)
            }

            # Theo dõi tiến trình của từng công việc đã hoàn thành
            for future in as_completed(futures):
                try:
                    result = future.result()  # Lấy kết quả từ mỗi công việc đã hoàn thành
                    if result:
                        processed_entries += 1
                        percent_complete = (processed_entries / total_entries) * 100
                        update_status_video(f"Đang Render : Đang tạo video {percent_complete:.2f}%", video_id, task_id, worker_id)
                    else:
                        print("Lỗi trong quá trình tạo video cho một đoạn.")
                        return False
                except Exception as e:
                    print(f"Lỗi khi tạo video: {e}")
                    update_status_video(
                        f"Render Lỗi : Lỗi khi tạo video - {e}",
                        video_id, task_id, worker_id
                    )
                    return False  # Dừng tiến trình khi có lỗi
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False
    
def create_video_lines(data, task_id, worker_id, max_retries=5):
    for attempt in range(max_retries):
        if create_video(data, task_id, worker_id):
            print(f"Video creation succeeded on attempt {attempt + 1}")
            return True
        else:
            print(f"Attempt {attempt + 1} failed, retrying...")
            time.sleep(1)  # Chờ một chút trước khi thử lại
    print("Max retries reached, video creation failed.")
    return False

def get_random_video_from_directory(directory_path):
    video_files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
    return os.path.join(directory_path, random.choice(video_files))

def image_to_video_zoom_out(input_image, output_video, duration, scale_width, scale_height, overlay_video):
    is_overlay_video = random.choice([True, False])
    base_video = get_random_video_from_directory(overlay_video)
    time_video = format_time(duration)
    if is_overlay_video:
        ffmpeg_command = [
            'ffmpeg',
            '-loop', '1',
            '-framerate','24',
            '-i', input_image,
            '-i', base_video,
            '-filter_complex',
            f"[0:v]format=yuv420p,scale=8000:-1,zoompan=z='zoom+0.001':x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):d={duration}*24:s={scale_width}x{scale_height}:fps=24[bg];[1:v]scale={scale_width}:{scale_height}[overlay_scaled];[bg][overlay_scaled]overlay=format=auto,format=yuv420p[outv]",
            '-map', '[outv]',
            '-t', time_video,
            "-r", "24",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "medium",
            "-loglevel", "debug",  # Thêm tùy chọn loglevel
            "-y",
            output_video
        ]

    else:
        ffmpeg_command = [
        'ffmpeg',
        '-loop', '1',
        '-framerate','24',
        '-i', input_image,
        '-vf',
        f"format=yuv420p,scale=8000:-1,zoompan=z='zoom+0.001':x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):d={duration}*24:s={scale_width}x{scale_height}:fps=24",
        '-t', time_video,
        "-r", "24",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-loglevel", "debug",  # Thêm tùy chọn loglevel
        "-y",
        output_video
    ]
    try:
        # Chạy lệnh FFmpeg
        subprocess.run(ffmpeg_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"lỗi chạy FFMPEG {e}")

def image_to_video_zoom_in(input_image, output_video, duration, scale_width, scale_height, overlay_video):
    is_overlay_video = random.choice([True, False])
    base_video = get_random_video_from_directory(overlay_video)
    time_video = format_time(duration)
    if is_overlay_video:
        ffmpeg_command = [
            'ffmpeg',
            '-loop', '1',
            '-framerate','24',
            '-i', input_image,
            '-i', base_video,
            '-filter_complex',
            f"[0:v]format=yuv420p,scale=8000:-1,zoompan=z='zoom+0.001':x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):d={duration}*24:s={scale_width}x{scale_height}:fps=24[bg];[1:v]scale={scale_width}:{scale_height}[overlay_scaled];[bg][overlay_scaled]overlay=format=auto,format=yuv420p[outv]",
            '-map', '[outv]',
            '-t', time_video,
            "-r", "24",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "medium",
            "-loglevel", "debug",  # Thêm tùy chọn loglevel
            "-y",
            output_video
        ]

    else:
        ffmpeg_command = [
        'ffmpeg',
        '-loop', '1',
        '-framerate','24',
        '-i', input_image,
        '-vf',
        f"format=yuv420p,scale=8000:-1,scale=8000:-1,zoompan=z='zoom+0.001':x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):d={duration}*24:s={scale_width}x{scale_height}:fps=24",
        '-t', time_video,
        "-r", "24",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-loglevel", "debug",  # Thêm tùy chọn loglevel
        "-y",
        output_video
    ]
    try:
        # Chạy lệnh FFmpeg
        subprocess.run(ffmpeg_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"lỗi chạy FFMPEG {e}")

def process_voice_entry(data, text_entry, video_id, task_id, worker_id, language):
    """Hàm xử lý giọng nói cho từng trường hợp ngôn ngữ."""
    file_name = f'media/{video_id}/voice/{text_entry["id"]}.wav'
    success = False
    
    # Xử lý ngôn ngữ tương ứng và kiểm tra kết quả tải
    if language == 'Japanese-VoiceVox':
        success = get_voice_japanese(data, text_entry['text'], file_name)
    elif language == 'Korea-TTS':
        success = get_voice_korea(data, text_entry['text'], file_name)
    elif language == 'VOICE GPT AI':
        success = get_voice_chat_gpt(data, text_entry['text'], file_name)
    
    elif language == 'AI-HUMAN':
        success = get_voice_chat_ai_human(data, text_entry['text'], file_name)
        
    elif language == 'SUPER VOICE':
        success = get_voice_super_voice(data, text_entry['text'], file_name)
    
    # Trả về False nếu tải không thành công, dừng toàn bộ
    if not success:
        print(f"Lỗi: Không thể tạo giọng nói cho đoạn văn bản ID {text_entry['id']}")
        return False, None  # Trả về False để đánh dấu lỗi
    return text_entry['id'], file_name  # Trả về ID và đường dẫn tệp đã tạo

def download_audio(data, task_id, worker_id):
    try:
        print("Đang tải giọng nói...")
        language = data.get('language')
        video_id = data.get('video_id')
        text = data.get('text_content')

        # Tải các đoạn văn bản từ `text_content`
        text_entries = json.loads(text)
        total_entries = len(text_entries)

        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(f'media/{video_id}/voice', exist_ok=True)

        # Danh sách giữ đường dẫn tệp theo thứ tự
        result_files = [None] * total_entries
        processed_entries = 0

        # Khởi tạo luồng xử lý tối đa 20 luồng
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(process_voice_entry, data, text_entry, video_id, task_id, worker_id, language): idx
                for idx, text_entry in enumerate(text_entries)
            }

            # Mở file để ghi các đường dẫn tệp âm thanh theo thứ tự
            with open(f'media/{video_id}/input_files.txt', 'w') as file:
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        result = future.result()  # Lấy kết quả từ công việc hoàn thành
                        if result[0] is False:  # Nếu có lỗi trong quá trình tải
                            print("Lỗi khi tải giọng nói, dừng toàn bộ tiến trình.")
                            # Hủy tất cả các công việc chưa hoàn thành
                            for f in futures.keys():
                                f.cancel()
                            return False
                        entry_id, file_name = result
                        result_files[idx] = file_name  # Đảm bảo thứ tự cho file_name
                        processed_entries += 1
                        percent_complete = (processed_entries / total_entries) * 100
                        update_status_video(
                            f"Đang Render : Đang tạo giọng đọc {percent_complete:.2f}%",
                            video_id, task_id, worker_id
                        )
                    except Exception as e:
                        print(f"Lỗi khi xử lý giọng đọc cho đoạn văn bản {text_entries[idx]['id']}: {e}")
                        update_status_video(
                            f"Render Lỗi : Lỗi khi tạo giọng đọc - {e}",
                            video_id, task_id, worker_id
                        )
                        # Hủy tất cả các công việc chưa hoàn thành
                        for f in futures.keys():
                            f.cancel()
                        return False  # Dừng toàn bộ nếu gặp lỗi

                # Ghi vào input_files.txt theo đúng thứ tự ban đầu của text_entries
                for file_name in result_files:
                    if file_name:
                        file.write(f"file 'voice/{os.path.basename(file_name)}'\n")
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def format_timestamp(seconds):
    """Chuyển đổi thời gian từ giây thành định dạng SRT (hh:mm:ss,ms)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def get_voice_japanese(data, text, file_name):
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
            url_query = f"http://voicevox:50021/audio_query?speaker={voice_id}"
            response_query = requests.post(url_query, params={'text': text})
            response_query.raise_for_status()  # Kiểm tra mã trạng thái HTTP
            
            # Lấy JSON từ phản hồi và điều chỉnh tốc độ
            query_json = response_query.json()
            query_json["speedScale"] = 1.0  # Điều chỉnh tốc độ

            # Yêu cầu tạo âm thanh
            url_synthesis = f"http://voicevox:50021/synthesis?speaker={voice_id}"
            headers = {"Content-Type": "application/json"}
            response_synthesis = requests.post(url_synthesis, headers=headers, json=query_json)
            response_synthesis.raise_for_status()  # Kiểm tra mã trạng thái HTTP

            # Ghi nội dung phản hồi vào tệp
            with open(file_name, 'wb') as f:
                f.write(response_synthesis.content)

            # Kiểm tra độ dài tệp âm thanh
            duration = get_audio_duration(file_name)
            if duration > 0:  # Đảm bảo rằng âm thanh có độ dài hợp lý
                success = True
                print(f"Tạo giọng nói thành công cho '{text}' tại {file_name}")
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
      
def get_voice_super_voice(data, text, file_name):
    # Tạo thư mục nếu chưa tồn tại
    directory = os.path.dirname(file_name)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        
    success = False
    attempt = 0
    
    print("Creating voice for SUPER VOICE", text)
    while not success and attempt < 10:
        try:
            idToken = login_data()
            if not idToken:
                return False
            access_token = get_access_token(idToken)
            if not access_token:
                return False

            idToken_active = active_token(access_token)
            if not idToken_active:
                return False

            url_voice_text = get_voice_text(idToken_active, text, data)
            if not url_voice_text:
                return False

            url_voice = get_audio_url(idToken_active, url_voice_text)
            if not url_voice:
                return False

            final_url = get_url_voice_succes(idToken_active, url_voice)
            if not final_url:
                return False
            
            response = requests.get(final_url)
            if response.status_code == 200:
                with open(file_name, 'wb') as f:
                    f.write(response.content)
                # Kiểm tra độ dài tệp âm thanh
                duration = get_audio_duration(file_name)
                if duration > 0:
                    success = True
                    print(f"Tạo giọng nói thành công cho '{text}' tại {file_name}")
                else:
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    print(f"Lỗi: Tệp âm thanh {file_name} không hợp lệ.")
            else:
                print(f"Lỗi: API trả về trạng thái {response.status_code}. Thử lại...")
        except requests.RequestException as e:
            print(f"Lỗi mạng khi gọi API: {e}. Thử lại...")
        except Exception as e:
            print(f"Lỗi không xác định: {e}. Thử lại...")
            
        attempt += 1
        if not success:
            time.sleep(1)
    if not success:
        print(f"Không thể tạo giọng nói sau {attempt} lần thử.")
    return success
      
def get_url_voice_succes(idToken, url_voice):
    print(url_voice)
    url = url_voice + '/cloudfront'
    headers = {
        'Authorization': f'Bearer {idToken}'
    }
    
    response = requests.get(url, headers=headers)
    
    # Kiểm tra mã trạng thái và phản hồi JSON
    if response.status_code == 200:
        try:
            return response.json()['result']
        except KeyError:
            print("Không tìm thấy trường 'result' trong phản hồi.")
            return None
    else:
        print("Yêu cầu đến API thất bại với mã trạng thái:", response.status_code)
        return None
  
def get_audio_url(idToken, url_voice_text):
    url = "https://typecast.ai/api/speak/batch/get"
    headers = {
        'Authorization': f'Bearer {idToken}'
    }

    # Thử lại tối đa 5 lần nếu có lỗi
    for attempt in range(30):
        print(f"Attempt {attempt + 1} to send request.")
        
        # Gửi yêu cầu POST đến API
        response = requests.post(url, headers=headers, json=url_voice_text)
        print("Response status code:", response.status_code)
        
        print(response.json())
        # Kiểm tra mã trạng thái và phản hồi JSON
        if response.status_code == 200:
            try:
                result = response.json().get("result", [])[0]
                audio_url = result.get("audio", {}).get("url")
                if audio_url:
                    return audio_url
                else:
                    print("Không tìm thấy trường 'audio' trong phản hồi.")
                    
            except (KeyError, IndexError, TypeError):
                print("Lỗi trong khi truy cập các trường trong phản hồi JSON.")
        else:
            print("Yêu cầu đến API thất bại với mã trạng thái:", response.status_code)
            print("Nội dung phản hồi lỗi:", response.text)
        # Đợi 2 giây trước khi thử lại nếu không thành công
        time.sleep(1)
    return None     
     
def get_voice_text(idToken, text, data):
    try:
        # Log the original style_name to help identify any formatting issues
        print("Original style_name:",data.get("style"))
        
        # Chuyển đổi `style_name` từ chuỗi JSON thành từ điển Python
        style_name_data = json.loads(data.get("style"))
        print("style_name_data:", style_name_data)

        # Cập nhật trường 'text' với văn bản đầu vào
        style_name_data['text'] = text
        
        # Kiểm tra định dạng JSON trước khi gửi
        style_name_json_string = json.dumps([style_name_data], indent=4)
        print("JSON to be sent:", style_name_json_string)
        
        # URL và headers cho API
        url = 'https://typecast.ai/api/speak/batch/post'
        headers = {
            'Authorization': f'Bearer {idToken}',
            'Content-Type': 'application/json'
        }
        
        # Gửi yêu cầu POST với `style_name_data` trong danh sách
        response = requests.post(url, headers=headers, json=[style_name_data])
        
        print("API response:", response.text)
        # Kiểm tra phản hồi JSON
        if response.status_code == 200:
            try:
                return response.json()["result"]["speak_urls"]
            except KeyError:
                return 
        else:   
            return False
    except json.JSONDecodeError as e:
        print("Lỗi khi giải mã JSON từ 'style_name' trong cơ sở dữ liệu:", e)
        return 
  
def active_token(access_token):
    Params = {
        "key": "AIzaSyBJN3ZYdzTmjyQJ-9TdpikbsZDT9JUAYFk"
    }
    
    data = {
        "token": access_token,
        "returnSecureToken": True
    }
    
    response = requests.post('https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken', params=Params, json=data)
    return response.json()['idToken']
        
def get_access_token(idToken):
    data = {
        "token": idToken
    }

    response = requests.post('https://typecast.ai/api/auth-fb/custom-token', json=data)

    return response.json()["result"]['access_token']
       
def login_data():
    data = {
        "returnSecureToken": True,
        "email": "dangtungmedia@gmail.com",
        "password": "@@Hien17987",
        "clientType": "CLIENT_TYPE_WEB"
        }
    Params = {
        "key": "AIzaSyBJN3ZYdzTmjyQJ-9TdpikbsZDT9JUAYFk"
    }
    
    url = 'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword'
    response = requests.post(url, params=Params, json=data)
    return response.json()['idToken']
                   
def get_filename_from_url(url):
    parsed_url = urllib.parse.urlparse(url)
    path = parsed_url.path
    filename = path.split('/')[-1]
    return filename

def download_single_image(url, local_directory, video_id, task_id, worker_id):
    """Hàm tải xuống một hình ảnh từ URL và lưu vào thư mục đích."""
    print(f"Đang tải xuống hình ảnh từ: {url}")
    for attempt in range(30):  # Thử tải lại 30 lần nếu thất bại
        try:
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                file_path = os.path.join(local_directory, get_filename_from_url(url))
                with open(file_path, 'wb') as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                print(f"Tải xuống thành công: {url}")
                return True  # Trả về True nếu tải thành công
            else:
                print(f"Trạng thái không thành công - {response.status_code} - URL: {url}")
        except requests.RequestException as e:
            print(f"Lỗi yêu cầu khi tải xuống {url}: {e}")
        except Exception as e:
            print(f"Lỗi không xác định khi tải xuống {url}: {e}")
        
        time.sleep(1)  # Đợi 1 giây trước khi thử lại
    return False  # Trả về False nếu không thể tải xuống

def download_image(data, task_id, worker_id):
    video_id = data.get('video_id')
    update_status_video(f"Đang Render : Bắt đầu tải xuống hình ảnh", video_id, task_id, worker_id)

    local_directory = os.path.join('media', str(video_id), 'image')
    os.makedirs(local_directory, exist_ok=True)

    images_str = data.get('images')
    if not images_str:
        return True

    images = json.loads(images_str)
    total_images = len(images)
    if total_images == 0:
        update_status_video(
            f"Đang Render : Không có hình ảnh nào để tải xuống bỏ qua",
            video_id, task_id, worker_id
        )
        return True

    downloaded_images = 0  # Số hình ảnh đã tải xuống thành công

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_url = {
            executor.submit(download_single_image, image, local_directory, video_id, task_id, worker_id): image
            for image in images
        }

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                # Kiểm tra kết quả của từng tương lai
                if future.result():
                    downloaded_images += 1
                    percent_complete = (downloaded_images / total_images) * 100
                    update_status_video(
                        f"Đang Render : Tải xuống hình ảnh thành công ({downloaded_images}/{total_images}) - {percent_complete:.2f}%",
                        video_id, task_id, worker_id
                    )
                else:
                    # Hủy tất cả các tác vụ còn lại khi gặp lỗi tải xuống
                    update_status_video(
                        f"Render Lỗi : Không thể tải xuống hình ảnh - {url}",
                        video_id, task_id, worker_id
                    )
                    for pending in future_to_url:
                        pending.cancel()  # Hủy tất cả các tác vụ chưa hoàn thành
                    return False  # Ngừng tiến trình ngay khi gặp lỗi
            except Exception as e:
                print(f"Lỗi khi tải xuống {url}: {e}")
                update_status_video(
                    f"Render Lỗi : Lỗi không xác định - {e} - {url}",
                    video_id, task_id, worker_id
                )
                # Hủy tất cả các tác vụ còn lại và ngừng tiến trình
                for pending in future_to_url:
                    pending.cancel()
                return False
                
    return True

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

def extract_subtitles(srt_content):
    # Định dạng để phân tích nội dung phụ đề
    subtitle_pattern = re.compile(
        r'(\d+)\s*'              # Số thứ tự
        r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\s*' # Thời gian
        r'(.*?)\s*(?=\d+\s*\d{2}:\d{2}|\Z)', # Văn bản
        re.DOTALL
    )
    
    subtitles = []
    for match in subtitle_pattern.finditer(srt_content):
        index = match.group(1)
        start_time = match.group(2)
        end_time = match.group(3)
        text = match.group(4).strip().replace('\n', ' ')
        subtitles.append({
            'index': index,
            'start_time': start_time,
            'end_time': end_time,
            'text': text
        })
    return subtitles

def downdload_video_reup(data, task_id, worker_id):
    video_id = data.get('video_id')
    output_file = f'media/{video_id}/cache.mp4'
    url = data.get('url_video_youtube')

    # Hàm xử lý tiến trình tải
    def progress_hook(d):
        if d['status'] == 'downloading':
            percent = d['_percent_str'].strip()
            update_status_video(f"Đang Render : Đang tải video {percent}", data['video_id'], task_id, worker_id)
        elif d['status'] == 'finished':
            update_status_video(f"Đang Render :  Đã tải xong video ", data['video_id'], task_id, worker_id)

    # Cấu hình yt-dlp
    ydl_opts = {
        'proxy': os.environ.get('PROXY_URL'), # Thêm proxy
        'format': 'bestvideo[height=720]+bestaudio/best',
        'outtmpl': f"{output_file}",
        'merge_output_format': 'mp4',  # Hợp nhất video và âm thanh thành định dạng MP4,
        'progress_hooks': [progress_hook],  # Thêm hàm xử lý tiến trình
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"Tải âm thanh từ: {url}")
        ydl.download([url])
    return True

def adjust_video_speed_and_pitch(data, task_id, worker_id):
    try:
        update_status_video("Đang Render: Đang chỉnh sửa Speed & Pitch", data['video_id'], task_id, worker_id)
        video_id = data.get('video_id')
        video_path = f'media/{video_id}/cache.mp4'
        output_path = f"media/{video_id}/video_adjusted.mp4"
        
        width, height = get_video_resolution(data.get('video_format'))

        # Retrieve and validate speed and pitch
        speed = data.get('speed_video_crop', 1.0)
        pitch = data.get('pitch_video_crop', 1.0)

        if isinstance(speed, decimal.Decimal):
            speed = float(speed)
        if isinstance(pitch, decimal.Decimal):
            pitch = float(pitch)

        if speed <= 0 or pitch <= 0:
            raise ValueError("Speed and pitch must be greater than zero.")

        update_status_video("Đang Render: Bắt đầu chỉnh Speed & Pitch", data['video_id'], task_id, worker_id)

        command = [
                "ffmpeg",
                "-i", video_path,  # Đường dẫn tới video đầu vào
                "-filter_complex",  # Áp dụng các bộ lọc video và audio
                f"[0:v]setpts={1/speed}*PTS,scale={width}:{height}[v];[0:a]asetrate={44100 * pitch},atempo={speed}[a]",
                "-map", "[v]",  # Lấy video đã xử lý
                "-map", "[a]",  # Lấy audio đã xử lý
                "-c:v", "libx264",  # Mã hóa video với codec H.264
                "-c:a", "aac",  # Mã hóa âm thanh với codec AAC
                "-movflags", "+faststart",  # Tối ưu hóa phát trực tiếp
                "-y",  # Ghi đè file đầu ra nếu đã tồn tại
                output_path  # Đường dẫn tới file đầu ra
            ]

        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            total_duration = None
            progress_bar = None

            for line in process.stderr:
                if "Duration" in line:
                    duration_str = line.split(",")[0].split("Duration:")[1].strip()
                    h, m, s = map(float, duration_str.split(":"))
                    total_duration = int(h * 3600 + m * 60 + s)
                    progress_bar = tqdm(total=total_duration, desc="Rendering", unit="s")

                if "time=" in line and progress_bar:
                    time_str = line.split("time=")[1].split(" ")[0].strip()
                    h, m, s = map(float, time_str.split(":"))
                    current_time = int(h * 3600 + m * 60 + s)
                    progress_bar.n = current_time
                    progress_bar.refresh()
                    percentage = int((current_time / total_duration) * 100)
                    if percentage <= 100:
                        update_status_video(f"Đang Render: Speed & Pitch render {percentage}% hoàn thành", data['video_id'], task_id, worker_id)
            process.wait()
            if process.returncode == 0:
                print(f"Video đã được điều chỉnh tốc độ và cao độ thành công và lưu tại {output_path}")
            else:
                print(f"Đã có lỗi xảy ra: {process.stderr.read()}")
    except Exception as e:
        print(f"An error occurred: {e}")
        update_status_video("Render Lỗi: Không thể điều chỉnh Speed & Pitch", data['video_id'], task_id, worker_id)
        return False

    update_status_video("Đang Render: Chỉnh sửa xong video Speed & Pitch", data['video_id'], task_id, worker_id)
    return True

class MyBarLogger(ProgressBarLogger):
    
    def __init__(self, video_id, task_id, worker_id,status):
        super().__init__()
        self.video_id = video_id
        self.task_id = task_id
        self.worker_id = worker_id
        self.status = status

    def bars_callback(self, bar, attr, value, old_value=None):
        # Every time the logger progress is updated, this function is called        
        total = self.bars[bar]['total']
        if total > 0:
            percentage = (value / total) * 100
        else:
            percentage = 0
        print(bar, attr, percentage)
        if bar == 'chunk':
            text = "đang lưu bộ nhớ tạm"
        else:
            text = "đang lưu video"
        update_status_video(f"{self.status} {text}--{bar} {attr} {percentage:.2f}%", self.video_id, self.task_id, self.worker_id)

def get_video_resolution(video_format):
    # Mapping giữa video_format và kích thước (rộng, cao)
    resolution_mapping = {
        '2160p': (3840, 2160),
        '1440p': (2560, 1440),
        '1080p': (1920, 1080),
        '720p': (1280, 720),
        '480p': (854, 480),
        '360p': (640, 360),
        '240p': (426, 240),
    }
    # Trả về chiều rộng và chiều cao dựa trên video_format
    return resolution_mapping.get(video_format, (1920, 1080))
# Tính vị trí và kích thước mới của video crop
def parse_crop_data(crop_data_str):
    # Tách chuỗi thành các phần tử và chuyển thành dictionary
    data_pairs = crop_data_str.split(',')
    crop_data = {}
    
    for pair in data_pairs:
        key, value = pair.split('=')
        crop_data[key] = int(value)
    
    return crop_data
# Tính toán vị trí và kích thước mới của video crop

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

def process_video_ffmpeg(input_video, output_video, width, height, fps=24, preset="medium",text='',video_id='', task_id='', worker_id=''):
    """
    Hàm sử dụng FFmpeg để xử lý video với các tùy chọn về độ phân giải, tốc độ khung hình và nén video.
    
    :param input_video: Đường dẫn video đầu vào.
    :param output_video: Đường dẫn video đầu ra (sau khi xử lý).
    :param width: Chiều rộng video đầu ra.
    :param height: Chiều cao video đầu ra.
    :param fps: Tốc độ khung hình (mặc định là 24).
    :param crf: Constant Rate Factor (CRF) cho chất lượng video (mặc định là 18, càng thấp thì chất lượng càng cao).
    :param preset: FFmpeg preset (mặc định là "medium").
    :return: Kết quả quá trình xử lý, True nếu thành công, False nếu có lỗi.
    """
    command = [
        "ffmpeg",
        "-i", input_video,
        "-vf", f"minterpolate=fps={fps},scale={width}:{height}",
        "-c:v", "libx264",
        "-preset", preset,
        "-c:a", "copy",
        "-y",  # Ghi đè file đầu ra nếu tồn tại
        output_video
    ]
    
    try:    
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            total_duration = None
            progress_bar = None

            for line in process.stderr:
                if "Duration" in line:
                    duration_str = line.split(",")[0].split("Duration:")[1].strip()
                    h, m, s = map(float, duration_str.split(":"))
                    total_duration = int(h * 3600 + m * 60 + s)
                    progress_bar = tqdm(total=total_duration, desc="Rendering", unit="s")

                if "time=" in line and progress_bar:
                    time_str = line.split("time=")[1].split(" ")[0].strip()
                    h, m, s = map(float, time_str.split(":"))
                    current_time = int(h * 3600 + m * 60 + s)
                    progress_bar.n = current_time
                    progress_bar.refresh()
                    percentage = int((current_time / total_duration) * 100)
                    if percentage <= 100:
                        update_status_video(f"{text}--{percentage}% ",video_id, task_id, worker_id)
            process.wait()
        return True
    except Exception as e:
        print(f"Lỗi khi chạy lệnh FFmpeg: {e}")
        return False

def create_video_reup(data, task_id, worker_id):
    video_id = data.get('video_id')
    name_video = data.get('name_video')
    video_path_audio = f"media/{video_id}/video_adjusted.mp4"

    output_path = f'media/{video_id}/{name_video}.mp4'
    
    # Lấy thông tin video
    video_format = data.get('video_format')
    width, height = get_video_resolution(video_format)

    try:
        update_status_video("Đang Render: Bắt đầu tạo video", video_id, task_id, worker_id)

        # Lấy thông tin video
        duration = get_video_duration(video_path_audio)
        # Chọn các video ngắn ngẫu nhiên cho đến khi đủ độ dài
        selected_videos = []
        current_duration = 0
        update_status_video("Đang Render: Đang lấy video random", video_id, task_id, worker_id)

        video_directory = f'media/{video_id}/video_backrought'
        os.makedirs(video_directory, exist_ok=True)
        while current_duration < duration:
            data_request = {
                'secret_key': SECRET_KEY,
                'action': 'get-video-backrought',
                'task_id': task_id,
                'worker_id': worker_id,
                'list_video': os.listdir(video_directory),
                'duration': 0,
            }
            url = f'{SERVER}/api/'
            response = requests.post(url, json=data_request)
            filename = response.headers.get('Content-Disposition').split('filename=')[1].strip('"')
            video_path = os.path.join(video_directory, filename)
            # Lưu video tải về
            with open(video_path, 'wb') as f:
                f.write(response.content)
            video_duration = get_video_duration(video_path)
            if video_duration > 0:
                selected_videos.append(video_path)
                current_duration += video_duration
                # Tính toán phần trăm tiến trình
                progress_percentage = min((current_duration / duration) * 100, 100)
                # Cập nhật trạng thái với phần trăm hoàn thành
                update_status_video(f"Đang Render: đã chọn {progress_percentage:.2f}% video", video_id, task_id, worker_id)
            else:
                print(f"Bỏ qua video {video_path} vì không thể lấy thời lượng.")

        concat_file_path = f"media/{video_id}/concat_list.txt"
        with open(concat_file_path, 'w') as concat_file:
            for video in selected_videos:
                concat_file.write(f"file '{os.path.abspath(video)}'\n")
        update_status_video(f"Đang Render: Đã tạo xong file nối", data['video_id'], task_id, worker_id)
        final_video_path = f"media/{video_id}/final_video.mp4"

        # Construct the ffmpeg command
        command = [
            "ffmpeg",
            "-f", "concat", 
            "-safe", "0", 
            '-t', str(duration),  # Chuyển duration thành chuỗi
            "-i", f'{concat_file_path}',  # Path to the file containing the list of videos to concatenate
            "-vf", f"scale={width}:{height}",  # Scale video to the specified resolution
            "-c:v", "libx264",  # Use H.264 codec
            "-crf", "23",  # Set CRF to balance quality and file size
            "-preset", "veryfast",  # Set encoding speed
            '-r', '24',  # Set frame rate
            "-c:a", "aac",  # Use AAC audio codec
            "-strict", "experimental",  # Allow experimental audio codec
            final_video_path  # Output file path
        ]

        # Execute the command and capture the output
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:    
            total_duration = None
            progress_bar = None

            # Read the stderr output line by line
            for line in process.stderr:
                print(f"ffmpeg output: {line.strip()}")  # Log the ffmpeg output for debugging
                if "Duration" in line:
                    # Extract the total duration of the video
                    try:
                        duration_str = line.split(",")[0].split("Duration:")[1].strip()
                        h, m, s = map(float, duration_str.split(":"))
                        total_duration = int(h * 3600 + m * 60 + s)
                        progress_bar = tqdm(total=total_duration, desc="Rendering", unit="s")
                    except ValueError as e:
                        print(f"Error parsing duration: {e}")
                        continue

                if "time=" in line and progress_bar:
                    # Extract the current time of the video being processed
                    time_str = line.split("time=")[1].split(" ")[0].strip()
                    if time_str != 'N/A':
                        try:
                            h, m, s = map(float, time_str.split(":"))
                            current_time = int(h * 3600 + m * 60 + s)
                            progress_bar.n = current_time
                            progress_bar.refresh()
                            percentage = int((current_time / total_duration) * 100)
                            if percentage <= 100:
                                update_status_video(f"Đang Render: Đang nối video {percentage}%", data['video_id'], task_id, worker_id)
                        except ValueError as e:
                            print(f"Skipping invalid time format: {time_str}, error: {e}")
            process.wait()
        # Update the status when rendering is complete
        update_status_video("Đang Render: Đã Nối xong video", data['video_id'], task_id, worker_id)
        crop_data_str = data.get('location_video_crop')
        crop_data = parse_crop_data(crop_data_str)
        original_resolution = (640, 360)  # Độ phân giải gốc
        target_resolution = (width, height)  # Độ phân giải mục tiêu
        left, top, width, height = calculate_new_position(crop_data, original_resolution, target_resolution)
        opacity=0.6
        
        # Lệnh FFmpeg để crop, làm mờ, giảm opacity và overlay video
        filter_complex = (
            f"[1:v]crop={width}:{height}:{left}:{top},format=rgba,colorchannelmixer=aa={opacity}[blurred];"
            f"[0:v][blurred]overlay={left}:{top}"
        )
        
        command = [
            "ffmpeg",
            "-i", final_video_path,   # Video nền (background)
            "-i", video_path_audio,  # Video đầu vào cần crop và làm mờ
            "-filter_complex", filter_complex,
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-strict", "experimental",
            output_path
        ]

        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as process:
            total_duration = None
            progress_bar = None

            for line in process.stderr:
                if "Duration" in line:
                    duration_str = line.split(",")[0].split("Duration:")[1].strip()
                    h, m, s = map(float, duration_str.split(":"))
                    total_duration = int(h * 3600 + m * 60 + s)
                    progress_bar = tqdm(total=total_duration, desc="Rendering", unit="s")

                if "time=" in line and progress_bar:
                    time_str = line.split("time=")[1].split(" ")[0].strip()
                    if time_str != 'N/A':
                        h, m, s = map(float, time_str.split(":"))
                        current_time = int(h * 3600 + m * 60 + s)
                        progress_bar.n = current_time
                        progress_bar.refresh()
                        percentage = int((current_time / total_duration) * 100)
                        if percentage <= 100:
                            update_status_video(f"Đang Render: Đang xuất video {percentage}% hoàn thành", data['video_id'], task_id, worker_id)
            process.wait()
        update_status_video("Đang Render: Xuất video xong ! chuẩn bị upload lên sever", data['video_id'], task_id, worker_id)
        return True
    except Exception as e:
        print(f"Lỗi tổng quát khi tạo video: {e}")
        update_status_video(f"Render Lỗi: Lỗi tổng quát khi tạo video", video_id, task_id, worker_id)
        return False
    

def get_video_info(url):
    # Thiết lập các tùy chọn yt_dlp để chỉ tải thông tin metadata
    ydl_opts = {
        'proxy': os.environ.get('PROXY_URL'), # Thêm proxy
        'quiet': True,
        'skip_download': True,
        'force_generic_extractor': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Lấy thông tin video
            info_dict = ydl.extract_info(url, download=False)
            # Truy xuất tiêu đề và thumbnail
            title = info_dict.get('title', 'No title found')
            thumbnail = info_dict.get('thumbnail', 'No thumbnail found')
            return title, thumbnail
    except Exception as e:
        print(f"Error occurred: {e}")
        return None, None

def update_info_video(data, task_id, worker_id):

    video_url  = data.get('url_video_youtube')
    try:
        title,thumbnail_url = get_video_info(video_url)
    except Exception as e:
        print(f"Error getting video info: {e}")
        title = "No title found"
        thumbnail_url = "No thumbnail found"
        update_status_video(f"Render Lỗi: lỗi lấy thông tin videos", video_id, task_id, worker_id)
 
    video_id = data.get('video_id')
    url = f'{SERVER}/api/'
    update_status_video(f"Đang Render : Đang lấy thông tin video", video_id, task_id, worker_id)
    
    payload = {
        'video_id': str(video_id),
        'action': 'update-info-video',
        'secret_key': SECRET_KEY,
        'title': title,
        'thumbnail_url': thumbnail_url,  # Tên trường khác
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        print("Thông tin video đã được cập nhật thành công.")
        return True
    else:
        print(f"Lỗi cập nhật thông tin video: {response.status_code}")
        return False

def update_status_video(status_video,video_id,task_id,worker_id):
    data = {
        'secret_key': SECRET_KEY,
        'action': 'update_status',
        'video_id': video_id,
        'status': status_video,
        'task_id': task_id,
        'worker_id': worker_id,
    }
    url = f'{SERVER}/api/'
    response = requests.post(url, json=data)
    if response.status_code == 200:
        print("Trạng thái video đã được cập nhật thành công.")
    else:
        print(f"Lỗi cập nhật trạng thái video: {response.status_code}")

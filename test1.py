from django.http.request import HttpRequest as HttpRequest
from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
import requests
import uuid

from apps.home.models import Folder, Font_Text, syle_voice, Voice_language, ProfileChannel
from .models import VideoRender, DataTextVideo, video_url,Count_Use_data,APIKeyGoogle,Api_Voice_ttsmaker,App_Update

from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from pytube import YouTube
import json ,re ,random ,string
from datetime import datetime, timedelta
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt


from .forms import VideoForm
from urllib.parse import urlparse, unquote
from django.core.cache import cache
from PIL import Image
from io import BytesIO
from apps.login.models import CustomUser
import calendar
import os
from django.http import FileResponse
from django.conf import settings
import pytz
import time
import urllib.parse
import mimetypes
from django.utils.html import escape
import boto3

from apps.render.task import render_video,render_video_reupload,delete_all_button
from celery.result import AsyncResult
from django import template

from .serializers import RenderSerializer

from apps.home.models import Voice_language, syle_voice,Folder,ProfileChannel

from apps.render.models import VideoRender
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from django.views.decorators.cache import cache_page
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import now
from django.db.models import Q


class index(LoginRequiredMixin, TemplateView):
    login_url = '/login/'
    template_name = 'render/index.html'
    
    def get(self, request):
        content = True
        # Lấy folders dựa theo quyền user
        self.update_channel_keywords()
        if request.user.is_superuser:
            folders = Folder.objects.filter(is_content=content)
        else:
            folders = Folder.objects.filter(use=request.user.id, is_content=content)
            
        # Lấy folder đầu tiên nếu có
        folders_first = folders.first() if folders.exists() else None
        
        # Lấy profiles nếu có folder
        profiles = []
        if folders_first:
            profiles = ProfileChannel.objects.filter(folder_name_id=folders_first.id)
        
        current_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        context = {
            'folders': folders,
            'profiles': profiles, 
            'current_time': current_time,
            'iscontent': content
        }
        return render(request, self.template_name, context)

    def update_channel_keywords(self):
        # Lấy tất cả các video đang chờ render
        videos_to_update = VideoRender.objects.filter(status_video__icontains="Đang Render")

        print(len(videos_to_update))
        # Cập nhật tất cả các video thỏa mãn điều kiện một lần
        videos_to_update.update(status_video="render")
        
    def post(self, request):
        action = request.POST.get('action')
        timezone_news = pytz.timezone('Asia/Bangkok')
        current_time_day = datetime.now(timezone_news)
        time_day = current_time_day.strftime("%H Giờ %M Phút %S Giây")
        channel_layer = get_channel_layer()
    
        if action == 'content':
            # Xử lý view_type từ POST data
            view_type = request.POST.get('view_type')
            content = view_type == 'true'
            videos = []  # Khởi tạo giá trị mặc định

            # Lấy folders dựa theo quyền user
            if request.user.is_superuser:
                folders = Folder.objects.filter(is_content=content)
            else:
                folders = Folder.objects.filter(use=request.user.id, is_content=content)
                
            # Lấy folder đầu tiên nếu có
            folders_first = folders.first() if folders.exists() else None
            
            # Lấy profiles nếu có folder
            profiles = []
            if folders_first:
                profiles = ProfileChannel.objects.filter(folder_name_id=folders_first.id)
                
                # Lấy videos nếu có profiles
                if profiles.exists():
                    if content:
                        videos = VideoRender.objects.filter(profile_id=profiles.first()).order_by('-id')
                    else:
                        videos = VideoRender.objects.filter(profile_id=profiles.first())
                    
            if content:
                sort_order = "asc"
            else:
                sort_order = "desc"
            current_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            context = {
                'folders': folders,
                'profiles': profiles, 
                'current_time': current_time,
                'is_content': content,
                'videos': videos,
                'sort_order':sort_order
            }
            return render(request,"render/base/change_content.html", context)
        
        elif action == 'change-folder':
            folder_id = request.POST.get('folder_id')
            sort_order = request.POST.get('sort_order')
            view_type = request.POST.get('view_type')
            content = view_type == 'true'
            videos = []  # Khởi tạo danh sách videos mặc định
            if folder_id:
                try:
                    if request.user.is_superuser:
                        folders = Folder.objects.filter(is_content=content)
                    else:
                        folders = Folder.objects.filter(use=request.user.id, is_content=content)
                    
                    # Lấy folder object từ folder_id
                    selected_folder = Folder.objects.get(id=folder_id)
                    
                    # Lọc danh sách profiles dựa trên folder
                    profiles = ProfileChannel.objects.filter(folder_name=selected_folder)
                    selected_profile = profiles.first()  # Lấy profile đầu tiên (nếu có)
                    videos=[]

                    if selected_profile:
                        if sort_order == "asc":
                            videos = VideoRender.objects.filter(profile_id=profiles.first()).order_by('-id')
                        else:
                            videos = VideoRender.objects.filter(profile_id=profiles.first())
                    current_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                    # Tạo context trả về cho template
                    context = {
                        'folders': folders,
                        'selected_folder':selected_folder,
                        'profiles': profiles,
                        'selected_profile': selected_profile,
                        'current_time':current_time,
                        "is_content" :content,
                        'videos': videos,
                        'sort_order':sort_order
                    }
                    # Render template combobox_profile.html
                    return render(request, 'render/base/change_content.html', context)

                except Folder.DoesNotExist:
                    # Trả về lỗi nếu không tìm thấy folder
                    return JsonResponse({'error': 'Folder not found'}, status=404)
            else:
                # Trả về lỗi nếu folder_id không được cung cấp
                return JsonResponse({'error': 'Folder ID is required'}, status=400)
        
        elif action == 'change-profile':
            try:
                folder_id = request.POST.get('folder_id')
                profile_id = request.POST.get('profile_id')
                sort_order = request.POST.get('sort_order')
                view_type = request.POST.get('view_type')
                content = view_type == 'true'
                
                if not folder_id :
                    return render(request, 'render/base/list_video_reup.html',{"video":None})
                
                if request.user.is_superuser:
                    folders = Folder.objects.filter(is_content=content)
                else:
                    folders = Folder.objects.filter(use=request.user.id, is_content=content)

                selected_folder = Folder.objects.get(id=folder_id)
                profiles = ProfileChannel.objects.filter(folder_name=selected_folder)
                selected_profile = ProfileChannel.objects.get(id=profile_id)

                videos = []
                if profile_id:
                    if sort_order == "asc":
                        videos = VideoRender.objects.filter(profile_id=selected_profile).order_by('-id')
                    else:
                        videos = VideoRender.objects.filter(profile_id=selected_profile)
                current_time = (timezone.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                context = {
                    'folders': folders,
                    'selected_folder': selected_folder,
                    'profiles': profiles,
                    'selected_profile': selected_profile,
                    "is_content" : content,
                    'current_time':current_time,
                    'videos': videos,
                    'sort_order':sort_order
                }
                return render(request, 'render/base/change_content.html', context)

            except (Folder.DoesNotExist, ProfileChannel.DoesNotExist):
                return JsonResponse({'error': 'Item not found'}, status=404)
            except Exception as e:
                
                print(e)
                return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
 
        elif action == 'btn-update-time-reup':
            # Lấy dữ liệu từ request
            list_time_upload = request.POST.get('list_time_upload')  # Chuỗi giờ
            date_upload = request.POST.get('date_upload')  # Ngày bắt đầu
            profile_id = request.POST.get('profile_id')  # ID profile
            
            # Chuyển chuỗi giờ thành danh sách
            time_list = [datetime.strptime(h.strip(), "%H:%M").time() for h in list_time_upload.split(",")]
            current_date = datetime.strptime(date_upload.strip(), "%Y-%m-%d").date()
            # Lấy danh sách video theo profile_id
            videos = list(VideoRender.objects.filter(profile_id=profile_id).exclude(status_video="Upload VPS Thành Công"))

            profile = ProfileChannel.objects.get(id=profile_id)
            folder = profile.folder_name
            user = folder.use
            user_id = user.id

            list_update =[]
            # Gán thời gian upload cho từng video
            for i, video in enumerate(videos):
                time_index = i % len(time_list)  # Lấy thời gian trong ngày
                video_time = time_list[time_index]

                # Nếu là giờ đầu tiên của ngày mới, tăng ngày lên
                if time_index == 0 and i != 0:
                    current_date += timedelta(days=1)

                # Chỉ lưu giờ và phút
                video.time_upload = video_time.strftime("%H:%M")
                video.date_upload =  current_date.strftime("%Y-%m-%d")

                title = video.url_video_youtube if video.url_reupload else video.title
                html_button_render = render_to_string('render/base/button-render.html', {'item': video})
                html_status_videos = render_to_string('render/base/status-videos.html', {'item': video})
                time = f"Ngày Upload {video.date_upload }Giờ Upload {video.time_upload }"
                url = video.url_thumbnail if video.url_thumbnail else "/static/assets/img/no-image-available.png"
                data = {
                    "id_videos":video.id,
                    "title":title,
                    "time":time,
                    "url":url,
                    "html_button_render":html_button_render,
                    "html_status_videos":html_status_videos,
                }
                list_update.append(data)
            
            # Cập nhật tất cả các bản ghi trong 1 query
            VideoRender.objects.bulk_update(videos, ['time_upload', 'date_upload'])
            
            async_to_sync(channel_layer.group_send)(
                "admin",
                {
                    'type': 'update_count_admin',
                    'message': 'update_status',
                    'data':list_update,
                }
            )

            async_to_sync(channel_layer.group_send)(
                str(user_id),
                {
                    'type': 'update_count_user',
                    'message': 'update_status',
                    'user': user_id,
                    'data':list_update,
                }
            )
            return JsonResponse({'status': 'success', 'message': 'Cập Nhập Thời Gian thành công'})
        
        elif action == 'btn-add-videos-reup':
            # Lấy dữ liệu từ request POST
            list_time_upload = request.POST.get('list_time_upload', '').strip()
            date_upload = request.POST.get('date_upload', '').strip()
            profile_id = request.POST.get('profile_id', '').strip()
            list_url = request.POST.get('list_url', '').strip()
            # Kiểm tra dữ liệu đầu vào
            if not profile_id:
                return JsonResponse({'status': 'error', 'message': 'Không có profile nào được chọn, vui lòng thêm profile!'})

            if not list_time_upload or not date_upload or not list_url:
                return JsonResponse({'status': 'error', 'message': 'Vui lòng nhập đầy đủ danh sách URL, thời gian, và ngày upload.'})

            # Kiểm tra profile có tồn tại không
            try:
                profile = ProfileChannel.objects.get(id=profile_id)
            except ObjectDoesNotExist:
                return JsonResponse({'status': 'error', 'message': f'Profile với ID {profile_id} không tồn tại.'})

            # Xử lý danh sách URL và loại bỏ trùng lặp
            url_list = list(dict.fromkeys(line.strip() for line in list_url.splitlines() if line.strip()))
            if not url_list:
                return JsonResponse({'status': 'error', 'message': 'Danh sách URL không hợp lệ hoặc trống.'})

            # Xử lý danh sách thời gian upload
            try:
                time_list = [datetime.strptime(h.strip(), "%H:%M").time() for h in list_time_upload.split(",")]
                current_date = datetime.strptime(date_upload, "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Định dạng thời gian hoặc ngày không hợp lệ.'})

            # Thiết lập giá trị mặc định cho video mới
            default_values = {
                "video_format": profile.video_format,
                "folder_id": profile.folder_name,
                "profile_id": profile,
                "description": profile.channel_description,
                "keywords": profile.channel_keywords,
                "status_video": "render",
                "intro_active": profile.channel_intro_active,
                "intro_url": profile.channel_intro_url,
                "outro_active": profile.channel_outro_active,
                "outro_url": profile.channel_outro_url,
                "logo_active": profile.channel_logo_active,
                "logo_url": profile.channel_logo_url,
                "logo_position": profile.channel_logo_position,
                "font_text": profile.channel_font_text,
                "font_size": profile.channel_font_size,
                "font_bold": profile.channel_font_bold,
                "font_italic": profile.channel_font_italic,
                "font_underline": profile.channel_font_underline,
                "font_strikeout": profile.channel_font_strikeout,
                "font_color": profile.channel_font_color,
                "font_color_opacity": profile.channel_font_color_opacity,
                "font_color_troke": profile.channel_font_color_troke,
                "font_color_troke_opacity": profile.channel_font_color_troke_opacity,
                "stroke_text": profile.channel_stroke_text,
                "font_background": profile.channel_font_background,
                "channel_font_background_opacity": profile.channel_font_background_opacity,
                "channel_voice_style": getattr(profile, 'channel_voice_style', None),  # Lấy giá trị hoặc None
                "location_video_crop": profile.location_video_crop,
                "speed_video_crop": profile.speed_video_crop,
                "pitch_video_crop": profile.pitch_video_crop,
                "channel_music_active": profile.channel_music_active,
            }
            new_videos = []
            list_name = []
            for i, url in enumerate(url_list):
                time_index = i % len(time_list)
                video_time = time_list[time_index]
                if time_index == 0 and i != 0:
                    current_date += timedelta(days=1)
                name_video = uuid.uuid4().hex[:7]
                new_video = VideoRender(
                    url_video_youtube=url,
                    name_video= name_video,  # Tạo tên video ngẫu nhiên an toàn hơn
                    url_reupload=True,
                    time_upload=video_time.strftime("%H:%M"),
                    date_upload=current_date.strftime("%Y-%m-%d"),
                    **default_values
                )
                new_videos.append(new_video)
                list_name.append(name_video)

            # Lưu video mới vào database bằng `bulk_create`
            new_videos = VideoRender.objects.bulk_create(new_videos)
            # Truy vấn lại ID của các bản ghi vừa tạo
            new_videos = VideoRender.objects.filter(
                profile_id=profile
            ).order_by("-id")
            
            folder = profile.folder_name
            user = folder.use
            user_id = user.id
            html = render_to_string('render/base/list_video_reup.html', {'videos': new_videos})
            data = {
                "videos_html":html,
                "profile_id" : profile_id,
            }

            async_to_sync(channel_layer.group_send)(
                "admin",
                {
                    'type': 'update_count_admin',
                    'message': 'add_videos_reup',
                    'data':data, # Gửi toàn bộ danh sách video cùng lúc
                }
            )

            async_to_sync(channel_layer.group_send)(
                str(user_id),
                {
                    'type': 'update_count_user',
                    'message': 'add_videos_reup',
                    'user': user_id,
                    'data':data,
                }
            )
            return JsonResponse({'status': 'success', 'message': 'Thêm video thành công!'})
        
        elif action == 'btn_render_all':
            profile_id = request.POST.get('id_profile')  # ID profile
            count_video = request.POST.get('count_video')
            videos  = VideoRender.objects.filter(
                profile_id=profile_id,
                status_video="render"
            )[:int(count_video)]
            list_video_render = []

            profile = ProfileChannel.objects.get(id=profile_id)
            folder = profile.folder_name
            user = folder.use
            user_id = user.id

            for video in videos:
                data = self.get_infor_render(video)
                if data is not None:  # Kiểm tra data không phải None
                    if video.folder_id.is_content:
                        task = render_video.apply_async(args=[data])
                    else:
                        task = render_video_reupload.apply_async(args=[data])
                    video.task_id = task.id
                    video.status_video = "Đang chờ render : Đợi đến lượt render"
                    html = render_to_string('render/base/status-videos.html', {"item": video})
                else :
                    video.status_video = "Render Lỗi : Cài đặt profile chưa đúng xoá video và cài đặt lại !"
                    html = render_to_string('render/base/status-videos.html', {"item": video})

                title = video.url_video_youtube if video.url_reupload else video.title
                html_button_render = render_to_string('render/base/button-render.html', {'item': video})
                html_status_videos = render_to_string('render/base/status-videos.html', {'item': video})
                time = f"Ngày Upload {video.date_upload }Giờ Upload {video.time_upload }"
                url = video.url_thumbnail if video.url_thumbnail else "/static/assets/img/no-image-available.png"
                video_data = {
                    "id_videos":video.id,
                    "title":title,
                    "time":time,
                    "url":url,
                    "html_button_render":html_button_render,
                    "html_status_videos":html_status_videos,
                }
                list_video_render.append(video_data)
            VideoRender.objects.bulk_update(videos, ['status_video'])

            async_to_sync(channel_layer.group_send)(
                "admin",
                {
                    'type': 'update_count_admin',
                    'message': 'update_status',
                    'data': list_video_render  # Gửi toàn bộ danh sách video cùng lúc
                }
            )

            async_to_sync(channel_layer.group_send)(
                str(user_id),
                {
                    'type': 'update_count_user',
                    'message': 'update_status',
                    'data': list_video_render,
                    'user': user_id
                }
            )
            return JsonResponse({'status': 'success', 'message': f'Render thành công {len(videos)} videos'})
        # Trong view xử lý việc thêm video và cập nhật thông tin
        elif action == 'btn_render_erron':
            profile_id = request.POST.get('id_profile')  # ID profile
            count_video = request.POST.get('count_video')
            videos = VideoRender.objects.filter(
                Q(profile_id=profile_id) & Q(status_video__contains="Render Lỗi")
            ) 
            list_video_render = []

            profile = ProfileChannel.objects.get(id=profile_id)
            folder = profile.folder_name
            user = folder.use
            user_id = user.id

            for video in videos:
                data = self.get_infor_render(video)
                if data is not None:  # Kiểm tra data không phải None
                    if video.folder_id.is_content:
                        task = render_video.apply_async(args=[data])
                    else:
                        task = render_video_reupload.apply_async(args=[data])
                    video.task_id = task.id
                    video.status_video = "Đang chờ render : Render Lại"
                else :
                    video.status_video = "Render Lỗi : Cài đặt profile chưa đúng xoá video và cài đặt lại !"
                    
                title = video.url_video_youtube if video.url_reupload else video.title
                html_button_render = render_to_string('render/base/button-render.html', {'item': video})
                html_status_videos = render_to_string('render/base/status-videos.html', {'item': video})
                time = f"Ngày Upload {video.date_upload }Giờ Upload {video.time_upload }"
                url = video.url_thumbnail if video.url_thumbnail else "/static/assets/img/no-image-available.png"
                video_data = {
                    "id_videos":video.id,
                    "title":title,
                    "time":time,
                    "url":url,
                    "html_button_render":html_button_render,
                    "html_status_videos":html_status_videos,
                }
                list_video_render.append(video_data)
            VideoRender.objects.bulk_update(videos, ['status_video'])
            async_to_sync(channel_layer.group_send)(
                "admin",
                {
                    'type': 'update_count_admin',
                    'message': 'update_status',
                    'data': list_video_render  # Gửi toàn bộ danh sách video cùng lúc
                }
            )

            async_to_sync(channel_layer.group_send)(
                str(user_id),
                {
                    'type': 'update_count_user',
                    'message': 'update_status',
                    'user': user_id,
                    'data': list_video_render
                }
            )
            return JsonResponse({'status': 'success', 'message': f'render lại thành công {len(videos)} videos'})
        
        elif action == 'btn_upload_erron':
            profile_id = request.POST.get('id_profile')  # ID profile
            count_video = request.POST.get('count_video')
            videos = VideoRender.objects.filter(
                Q(profile_id=profile_id) & Q(status_video__contains="Upload VPS Thất Bại")
            ) 
            list_video_render = []

            profile = ProfileChannel.objects.get(id=profile_id)
            folder = profile.folder_name
            user = folder.use
            user_id = user.id

            for video in videos:
                video.status_video = "Render Thành Công : Đang Chờ Upload lên Kênh"
                title = video.url_video_youtube if video.url_reupload else video.title
                html_button_render = render_to_string('render/base/button-render.html', {'item': video})
                html_status_videos = render_to_string('render/base/status-videos.html', {'item': video})
                time = f"Ngày Upload {video.date_upload }Giờ Upload {video.time_upload }"
                url = video.url_thumbnail if video.url_thumbnail else "/static/assets/img/no-image-available.png"
                video_data = {
                    "id_videos":video.id,
                    "title":title,
                    "time":time,
                    "url":url,
                    "html_button_render":html_button_render,
                    "html_status_videos":html_status_videos,
                }
                list_video_render.append(video_data)

            VideoRender.objects.bulk_update(videos, ['status_video'])

            async_to_sync(channel_layer.group_send)(
                "admin",
                {
                    'type': 'update_count_admin',
                    'message': 'update_status',
                    'data': list_video_render  # Gửi toàn bộ danh sách video cùng lúc
                }
            )

            async_to_sync(channel_layer.group_send)(
                str(user_id),
                {
                    'type': 'update_count_admin',
                    'message': 'update_status',
                    'data': list_video_render
                }
            )

            return JsonResponse({'status': 'success', 'message': f'đã chỉnh sửa lại {len(videos)} videos upload lỗi'})

        elif action == 'btn_delete_video_success':
            profile_id = request.POST.get('id_profile')  # ID profile
            videos  = VideoRender.objects.filter(
                profile_id=profile_id,
                status_video="Upload VPS Thành Công"
            )
            
            for iteam in videos:
                if iteam.task_id:
                    try:
                        result = AsyncResult(iteam.task_id)
                        result.revoke(terminate=True)
                    except Exception as e:
                        print(f"❌ Không thể hủy task {iteam.task_id}: {e}")
            profile = ProfileChannel.objects.get(id=profile_id)
            folder = profile.folder_name
            user = folder.use
            user_id = user.id

            video_ids = list(videos.values_list('id', flat=True))
            delete_all_button.apply_async(args=[video_ids])
            deleted_count, _ = videos.delete()

            data = {
                'video_ids': video_ids,
            }
            async_to_sync(channel_layer.group_send)(
                    "admin",  # Tên nhóm
                    {
                        'type': 'update_count_admin',  # Loại sự kiện
                        'message': 'delete_videos',  # Thông báo
                        'data': data,  # Dữ liệu kèm theo
                    }
                ) 
            async_to_sync(channel_layer.group_send)(
                str(user_id),  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'delete_videos',  # Thông báo
                    'user': user_id,
                    'data':data,
                }
            ) 
            return JsonResponse({'status': 'success', 'message': f'Đã xóa {deleted_count} video thành công'})

        elif action == 'btn_delete_video_checkbox':
            profile_id = request.POST.get('id_profile')
            ids = request.POST.get('ids', '').split(',')
            # Truy vấn video theo các ID đã lấy
            videos = VideoRender.objects.filter(id__in=ids)
            
            for iteam in videos:
                if iteam.task_id:
                    try:
                        result = AsyncResult(iteam.task_id)
                        result.revoke(terminate=True)
                    except Exception as e:
                        print(f"❌ Không thể hủy task {iteam.task_id}: {e}")

            profile = ProfileChannel.objects.get(id=profile_id)
            folder = profile.folder_name
            user = folder.use
            user_id = user.id

            video_ids = list(videos.values_list('id', flat=True))
            delete_all_button.apply_async(args=[video_ids])
            videos.delete()
            data = {
                'video_ids': video_ids,
            }
            async_to_sync(channel_layer.group_send)(
                    "admin",  # Tên nhóm
                    {
                        'type': 'update_count_admin',  # Loại sự kiện
                        'message': 'delete_videos',  # Thông báo
                        'data': data,  # Dữ liệu kèm theo
                    }
                ) 
            async_to_sync(channel_layer.group_send)(
                str(user_id),  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'delete_videos',  # Thông báo
                    'user': user_id,
                    'data':data,
                }
            ) 
            return JsonResponse({'status': 'success', 'message': f'Đã xóa {len(video_ids)} video thành công'})

        elif action == 'add-content-video-and-update':
            id_video = request.POST.get('id_video')
            title = request.POST.get('title')
            profile_id = request.POST.get('profile_id')
            description = request.POST.get('description')
            keywords = request.POST.get('keywords')
            date_upload = request.POST.get('date_upload')
            time_upload = request.POST.get('time_upload')
            text_content = request.POST.get('text_content')
            text_content_2 = request.POST.get('text_content_2')
            video_image = request.POST.get('video_image')
            # Tách video_image thành danh sách URL
            list_url = json.loads(video_image)
            data_json = json.loads(text_content_2)
            list_files = json.loads(request.POST.get('list_files', '{}'))

            if id_video == 'none':
                profile = ProfileChannel.objects.get(id=profile_id)
                # Tạo thông tin mặc định
                default_values = {
                    "video_format": profile.video_format,
                    "folder_id": profile.folder_name,
                    'name_video': ''.join(random.choices(string.ascii_letters + string.digits, k=7)),
                    "profile_id": profile,
                    "description": description or profile.channel_description,
                    "keywords": keywords or profile.channel_keywords,
                    "status_video": "render",
                    "intro_active": profile.channel_intro_active,
                    "intro_url": profile.channel_intro_url,
                    "outro_active": profile.channel_outro_active,
                    "outro_url": profile.channel_outro_url,
                    "logo_active": profile.channel_logo_active,
                    "logo_url": profile.channel_logo_url,
                    "logo_position": profile.channel_logo_position,
                    "font_text": profile.channel_font_text,
                    "font_size": profile.channel_font_size,
                    "font_bold": profile.channel_font_bold,
                    "font_italic": profile.channel_font_italic,
                    "font_underline": profile.channel_font_underline,
                    "font_strikeout": profile.channel_font_strikeout,
                    "font_color": profile.channel_font_color,
                    "font_color_opacity": profile.channel_font_color_opacity,
                    "font_color_troke": profile.channel_font_color_troke,
                    "font_color_troke_opacity": profile.channel_font_color_troke_opacity,
                    "stroke_text": profile.channel_stroke_text,
                    "font_background": profile.channel_font_background,
                    "channel_font_background_opacity": profile.channel_font_background_opacity,
                    "channel_voice_style": getattr(profile, 'channel_voice_style', None),
                    "location_video_crop": profile.location_video_crop,
                    "speed_video_crop": profile.speed_video_crop,
                    "pitch_video_crop": profile.pitch_video_crop,
                    "channel_music_active": profile.channel_music_active,
                    "title": title,
                    "description": description,
                    "keywords": keywords,
                    "time_upload": time_upload,
                    "date_upload": date_upload,
                    "text_content": text_content,
                    "text_content_2": text_content_2,
                    "url_reupload": False,
                }

                # Tạo đối tượng video
                video = VideoRender.objects.create(**default_values)

                # Lấy folders dựa theo quyền user
                if not request.user.is_superuser:
                    Count_Use_data.objects.create(videoRender_id=video, use=request.user, edit_title=True, title=title)
                    Count_Use_data.objects.create(videoRender_id=video, use=request.user, creade_video=True)

                # Lưu thumbnail nếu có trong request
                if 'thumnail' in request.FILES:
                    thumnail = request.FILES['thumnail']
                    filename = thumnail.name.strip().replace(" ", "_")

                    # Tạo thư mục lưu trữ nếu chưa có
                    upload_dir = f"data/{video.id}/thumnail/"
                    os.makedirs(os.path.join(default_storage.location, upload_dir), exist_ok=True)

                    file_name = default_storage.save(f"{upload_dir}{filename}", thumnail)
                    file_url = default_storage.url(file_name)

                    # Lưu URL của thumbnail vào video
                    video.url_thumbnail = file_url
                    video.save()
                    if not request.user.is_superuser:
                        Count_Use_data.objects.create(videoRender_id=video, use=request.user, edit_thumnail=True, url_thumnail=file_url)


                # Lưu file từ "files" trong request
                if 'files' in request.FILES:
                    for index, file in enumerate(request.FILES.getlist('files')):
                        filename = file.name.strip().replace(" ", "_")
                        upload_dir = f"data/{video.id}/image/"
                        os.makedirs(os.path.join(default_storage.location, upload_dir), exist_ok=True)

                        file_image = default_storage.save(f"{upload_dir}{filename}", file)
                        file_url = default_storage.url(file_image)

                        # Cập nhật URL trong list_files
                        list_files[str(index)]["url"] = file_url

                # Cập nhật URL trong data_json và list_url
                for item in data_json:
                    for file_key, file_data in list_files.items():
                        if item["url_video"] == file_data.get("blobUrl"):
                            item["url_video"] = file_data["url"]

                for i, url in enumerate(list_url):
                    for file_key, file_data in list_files.items():
                        if url == file_data.get("blobUrl"):
                            list_url[i] = file_data["url"]
                            
                # Cập nhật thông tin video
                video.text_content_2 = json.dumps(data_json)
                video.video_image = json.dumps(list_url)
                video.save()
                
                # Tạo HTML mới cho video, truyền cả thông tin trạng thái đã xử lý
                html = render_to_string(
                    'render/base/iteam-video.html',
                    {'item': video}
                )
                folder = video.folder_id  # Nếu đã là object, không cần truy vấn DB nữa
                user = folder.use  # Không cần truy vấn CustomUser nữa
                user_id = user.id  
                data = {
                    'video_id': video.id, # Dữ liệu kèm theo
                    'profile_id': profile.id,
                    'video_iteam': html,  # Dữ liệu kèm theo
                }



                async_to_sync(channel_layer.group_send)(
                    "admin",  # Tên nhóm
                    {
                        'type': 'update_count_admin',  # Loại sự kiện
                        'message': 'add_videos',  # Thông báo
                        'data': data,  # Dữ liệu kèm theo
                    }
                ) 
                async_to_sync(channel_layer.group_send)(
                    str(user_id),  # Tên nhóm
                    {
                        'type': 'update_count_admin',  # Loại sự kiện
                        'message': 'add_videos',  # Thông báo
                        'user': user_id,
                        'data':data,
                    }
                ) 
                # Trả về JSON với phần HTML mới
                return JsonResponse({'status': 'success'})

        elif action == "video-update":
            id_video = request.POST.get('id_video')
            title = request.POST.get('title')
            profile_id = request.POST.get('profile_id')
            description = request.POST.get('description')
            keywords = request.POST.get('keywords')
            date_upload = request.POST.get('date_upload')
            time_upload = request.POST.get('time_upload')
            text_content = request.POST.get('text_content')
            text_content_2 = request.POST.get('text_content_2')
            video_image = request.POST.get('video_image')
            
            video = VideoRender.objects.get(id=id_video)
            
            list_url = json.loads(video_image)
            data_json = json.loads(text_content_2)
            list_files = json.loads(request.POST.get('list_files', '{}'))
            
            # Lưu thumbnail nếu có trong request
            if 'thumnail' in request.FILES:
                thumnail = request.FILES['thumnail']
                filename = thumnail.name.strip().replace(" ", "_")

                # Tạo thư mục lưu trữ nếu chưa có
                upload_dir = f"data/{video.id}/thumnail/"
                os.makedirs(os.path.join(default_storage.location, upload_dir), exist_ok=True)

                file_name = default_storage.save(f"{upload_dir}{filename}", thumnail)
                file_url = default_storage.url(file_name)

                # Lưu URL của thumbnail vào video
                video.url_thumbnail = file_url

            # Lưu file từ "files" trong request
            if 'files' in request.FILES:
                for index, file in enumerate(request.FILES.getlist('files')):
                    filename = file.name.strip().replace(" ", "_")
                    upload_dir = f"data/{video.id}/image/"
                    os.makedirs(os.path.join(default_storage.location, upload_dir), exist_ok=True)

                    file_image = default_storage.save(f"{upload_dir}{filename}", file)
                    file_url = default_storage.url(file_image)

                    # Cập nhật URL trong list_files
                    list_files[str(index)]["url"] = file_url
            # Cập nhật URL trong data_json và list_url
            for item in data_json:
                for file_key, file_data in list_files.items():
                    if item["url_video"] == file_data.get("blobUrl"):
                        item["url_video"] = file_data["url"]

            for i, url in enumerate(list_url):
                for file_key, file_data in list_files.items():
                    if url == file_data.get("blobUrl"):
                        list_url[i] = file_data["url"]
                        
            # Cập nhật thông tin video

            video.title = title
            video.description = description
            video.keywords = keywords
            video.date_upload = date_upload
            video.time_upload = time_upload
            video.text_content = text_content

            video.text_content_2 = json.dumps(data_json)
            video.video_image = json.dumps(list_url)
            video.save()


            if not video.url_reupload:
                # Kiểm tra nếu video chưa được upload lại (url_reupload = False)
                
                # Kiểm tra nếu có bản ghi `Count_Use_data` cho việc chỉnh sửa tiêu đề
                is_edit_title = Count_Use_data.objects.filter(
                    videoRender_id=video, creade_video=False, edit_title=True, edit_thumnail=False
                ).first()
                
                if is_edit_title:
                    # Nếu có bản ghi, cập nhật tiêu đề
                    is_edit_title.title = video.title
                    is_edit_title.save()  # Lưu lại thay đổi
                else:
                    # Nếu không có bản ghi, tạo mới nếu user không phải superuser
                    if not request.user.is_superuser:
                        Count_Use_data.objects.create(
                            videoRender_id=video, 
                            use=request.user, 
                            edit_title=True, 
                            title=video.title
                        )

                # Kiểm tra nếu có bản ghi `Count_Use_data` cho việc chỉnh sửa thumbnail
                is_edit_thumnail = Count_Use_data.objects.filter(
                    videoRender_id=video, creade_video=False, edit_title=False, edit_thumnail=True
                ).first()
                
                if is_edit_thumnail:
                    # Nếu có bản ghi và có `url_thumbnail`, cập nhật lại thumbnail
                    is_edit_thumnail.url_thumbnail = video.url_thumbnail
                    is_edit_thumnail.save()  # Lưu lại thay đổi
                else:
                    # Nếu không có bản ghi, tạo mới nếu user không phải superuser
                    if not request.user.is_superuser and video.url_thumbnail:
                        Count_Use_data.objects.create(
                            videoRender_id=video, 
                            use=request.user, 
                            edit_thumnail=True, 
                            url_thumnail=video.url_thumbnail
                        )
            # Tạo HTML mới cho video, truyền cả thông tin trạng thái đã xử lý
        
            title = video.url_video_youtube if video.url_reupload else video.title
            html_button_render = render_to_string('render/base/button-render.html', {'item': video})
            html_status_videos = render_to_string('render/base/status-videos.html', {'item': video})
            time = f"Ngày Upload {video.date_upload }Giờ Upload {video.time_upload }"
            url = video.url_thumbnail if video.url_thumbnail else "/static/assets/img/no-image-available.png"
            data = [{
                "id_videos":video.id,
                "thumnail_video":url,
                "title":title,
                "html_button_render":html_button_render,
                "html_status_videos":html_status_videos,
                "time_upload":time,
            }]

            channel_layer = get_channel_layer()
            profile = video.profile_id
            folder = video.folder_id  # Nếu đã là object, không cần truy vấn DB nữa
            user = folder.use  # Không cần truy vấn CustomUser nữa
            user_id = user.id  



            async_to_sync(channel_layer.group_send)(
                "admin",  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'update_status',  # Thông báo
                    'data': data,  # Dữ liệu kèm theo
                }
            ) 
            async_to_sync(channel_layer.group_send)(
                str(user_id),  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'update_status',  # Thông báo
                    'user': user_id,
                    'data':data,
                }
            ) 
            # Trả về JSON với phần HTML mới
            return JsonResponse({'status': 'success'})
        
        elif action == 'btn_render_one_video':
            id_video = request.POST.get('id_video')
            video = VideoRender.objects.get(id=id_video)
            data = self.get_infor_render(video)
            if data is not None:  # Kiểm tra data không phải None
                if video.status_video == "render":
                    try:
                        if video.folder_id.is_content:
                            task = render_video.apply_async(args=[data])
                        else:
                            task = render_video_reupload.apply_async(args=[data])
                        video.task_id = task.id
                        video.status_video = "Đang chờ render : Đợi đến lượt render"
                       

                    except Exception as e:
                        video.status_video = "Render Lỗi : Dừng Render"
                       
                elif "Đang chờ render" in video.status_video or "Đang Render" in video.status_video:
                    try:
                        result = AsyncResult(video.task_id)
                        result.revoke(terminate=True)
                        video.task_id = ''
                        video.status_video = "Render Lỗi : Dừng Render"
                    
                    except Exception as e:
                        video.status_video = "Render Lỗi : Dừng Render"
                        
                elif "Render Lỗi" in video.status_video:
                    try:
                        if video.folder_id.is_content:
                            task = render_video.apply_async(args=[data])
                        else:
                            task = render_video_reupload.apply_async(args=[data])
                        video.task_id = task.id
                        video.status_video = "Đang chờ render : Render Lại"

                    except Exception as e:
                        video.status_video = "Render Lỗi : Dừng Render"
                    
                elif "Render Thành Công" in video.status_video or "Đang Upload Lên VPS" in video.status_video or "Upload VPS Thành Công" in video.status_video or "Upload VPS Thất Bại" in video.status_video:
                    try:
                        if video.folder_id.is_content:
                            task = render_video.apply_async(args=[data])
                        else:
                            task = render_video_reupload.apply_async(args=[data])
                        video.task_id = task.id
                        video.status_video = "Đang chờ render : Render Lại"
                        folder_path = f"data/{video.id}"
                        file = self.get_filename_from_url(video.url_video)
                        default_storage.delete(f"{folder_path}/{file}")
                        video.url_video = ''
                    except Exception as e:
                        video.status_video = "Render Lỗi : Dừng Render"

            else :
                video.status_video = "Render Lỗi : Cài đặt profile chưa đúng xoá video và cài đặt lại !"
            video.save()
            title = video.url_video_youtube if video.url_reupload else video.title
            html_button_render = render_to_string('render/base/button-render.html', {'item': video})
            html_status_videos = render_to_string('render/base/status-videos.html', {'item': video})
            time = f"Ngày Upload {video.date_upload }Giờ Upload {video.time_upload }"
            url = video.url_thumbnail if video.url_thumbnail else "/static/assets/img/no-image-available.png"
            data = [{
                "id_videos":video.id,
                "thumnail_video":url,
                "title":title,
                "html_button_render":html_button_render,
                "html_status_videos":html_status_videos,
                "time_upload":time,
            }]

            channel_layer = get_channel_layer()
            profile = video.profile_id
            folder = video.folder_id  # Nếu đã là object, không cần truy vấn DB nữa
            user = folder.use  # Không cần truy vấn CustomUser nữa
            user_id = user.id  

            async_to_sync(channel_layer.group_send)(
                "admin",  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'update_status',  # Thông báo
                    'data': data,  # Dữ liệu kèm theo
                }
            ) 
            async_to_sync(channel_layer.group_send)(
                str(user_id),  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'update_status',  # Thông báo
                    'user': user_id,
                    'data':data,
                }
            ) 
            # Trả về JSON với phần HTML mới
            return JsonResponse({'status': 'success'})

        elif action == 'btn_re_upload_one_video':
            id_video = request.POST.get('id_video')
            video = VideoRender.objects.get(id=id_video)
            if video.url_video and video.status_video != "Upload VPS Thành Công":
                video.status_video = "Render Thành Công : Đang Chờ Upload lên Kênh"
                video.save()
            elif not video.url_video and video.status_video != "Upload VPS Thành Công":
                video.status_video = "render"
                video.save()
            title = video.url_video_youtube if video.url_reupload else video.title
            html_button_render = render_to_string('render/base/button-render.html', {'item': video})
            html_status_videos = render_to_string('render/base/status-videos.html', {'item': video})
            time = f"Ngày Upload {video.date_upload }Giờ Upload {video.time_upload }"
            url = video.url_thumbnail if video.url_thumbnail else "/static/assets/img/no-image-available.png"
            data = [{
                "id_videos":video.id,
                "thumnail_video":url,
                "title":title,
                "html_button_render":html_button_render,
                "html_status_videos":html_status_videos,
                "time_upload":time,
            }]
            channel_layer = get_channel_layer()
            profile = video.profile_id
            folder = video.folder_id  # Nếu đã là object, không cần truy vấn DB nữa
            user = folder.use  # Không cần truy vấn CustomUser nữa
            user_id = user.id
            async_to_sync(channel_layer.group_send)(
                "admin",  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'update_status',  # Thông báo
                    'data': data,  # Dữ liệu kèm theo
                }
            )
            async_to_sync(channel_layer.group_send)(
                str(user_id),  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'update_status',  # Thông báo
                    'user': user_id,
                    'data':data,
                }
            )
            
        elif action == 'btn_coppy':
            id_video = request.POST.get('id_video')
            profile_id = request.POST.get('id_profile')

            old_video = VideoRender.objects.get(pk=id_video)
            # Lấy thông tin profile mới
            profile_new = ProfileChannel.objects.get(pk=profile_id)

            # Tạo video mới với dữ liệu từ video cũ + profile mới
            new_video = VideoRender.objects.create(
                video_format=old_video.video_format,
                folder_id=old_video.folder_id,
                profile_id=profile_new,
                name_video=''.join(random.choices(string.ascii_letters + string.digits, k=7)),
                text_content=old_video.text_content,
                text_content_2=old_video.text_content_2,
                video_image=old_video.video_image,
                status_video="render",  # ✅ Sửa lỗi syntax
                intro_active=profile_new.channel_intro_active,
                intro_url=profile_new.channel_intro_url,
                outro_active=profile_new.channel_outro_active,
                outro_url=profile_new.channel_outro_url,
                logo_active=profile_new.channel_logo_active,
                logo_url=profile_new.channel_logo_url,
                logo_position=profile_new.channel_logo_position,
                font_text=profile_new.channel_font_text,
                font_size=profile_new.channel_font_size,
                font_bold=profile_new.channel_font_bold,
                font_italic=profile_new.channel_font_italic,
                font_underline=profile_new.channel_font_underline,
                font_strikeout=profile_new.channel_font_strikeout,
                font_color=profile_new.channel_font_color,
                font_color_opacity=profile_new.channel_font_color_opacity,
                font_color_troke=profile_new.channel_font_color_troke,
                font_color_troke_opacity=profile_new.channel_font_color_troke_opacity,
                stroke_text=profile_new.channel_stroke_text,
                font_background=profile_new.channel_font_background,
                channel_font_background_opacity=profile_new.channel_font_background_opacity,
                channel_voice_style=getattr(profile_new, 'channel_voice_style', None),  # ✅ Lấy giá trị hoặc None
                location_video_crop=profile_new.location_video_crop,
                speed_video_crop=profile_new.speed_video_crop,
                pitch_video_crop=profile_new.pitch_video_crop,
                channel_music_active=profile_new.channel_music_active,
                title = old_video.title,
                description = old_video.description,
                keywords = old_video.keywords,
                time_upload = old_video.time_upload,
                date_upload = old_video.date_upload,
            )

            title = new_video.url_reupload if new_video.url_reupload else new_video.title
            html_button_render = render_to_string('render/base/button-render.html', {'item': new_video})
            html_status_videos = render_to_string('render/base/status-videos.html', {'item': new_video})
            time = f"Ngày Upload {new_video.date_upload }Giờ Upload {new_video.time_upload }"
            url = new_video.url_thumbnail if new_video.url_thumbnail else "/static/assets/img/no-image-available.png"
            
            # Tạo HTML mới cho video, truyền cả thông tin trạng thái đã xử lý
            html = render_to_string(
                'render/base/iteam-video.html',
                {'item': new_video}
            )
            folder = new_video.folder_id  # Nếu đã là object, không cần truy vấn DB nữa
            user = folder.use  # Không cần truy vấn CustomUser nữa
            user_id = user.id  
            data = {
                'video_id': new_video.id, # Dữ liệu kèm theo
                'profile_id': profile_new.id,
                'video_iteam': html,  # Dữ liệu kèm theo
            }
            async_to_sync(channel_layer.group_send)(
                "admin",  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'add_videos',  # Thông báo
                    'data': data,  # Dữ liệu kèm theo
                }
            ) 
            async_to_sync(channel_layer.group_send)(
                str(user_id),  # Tên nhóm
                {
                    'type': 'update_count_admin',  # Loại sự kiện
                    'message': 'add_videos',  # Thông báo
                    'user': user_id,
                    'data':data,
                }
            ) 
            return JsonResponse({'status': 'success', 'message': 'Đã coppy video thành công'})

    def handle_thumbnail(self,video, thumnail, video_id):
        if video.url_thumbnail:
            image = video.url_thumbnail
            file_name = self.get_filename_from_url(image)
            default_storage.delete(f"data/{video_id}/thumnail/{file_name}")
        filename = thumnail.name.strip().replace(" ", "_")
        file_name = default_storage.save(f"data/{video_id}/thumnail/{filename}", thumnail)
        file_url = default_storage.url(file_name)
        video.url_thumbnail = file_url
        return file_url

    def update_video_info(self,video, input_data, date_formatted, json_text, thumnail, video_id):
        video.title = input_data['title']
        video.description = input_data['description']
        video.keywords = input_data['keyword']
        video.time_upload = input_data['time_upload']
        video.date_upload = date_formatted
        video.text_content = input_data['content']
        video.video_image = input_data['video_image']
        video.text_content_2 = json_text
        if thumnail:
            video.url_thumbnail = self.handle_thumbnail(video, thumnail, video_id)
        video.save()

    def get_infor_render(self, video):
        try:
            data = {
                'video_format': video.video_format,
                "is_content": video.folder_id.is_content,
                'url_reupload': video.url_reupload,
                "url_video_youtube": video.url_video_youtube,
                'video_id': video.id,
                'name_video': video.name_video,
                'text': video.text_content,
                'text_content': video.text_content_2,
                'images': video.video_image,
                'font_name': video.font_text.font_name if video.font_text else None,
                'font_size': video.font_size,
                'font_bold': video.font_bold,
                'font_italic': video.font_italic,
                'font_underline': video.font_underline,
                'font_strikeout': video.font_strikeout,
                'font_color': self.convert_color_to_ass(video.font_color, video.font_color_opacity),
                'color_background': self.convert_color_to_ass(video.font_background, video.channel_font_background_opacity),
                'stroke': self.convert_color_to_ass(video.font_color_troke, video.font_color_troke_opacity),
                'stroke_size': video.stroke_text,
                'language': video.channel_voice_style.voice_language.name if video.channel_voice_style and video.channel_voice_style.voice_language else "Unknown",
                'style': video.channel_voice_style.style_name if video.channel_voice_style else "Unknown",
                'voice_id': video.channel_voice_style.id_style if video.channel_voice_style else None,
                'name_langue': video.channel_voice_style.name_voice if video.channel_voice_style else "Unknown",
                'url_audio': video.url_audio,
                'file_srt': video.url_subtitle,
                'location_video_crop': video.location_video_crop,
                'speed_video_crop': video.speed_video_crop,
                'pitch_video_crop': video.pitch_video_crop,
                'channel_music_active': video.channel_music_active
            }
            return data
        except :
            return None
    
    def convert_color_to_ass(self, color_hex, opacity):
        # Chuyển đổi mã màu HEX sang RGB
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)

        # Tính giá trị Alpha từ độ trong suốt
        alpha = round(255 * (1 - opacity / 100))

        # Định dạng lại thành mã màu ASS
        ass_color = f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}&"

        return ass_color

class VideoRenderList(LoginRequiredMixin, TemplateView):
    login_url = '/login/'
    template_name = 'render/count_data_use.html'
    def get(self, request):
        current_date = timezone.now().date()
        data = []
        date = current_date.strftime("%Y-%m-%d")
        all_users = CustomUser.objects.all()
        for user in all_users:
            cread_video = Count_Use_data.objects.filter(use=user, creade_video=True, timenow=current_date).count()
            edit_title = Count_Use_data.objects.filter(use=user, edit_title=True, timenow=current_date).count()
            edit_thumnail = Count_Use_data.objects.filter(use=user, edit_thumnail=True, timenow=current_date).count()
            data.append({
                'user': user,
                'cread_video': cread_video,
                'edit_title': edit_title,
                'edit_thumnail': edit_thumnail
            })
        return render(request, self.template_name, {'data': data, 'current_date_old': date, 'current_date_new': date})
    
    def post(self, request):
        action = request.POST.get('action')
        if action == 'Seach':
            date_upload_old = request.POST.get('date_upload_old')
            date_upload_new = request.POST.get('date_upload_new')

            # Chuyển đổi chuỗi ngày tháng thành đối tượng datetime
            date_upload_old = timezone.datetime.strptime(date_upload_old, '%Y-%m-%d').date()
            date_upload_new = timezone.datetime.strptime(date_upload_new, '%Y-%m-%d').date()

            date_old = date_upload_old.strftime("%Y-%m-%d")
            date_new = date_upload_new.strftime("%Y-%m-%d")
            data = []
            all_users = CustomUser.objects.all()

            for user in all_users:
                cread_video = Count_Use_data.objects.filter(use=user, creade_video=True, timenow__range=[date_upload_old, date_upload_new]).count()
                edit_title = Count_Use_data.objects.filter(use=user, edit_title=True, timenow__range=[date_upload_old, date_upload_new]).count()
                edit_thumnail = Count_Use_data.objects.filter(use=user, edit_thumnail=True, timenow__range=[date_upload_old, date_upload_new]).count()
                data.append({
                    'user': user,
                    'cread_video': cread_video,
                    'edit_title': edit_title,
                    'edit_thumnail': edit_thumnail
                })

            return render(request, self.template_name, {'data': data, 'current_date_old': date_old, 'current_date_new': date_new})
        
        if action == 'Date-Yesterday':
            current_date = timezone.now().date() - timedelta(days=1)
            date = current_date.strftime("%Y-%m-%d")
            data = []
            all_users = CustomUser.objects.all()
            for user in all_users:
                cread_video = Count_Use_data.objects.filter(use=user, creade_video=True, timenow=current_date).count()
                edit_title = Count_Use_data.objects.filter(use=user, edit_title=True, timenow=current_date).count()
                edit_thumnail = Count_Use_data.objects.filter(use=user, edit_thumnail=True, timenow=current_date).count()
                data.append({
                    'user': user,
                    'cread_video': cread_video,
                    'edit_title': edit_title,
                    'edit_thumnail': edit_thumnail
                })
            return render(request, self.template_name, {'data': data, 'current_date_old': date, 'current_date_new': date})
        
        if action == 'Date-Today':
            current_date = timezone.now().date()
            date = current_date.strftime("%Y-%m-%d")
            data = []
            all_users = CustomUser.objects.all()
            for user in all_users:
                cread_video = Count_Use_data.objects.filter(use=user, creade_video=True, timenow=current_date).count()
                edit_title = Count_Use_data.objects.filter(use=user, edit_title=True, timenow=current_date).count()
                edit_thumnail = Count_Use_data.objects.filter(use=user, edit_thumnail=True, timenow=current_date).count()
                data.append({
                    'user': user,
                    'cread_video': cread_video,
                    'edit_title': edit_title,
                    'edit_thumnail': edit_thumnail
                })
            return render(request, self.template_name, {'data': data, 'current_date_old': date, 'current_date_new': date})
        
        if action == "Date-Month":
            current_date = timezone.now().date()
            first_day = current_date.replace(day=1)
            last_day = current_date.replace(day=calendar.monthrange(current_date.year, current_date.month)[1])
            date_old = first_day.strftime("%Y-%m-%d")
            date_new = last_day.strftime("%Y-%m-%d")
            data = []
            all_users = CustomUser.objects.all()

            for user in all_users:
                cread_video = Count_Use_data.objects.filter(use=user, creade_video=True, timenow__range=[first_day, last_day]).count()
                edit_title = Count_Use_data.objects.filter(use=user, edit_title=True, timenow__range=[first_day, last_day]).count()
                edit_thumnail = Count_Use_data.objects.filter(use=user, edit_thumnail=True, timenow__range=[first_day, last_day]).count()
                data.append({
                    'user': user,
                    'cread_video': cread_video,
                    'edit_title': edit_title,
                    'edit_thumnail': edit_thumnail
                })

            return render(request, self.template_name, {
                'data': data, 
                'current_date_old': date_old, 
                'current_date_new': date_new
            })

        elif action == 'show-thumnail':
            id = request.POST.get('id')
            page = request.POST.get('page')
            date_upload_old = request.POST.get('current_date_old')
            date_upload_new = request.POST.get('current_date_new')
            user = CustomUser.objects.get(id=id)
            data = Count_Use_data.objects.filter(use=user, edit_thumnail=True, timenow__range=[date_upload_old, date_upload_new])
            paginator = Paginator(data,9)
            page_obj = paginator.get_page(page)
            thumnail = render_to_string('render/show-image.html', {'page_obj': page_obj}, request)
            page_obj = render_to_string('render/thumnail_page_bar_template.html', {'page_obj': page_obj}, request)
            return JsonResponse({'success': True, 'thumnail_html': thumnail, 'page_bar_html': page_obj})
        

        elif action == 'show-title':
            id = request.POST.get('id')
            page = request.POST.get('page')
            date_upload_old = request.POST.get('current_date_old')
            date_upload_new = request.POST.get('current_date_new')

            # Chuyển đổi chuỗi ngày tháng thành đối tượng datetime
            date_upload_old = timezone.datetime.strptime(date_upload_old, '%Y-%m-%d').date()
            date_upload_new = timezone.datetime.strptime(date_upload_new, '%Y-%m-%d').date()

            user = CustomUser.objects.get(id=id)
            data = Count_Use_data.objects.filter(use=user, edit_title=True, timenow__range=[date_upload_old, date_upload_new])
            paginator = Paginator(data, 10)
            page_obj = paginator.get_page(page)

            # Sử dụng page_obj thay vì paginator khi gọi render_to_string
            title_html = render_to_string('render/show-title.html', {'page_obj': page_obj}, request)
            page_bar_html = render_to_string('render/title_page_bar_template.html', {'page_obj': page_obj}, request)

            return JsonResponse({'success': True, 'title_html': title_html, 'page_bar_html': page_bar_html})
 
def download_file(request):
    # Lấy bản ghi đầu tiên từ App_Update
    app_update = App_Update.objects.first()

    # Kiểm tra nếu không có bản ghi nào
    if not app_update:
        return JsonResponse({"error": "No records found in App_Update"}, status=404)

    # Kiểm tra nếu file_upload không có tệp
    if not app_update.file_upload:
        return JsonResponse({"error": "No file uploaded for the first record"}, status=404)

    # Trả về URL của tệp
    file_url = app_update.file_upload.url
    return HttpResponseRedirect(file_url)

@login_required(login_url="/login/")
def get_image(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid HTTP method. Use POST."}, status=405)

    try:
        # Lấy thông tin của người dùng đang yêu cầu
        user = request.user
        source = request.POST.get("source", "")
        keyword = request.POST.get("input-keyword", "")
        list_url = []

        if source == "google":
            # API Google Images
            url = "https://google.serper.dev/images"
            payload = json.dumps({
                "q": keyword,  # Sử dụng từ khóa từ client
                "num": 100,
                "type": "images",
                "tbs": "qdr:h"
            })

            # Lấy API key của người dùng
            api_key = getattr(user, 'api_key_google', None)
            if not api_key:
                return JsonResponse({"success": False, "error": "API key not found for Google Images"}, status=403)

            headers = {
                'X-API-KEY': api_key,
                'Content-Type': 'application/json'
            }

            # Gửi yêu cầu đến API Google Images
            response = requests.post(url, headers=headers, data=payload)



            if response.status_code == 200:
                data = response.json()
                for item in data.get("images", []):
                    width = item.get("imageWidth", 0)
                    height = item.get("imageHeight", 0)
                    url = item.get("imageUrl", "")
                    # Chỉ lấy ảnh ngang
                    if width > height:
                        list_url.append({
                            'is_image': True,
                            'file_name': get_name_url(url),
                            'url': url,
                        })
            else:
                return JsonResponse({"success": False, "error": f"Google API returned status {response.status_code}"}, status=response.status_code)
            
        elif source == "freepik":
            url = "https://www.freepik.com/api/regular/search"
            params = {
                "filters[ai-generated][only]": 1,
                "filters[content_type]": "photo",
                "filters[license]": "free",
                "locale": "en",
                "term": keyword,
            }
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    preview = item.get("preview", {})
                    width = preview.get("width", 0)
                    height = preview.get("height", 0)
                    url = preview.get("url", "")
                    if width > height:  # Chỉ lấy ảnh ngang
                        list_url.append({
                            'is_image': True,
                            'file_name': get_name_url(url),
                            'url': url,
                        })
        # Render template với danh sách URL
        context = {"list_url": list_url}
        return render(request, "render/base/iteam-views.html", context)

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
   
def get_name_url(url):
    """
    Trích xuất tên file từ URL và xử lý nếu tên file quá dài.

    Args:
        url (str): URL chứa file.

    Returns:
        str: Tên file được xử lý.
    """
    # Loại bỏ query string
    clean_url = url.split('?')[0]

    # Lấy tên file từ URL đã làm sạch
    file_name = clean_url.split('/')[-1]

    # Xử lý tên file nếu quá dài
    if len(file_name) > 15:
        return f"{file_name[:5]} ... {file_name[-10:]}"
    return file_name

@login_required(login_url="/login/") 
def get_video(request):
    """
    Xử lý yêu cầu POST để lấy danh sách URL video từ Freepik API.
    """
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid HTTP method. Use POST."}, status=405)

    try:
        keyword = request.POST.get("input-keyword", "")
        # URL API Freepik
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": "38396855-7183824f50d61fd232c569758",
            "q": keyword,
            "lang": "en",
            "video_type": "all",
            "per_page": 100,
            "page": 1,
        }
        
        # Gửi yêu cầu đến Freepik API
        response = requests.get(url, params=params)

        list_url = []
        # Kiểm tra trạng thái phản hồi
        if response.status_code == 200:
            data = response.json()
            
            # Kiểm tra nếu có hits
            if "hits" in data:
                for item in data["hits"]:
                    small_video = item.get("videos", {}).get("small", {})
                    video_width = small_video.get("width", 0)
                    video_height = small_video.get("height", 0)
                    video_duration = int(item.get("duration", 0))

                    # Kiểm tra kích thước và thời lượng
                    if video_width == 1920 and video_height == 1080  and video_duration >= 10:
                        url = small_video.get("url", "")
                        print(url)
                        list_url.append({
                            'is_image': False,
                            'file_name': get_name_url(url),
                            'url': url,
                        })
            context = {"list_url": list_url}
            return render(request, "render/base/iteam-views.html", context)
        else:
            return JsonResponse({"success": False, "error": f"Freepik API returned status {response.status_code}"}, status=response.status_code)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
 
@login_required(login_url="/login/") 
def get_video_id(request):
    video_id = request.POST.get('id_video')  # Lấy ID video từ yêu cầu POST
    print("📌 ID video nhận được:", video_id)
    # Kiểm tra nếu ID hợp lệ
    if not video_id:
        return render(request, "render/base/update-infor-video.html", {"error": "ID video không hợp lệ."})

    # Lấy video hoặc trả về 404 nếu không tìm thấy
    video = get_object_or_404(VideoRender, id=video_id)

    # Xử lý text_content_2
    text_content_2 = []
    if video.text_content_2:  # Kiểm tra nếu `text_content_2` không rỗng
        try:
            text_content_2 = json.loads(video.text_content_2)
            for item in text_content_2:
                url = item.get("url_video", "")
                url_type = is_video_or_image(url) if url else "unknown"
                item["url_type"] = url_type
        except json.JSONDecodeError:
            print("⚠️ Lỗi: `text_content_2` không phải là JSON hợp lệ!")
            text_content_2 = []

    # Xử lý video_image
    list_image = []
    if video.video_image:  # Kiểm tra nếu `video_image` không rỗng
        list_url = json.loads( video.video_image)
        for item in list_url:
            content = {
                "url_type": is_video_or_image(item),
                "name_file": get_name_url(item),
                "Url_file": item,
            }
            list_image.append(content)

    return render(request, "render/base/update-infor-video.html", {
        'item': video,
        "text_content_2": text_content_2,
        "list_image": list_image
    })

def is_video_or_image(url):
    """
    Kiểm tra URL xem là video hay hình ảnh.
    
    Args:
        url (str): URL cần kiểm tra.
        
    Returns:
        str: "video" nếu URL là video, "image" nếu URL là hình ảnh, hoặc "unknown".
    """
    if not url:
        return "unknown"

    # Parse URL để lấy phần đường dẫn
    parsed_url = urllib.parse.urlparse(url)
    path = parsed_url.path.lower()

    # Đoán loại MIME dựa trên phần mở rộng
    mime_type, _ = mimetypes.guess_type(path)

    if mime_type:
        if mime_type.startswith("video"):
            return "video"
        elif mime_type.startswith("image"):
            return "image"

    return "unknown"
    
@cache_page(60 * 30)  # Cache trong 30 phút
def get_list_video(request):
    try:
        with open("filtered_videos.json", "r", encoding="utf-8") as file:
            data = json.load(file)  # Đọc nội dung file và parse thành Python object (list hoặc dict)
    except FileNotFoundError:
        return JsonResponse({"error": "File not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    # Trả về dữ liệu dưới dạng JSON
    return JsonResponse(data, safe=False)
        


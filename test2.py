from core.celery import app 
from apps.render.models import VideoRender
from collections import Counter

# Kiểm tra các task đang hoạt động
active_tasks = app.control.inspect().active()
total_active = 0
list_id = []
tasks_to_revoke = []
task_details = {}  # Lưu thông tin chi tiết của mỗi task

if active_tasks:
    for worker, tasks in active_tasks.items():
        worker_active_count = len(tasks)
        total_active += worker_active_count
        print(f"Worker {worker} đang có {worker_active_count} task đang hoạt động:")
        
        for task in tasks:
            # In thông tin về mỗi task
            task_id = task['id']
            print(f"  - Task ID: {task_id}")
            print(f"    Tên: {task['name']}")
            print(f"    Thời gian bắt đầu: {task.get('time_start', 'N/A')}")
            print(f"    Keyword args: {task.get('kwargs', {})}")
            data = task.get('args', [])
            
            # Đảm bảo data có phần tử và có key 'video_id'
            if data and isinstance(data[0], dict) and 'video_id' in data[0]:
                print(f"    Tên: {task['name']}")
                video_id = data[0]['video_id']
                list_id.append(video_id)
                tasks_to_revoke.append(task_id)
                
                # Lưu thông tin chi tiết
                if video_id not in task_details:
                    task_details[video_id] = []
                task_details[video_id].append({
                    'task_id': task_id,
                    'worker': worker,
                    'time_start': task.get('time_start', 'N/A')
                })
                
                
                print(video_id)
            else:
                print(f"    --> Không tìm thấy video_id trong task này")
    
    # Sử dụng Counter để đếm số lần xuất hiện của mỗi video_id
    video_id_counts = Counter(list_id)
    
    # Tìm video_id bị trùng (xuất hiện nhiều hơn 1 lần)
    duplicate_video_ids = {video_id: count for video_id, count in video_id_counts.items() if count > 1}
    unique_video_ids = {video_id: count for video_id, count in video_id_counts.items() if count == 1}
    
    print("\n=== THỐNG KÊ ===")
    print(f"Tổng số task đang chạy: {total_active}")
    print(f"Tổng số video_id được xử lý: {len(video_id_counts)}")
    print(f"Số video_id bị trùng: {len(duplicate_video_ids)}")
    print(f"Số video_id không bị trùng: {len(unique_video_ids)}")
    
    # Hiển thị chi tiết về các video_id bị trùng
    if duplicate_video_ids:
        print("\n=== CHI TIẾT CÁC VIDEO_ID BỊ TRÙNG ===")
        for video_id, count in duplicate_video_ids.items():
            print(f"Video ID: {video_id} - Đang được xử lý bởi {count} task:")
            for task_info in task_details[video_id]:
                print(f"  - Task ID: {task_info['task_id']}")
                print(f"    Worker: {task_info['worker']}")
                print("xxxxxxxxxxxxxxxxxxx")
                print(f"    Worker: {video_id}")
                print(f"    Thời gian bắt đầu: {task_info['time_start']}")
                
                
        videos = VideoRender.objects.filter(id__in=list_id)
        print("\nTrạng thái hiện tại của các video:")
        print(len(videos))
        for video in videos:
            print(f"Video ID: {video.id}, Trạng thái: {video.status_video} , name video {video.name_video} ,{video.folder_id} ,{video.profile_id}")
else:
    print("Không có task đang hoạt động hoặc không có worker nào đang chạy")
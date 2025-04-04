# Mở Django shell
python manage.py shell

# Trong shell:
from core.celery import app  # Thay 'myproject' bằng tên dự án của bạn
purged = app.control.purge()
print(f"Đã xóa {purged} task.")

from core.celery import app 
from apps.render.task import render_video_task

# Kiểm tra các task đang hoạt động
active_tasks = app.control.inspect().active()
total_active = 0
list_id = []
tasks_to_revoke = []

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
                video_id = data[0]['video_id']
                
                if video_id in list_id:
                    # ID đã tồn tại, thêm task vào danh sách cần hủy
                    tasks_to_revoke.append(task_id)
                    video = VideoRender.objects.get(id=video_id)
                    video.update(status_video="render")
                    print(f"    --> Phát hiện video_id trùng lặp: {video_id}, sẽ hủy task này")
                else:
                    # ID chưa tồn tại, thêm vào danh sách đã xử lý
                    list_id.append(video_id)
                    print(f"    --> Thêm video_id vào danh sách theo dõi: {video_id}")
            else:
                print(f"    --> Không tìm thấy video_id trong task này")
            
    print(f"\nTổng số task đang hoạt động: {total_active}")
    
    # Hủy các task trùng lặp
    if tasks_to_revoke:
        print(f"\nĐang hủy {len(tasks_to_revoke)} task trùng lặp...")
        for task_id in tasks_to_revoke:
            try:
                # Hủy task bằng ID
                app.control.revoke(task_id, terminate=True, signal='SIGKILL')
                print(f"Đã hủy task ID: {task_id}")
            except Exception as e:
                print(f"Lỗi khi hủy task {task_id}: {str(e)}")
else:
    print("Không có task đang hoạt động hoặc không có worker nào đang chạy")

print("\nDanh sách video_id đã xử lý:")
print(list_id)
print(f"Tổng số video_id duy nhất: {len(list_id)}")



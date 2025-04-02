from apps.render.models import VideoRender
from core.celery import app 

# Kiểm tra các task đang hoạt động
active_tasks = app.control.inspect().active()
total_active = 0
list_id = []
tasks_to_revoke = set()  # Thay đổi từ list sang set
task_video_mapping = {}  # Thêm dictionary để theo dõi mapping

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
                    # ID đã tồn tại, thêm task vào set cần hủy
                    tasks_to_revoke.add(task_id)  # Sử dụng add() thay vì append()
                    
                    # Kiểm tra và ghi log nếu task ID đã được mapping trước đó
                    if task_id in task_video_mapping:
                        print(f"    --> LƯU Ý: Task ID {task_id} đã được ánh xạ với video_id {task_video_mapping[task_id]}, hiện đang xuất hiện với video_id {video_id}")
                    
                    task_video_mapping[task_id] = video_id
                    
                    try:
                        # Cập nhật trạng thái video trong database
                        VideoRender.objects.filter(id=video_id).update(status_video="render")
                        print(f"    --> Phát hiện video_id trùng lặp: {video_id}, sẽ hủy task này")
                        print(f"    --> Đã cập nhật trạng thái video {video_id} thành 'render'")
                    except Exception as e:
                        print(f"    --> Lỗi khi cập nhật trạng thái video {video_id}: {str(e)}")
                else:
                    # ID chưa tồn tại, thêm vào danh sách đã xử lý
                    list_id.append(video_id)
                    task_video_mapping[task_id] = video_id
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
    
    # Hiển thị thông tin tổng hợp
    print(f"\nTổng số task trùng lặp đã hủy: {len(tasks_to_revoke)}")
    print(f"Tổng số task còn lại: {total_active - len(tasks_to_revoke)}")
else:
    print("Không có task đang hoạt động hoặc không có worker nào đang chạy")

# Hiển thị thông tin về danh sách video_id
print("\nDanh sách video_id đã xử lý:")
for idx, video_id in enumerate(list_id, 1):
    print(f"{idx}. {video_id}")
print(f"Tổng số video_id duy nhất: {len(list_id)}")

list_render = []
# Kiểm tra trạng thái hiện tại của các video trong danh sách
try:
    videos = VideoRender.objects.filter(id__in=list_id)
    print("\nTrạng thái hiện tại của các video:")
    print(len(videos))
    for video in videos:
        if "Đang Render" in video.status_video:
            list_render.append(videos)
        print(f"Video ID: {video.id}, Trạng thái: {video.status_video} , name video {video.name_video}")
        print(len(list_render))
except Exception as e:
    print(f"Lỗi khi truy vấn trạng thái video: {str(e)}")
    print(len(list_render))
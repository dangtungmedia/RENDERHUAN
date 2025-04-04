from core.celery import app

# Lấy inspector từ Celery app
inspector = app.control.inspect()

# Lấy thông tin các task được đăng ký
registered_tasks = inspector.registered()

# Từ điển để lưu trữ kết quả
worker_task_mapping = {}

if registered_tasks:
    for worker, tasks in registered_tasks.items():
        # Bỏ qua worker có tiền tố "SEVER"
        if worker.startswith('SEVER'):
            continue
        
        # Làm sạch tên worker (loại bỏ potential prefixes)
        clean_worker_name = worker.split('@')[-1] if '@' in worker else worker
        
        # Lưu danh sách task names
        worker_task_mapping[clean_worker_name] = list(tasks)


list_name_task =[]
# In ra mapping
print("===== WORKER VÀ CÁC TASK ĐƯỢC PHÉP XỬ LÝ =====")
for worker, tasks in worker_task_mapping.items():
    print(f"\nWorker: {worker}")
    print("Các task được phép xử lý:")
    for task in tasks:
        if task not in list_name_task:
            list_name_task.append(task)
print(list_name_task)
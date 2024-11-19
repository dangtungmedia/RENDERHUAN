#!/bin/sh

if [ ! -d /app/video_screen ]; then
    echo 'Thư mục chưa tồn tại, tiến hành tải và giải nén.'
    wget -O /app/video_screen.rar 'https://hrmedia89.com/download_file_screen/' &&
    mkdir -p /app/video_screen &&
    unrar x /app/video_screen.rar /app/video_screen

    if [ $? -eq 0 ]; then
        rm -f /app/video_screen.rar
        echo 'done' > /app/video_screen/ready.txt
    else
        echo 'Giải nén thất bại. Xóa file nén.'
        rm -f /app/video_screen.rar
    fi
else
    echo 'Thư mục đã tồn tại, không tải và giải nén lại.'
    echo 'done' > /app/video_screen/ready.txt
fi

# Giữ cho container không bị thoát
tail -f /dev/null

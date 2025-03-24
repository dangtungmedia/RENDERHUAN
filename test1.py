
# chuyển đổi định dạng  về  1 định dạng 
ffmpeg -i chace_video/8935-215796381_medium.mp4 -vf scale=1280:720,fps=24,setpts=1*PTS -c:v h264_nvenc -profile:v high -b:v 12558k -an -f mp4 -movflags +faststart -y output.mp4

# slide hình ảnh không mov zoom in 
ffmpeg -loop 1 -framerate 24 -i "anh-co-gai-xinh-dep-4.jpg" -i "media/338516/voice/14.wav" -vf "format=yuv420p,scale=8000:-1,zoompan=z='zoom+0.003':x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):s=1920x1080:fps=24" -r 24 -c:v h264_nvenc -profile:v high -b:v 12558k -c:a aac -b:a 192k -map 0:v:0 -map 1:a:0 -shortest -f mp4 -movflags +faststart -y output.mp4

# mã hình ảnh âm thanh và screen  zoom in 
ffmpeg -loop 1 -framerate 24 -i "anh-co-gai-xinh-dep-4.jpg" -i "Video_screen\screen03.mov" -i "media/338516/voice/14.wav" -filter_complex "[0:v]format=yuv420p,scale=8000:-1,zoompan=z='zoom+0.003':x=iw/2-(iw/zoom/2):y=ih/2-(ih/zoom/2):d=240:s=1920x1080:fps=24[bg];[1:v]scale=1920:1080,fps=24[overlay_scaled];[bg][overlay_scaled]overlay=format=auto,format=yuv420p[outv]" -map "[outv]" -map 2:a:0 -c:v h264_nvenc -profile:v high -b:v 12558k -c:a aac -b:a 192k -shortest -f mp4 -movflags +faststart -y output.mp4




# cắt video không có mov
ffmpeg -ss 00:00:00 -i "media/363030/image/76719-560201053_large.mp4" -i "media/363030/voice/6.wav" -vf "scale=1920:1080,fps=24,setpts=1*PTS" -c:v h264_nvenc -profile:v high -b:v 12558k -c:a aac -b:a 192k -map 0:v:0 -map 1:a:0 -shortest -f mp4 -movflags +faststart -y output.mp4


# nếu video dài hơn + Mov
ffmpeg -y -ss 00:00:00 -i "video\42033-431407107_medium.mp4" -i "Video_screen\screen03.mov" -i "media/338516/voice/14.wav" -filter_complex "[0:v]scale=1280:720,fps=24,setpts=1*PTS[bg];[1:v]scale=1280:720[fg];[bg][fg]overlay=format=auto[outv]" -map "[outv]" -map 2:a:0 -c:v h264_nvenc -profile:v high -b:v 12558k -c:a aac -b:a 192k -shortest -f mp4 -movflags +faststart -y output.mp4







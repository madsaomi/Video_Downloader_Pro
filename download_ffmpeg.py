import urllib.request
import zipfile
import os
import shutil

url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
zip_path = "ffmpeg.zip"

print("Downloading FFmpeg...")
urllib.request.urlretrieve(url, zip_path)

print("Extracting FFmpeg...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall("ffmpeg_temp")

# Find the bin folder
for root, dirs, files in os.walk("ffmpeg_temp"):
    if "ffmpeg.exe" in files:
        shutil.move(os.path.join(root, "ffmpeg.exe"), "ffmpeg.exe")
    if "ffprobe.exe" in files:
        shutil.move(os.path.join(root, "ffprobe.exe"), "ffprobe.exe")

print("Cleaning up...")
os.remove(zip_path)
shutil.rmtree("ffmpeg_temp")
print("Done! ffmpeg.exe and ffprobe.exe are now in the directory.")

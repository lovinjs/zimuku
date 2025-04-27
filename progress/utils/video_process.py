import subprocess
import json


def process_video(video_path):
    """获取视频元信息"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_format",
        "-show_streams",
        "-of", "json",
        video_path
    ]
    result = subprocess.check_output(cmd).decode()
    return json.loads(result)

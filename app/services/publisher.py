import requests
import json
from app.config import settings
from app.utils.api_clients import volcano_sign_request
from pathlib import Path
import time


def publish_video(video_path: Path, schedule_time: str = None):
    # 第一步：初始化上传
    init_url = "https://open.douyin.com/api/v2/video/upload/"
    headers = {
        "Authorization": f"Bearer {settings.DOUYIN_TOKEN}",
        "Content-Type": "application/json"
    }

    init_data = {
        "source": "client_video",
        "file_name": video_path.name
    }

    init_resp = requests.post(init_url, json=init_data, headers=headers)
    upload_id = init_resp.json()["upload_id"]
    chunk_size = 1024 * 1024 * 5  # 5MB分块

    # 第二步：分块上传
    with open(video_path, "rb") as f:
        part_number = 1
        while chunk := f.read(chunk_size):
            upload_url = "https://open.douyin.com/api/v2/video/upload/part/upload/"
            files = {
                "video": (video_path.name, chunk, "video/mp4"),
                "upload_id": (None, upload_id),
                "part_number": (None, str(part_number))
            }

            upload_resp = requests.post(upload_url, files=files, headers=headers)
            part_number += 1

    # 第三步：提交发布
    publish_url = "https://open.douyin.com/api/v2/video/create/"
    publish_data = {
        "upload_id": upload_id,
        "title": "自动生成视频",
        "allow_comment": True,
        "allow_share": True
    }

    if schedule_time:
        publish_data["schedule_time"] = int(time.mktime(
            datetime.strptime(schedule_time, "%Y-%m-%d %H:%M:%S").timetuple()
        ))

    response = requests.post(publish_url, json=publish_data, headers=headers)
    return response.json()
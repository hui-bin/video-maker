import json
import time
import uuid
from pathlib import Path

import requests
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip

from app.config import settings
from app.utils.api_clients import volcano_sign_request


def generate_videos(scenes: list, image_paths: list, task_dir: Path):
    video_paths = []

    # 新的视频生成 API 请求参数构建
    def build_api_request(scenes, image_paths):
        content = []
        if image_paths:
            for idx, img_path in enumerate(image_paths):
                # 处理图片，可根据需求选择 URL 或 Base64 编码
                with open(img_path, "rb") as f:
                    import base64
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                    image_url = f"data:image/jpeg;base64,{image_data}"
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                })
        if scenes:
            for scene in scenes:
                text = scene["narration"]
                # 可根据需求添加参数，如 --ratio 16:9 等
                content.append({
                    "type": "text",
                    "text": text
                })
        return {
            "model": settings.VIDEO_GENERATION_MODEL_EP,  # 假设在 settings 中配置了推理接入点 ID
            "content": content
        }

    api_request = build_api_request(scenes, image_paths)

    # 发送创建视频生成任务请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.ACCESS_TOKEN}"
    }
    response = requests.post(settings.VIDEO_GENERATION_API_URL, headers=headers, json=api_request)
    response_data = response.json()
    if response.status_code != 200:
        print(f"视频生成任务创建失败: {response_data}")
        raise Exception(f"视频生成任务创建失败: {response_data}")
    task_id = response_data["id"]

    # 查询任务状态，等待任务完成
    while True:
        query_response = requests.get(settings.VIDEO_GENERATION_API_QUERY_URL.format(task_id), headers=headers)
        query_data = query_response.json()
        status = query_data["status"]
        if status == "succeeded":
            video_url = query_data["content"]["video_url"]
            break
        elif status == "failed":
            error = query_data["error"]
            print(f"视频生成任务失败: {error}")
            raise Exception(f"视频生成任务失败: {error}")
        elif status == "cancelled":
            print(f"视频生成任务被取消: {task_id}")
            raise Exception(f"视频生成任务被取消: {task_id}")
        time.sleep(5)  # 每隔 5 秒查询一次

    # 下载生成的视频
    video_data = requests.get(video_url).content
    video_path = task_dir / "generated_video.mp4"
    with open(video_path, "wb") as f:
        f.write(video_data)
    video_paths.append(video_path)

    return video_paths


def _generate_tts(text: str, task_dir: Path, idx) -> Path:
    # 生成唯一的 reqid
    reqid = str(uuid.uuid4())

    # 构建请求数据
    data = {
        "app": {
            "appid": settings.APPID,  # 假设 APPID 存储在 settings 中
            "token": settings.ACCESS_TOKEN,  # 假设 ACCESS_TOKEN 存储在 settings 中
            "cluster": "volcano_tts",
        },
        "user": {
            "uid": "uid123"  # 可根据实际情况修改
        },
        "audio": {
            "voice_type": "zh_male_M392_conversation_wvae_bigtts",
            "encoding": "mp3",
            "speed_ratio": 1.0,
        },
        "request": {
            "reqid": reqid,
            "text": text,
            "operation": "query",
        }
    }

    # 设置请求头
    headers = {
        "Authorization": f"Bearer;{settings.ACCESS_TOKEN}",  # 注意 Bearer 和 token 使用分号分隔
        "Content-Type": "application/json"
    }

    # 发送请求
    response = requests.post(
        "https://openspeech.bytedance.com/api/v1/tts",
        headers=headers,
        json=data
    )

    # 解析响应
    response_data = response.json()
    if response_data["code"] != 3000:
        raise Exception(f"TTS 请求失败，错误码: {response_data['code']}, 错误信息: {response_data['message']}")

    # 解码 base64 编码的音频数据
    import base64
    audio_data = base64.b64decode(response_data["data"])

    # 保存音频文件
    path = task_dir / f"audio{idx}.mp3"
    with open(path, "wb") as f:
        f.write(audio_data)

    return path


def _generate_video_clip(image_path: str, audio_path: str, task_dir: Path, index: int) -> Path:
    # 调用火山引擎图生视频API
    headers = volcano_sign_request("POST", "/vod/v1/video_ai/gen", {})
    headers.update({"Content-Type": "application/json"})

    with open(image_path, "rb") as f:
        image_data = f.read()

    files = {
        "image": (f"scene_{index}.jpg", image_data, "image/jpeg"),
        "config": (None, json.dumps({
            "duration": 5,
            "transition": "slide"
        }), "application/json")
    }

    response = requests.post(
        settings.VOLCANO_VIDEO_URL,
        headers=headers,
        files=files
    )

    video_url = response.json()["video_url"]
    video_data = requests.get(video_url).content
    raw_video_path = task_dir / f"raw_video_{index}.mp4"

    with open(raw_video_path, "wb") as f:
        f.write(video_data)

    # 合并音频视频
    final_path = task_dir / f"final_clip_{index}.mp4"
    _merge_audio_video(str(raw_video_path), str(audio_path), str(final_path))

    return final_path


def _merge_audio_video(video_path: str, audio_path: str, output_path: str):
    video = VideoFileClip(video_path)
    audio = AudioFileClip(audio_path)

    # 调整音频时长与视频一致
    audio = audio.set_duration(video.duration)

    final_clip = video.set_audio(CompositeAudioClip([audio]))
    final_clip.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        threads=4
    )

    video.close()
    audio.close()


def combine_videos(video_paths: list, task_dir: Path) -> Path:
    clips = [VideoFileClip(str(p)) for p in video_paths]
    final_clip = concatenate_videoclips(clips, method="compose")

    output_path = task_dir / "final_output.mp4"
    final_clip.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        threads=4
    )

    for clip in clips:
        clip.close()

    return output_path

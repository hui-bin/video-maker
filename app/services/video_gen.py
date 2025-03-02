import base64
import logging
import time
import uuid
from pathlib import Path
from typing import List

import requests
from moviepy.editor import concatenate_videoclips, ImageClip
from moviepy.editor import VideoFileClip, AudioFileClip

from app.config import settings
from app.services.video_gen_core import (
    encode_image_to_base64,
    create_video_generation_task,
    get_video_generation_task,
    download_video,
    delete_video_generation_task
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoGenerationError(Exception):
    """自定义视频生成异常"""
    pass


class TTSGenerationError(Exception):
    """自定义语音生成异常"""
    pass


def generate_videos(scenes: List[dict], image_paths: List[str], task_dir: Path) -> List[Path]:
    """
    生成视频主流程
    :param scenes: 场景描述列表
    :param image_paths: 对应图片路径列表
    :param task_dir: 任务输出目录
    :return: 生成的视频路径列表
    """
    video_paths = []

    for idx, (scene, image_path) in enumerate(zip(scenes, image_paths)):
        logger.info(f"正在处理第 {idx + 1}/{len(scenes)} 个场景...")
        retries = 0
        MAX_RETRIES = settings.MAX_RETRIES

        while retries < MAX_RETRIES:
            try:
                # 生成视频
                raw_video_path = _generate_single_video(
                    image_path=image_path,
                    text_prompt=scene["narration"],
                    task_dir=task_dir,
                    index=idx
                )

                # 生成语音
                audio_path = _generate_tts(
                    text=scene["narration"],
                    task_dir=task_dir,
                    idx=idx
                )

                # 合并音视频
                merged_path = _merge_audio_video(
                    video_path=raw_video_path,
                    audio_path=audio_path,
                    task_dir=task_dir,
                    index=idx
                )

                video_paths.append(merged_path)
                break

            except VideoGenerationError as e:
                logger.error(f"视频生成失败: {str(e)}")
                retries += 1
                if retries >= MAX_RETRIES:
                    raise RuntimeError(f"场景 {idx} 视频生成达到最大重试次数")

            except TTSGenerationError as e:
                logger.error(f"语音生成失败: {str(e)}")
                retries += 1
                if retries >= MAX_RETRIES:
                    raise RuntimeError(f"场景 {idx} 语音生成达到最大重试次数")

            except Exception as e:
                logger.error(f"未知错误: {str(e)}")
                retries += 1
                if retries >= MAX_RETRIES:
                    raise RuntimeError(f"场景 {idx} 处理失败")

    return video_paths


def _generate_single_video(image_path: str, text_prompt: str, task_dir: Path, index: int) -> Path:
    """生成单个视频片段"""
    # try:
    # 校验图片文件
    if not Path(image_path).exists():
        raise FileNotFoundError(f"图片文件 {image_path} 不存在")

    # 编码图片
    logger.info(f"正在编码第 {index} 张图片...")
    image_base64 = encode_image_to_base64(image_path)

    # 创建生成任务
    logger.info(f"创建第 {index} 个视频生成任务...")
    create_result = create_video_generation_task(
        model_id=settings.VIDEO_GENERATION_MODEL_EP,
        text_prompt=text_prompt,
        image_base64=image_base64
    )

    # 轮询任务状态
    logger.info(f"开始轮询任务状态 [{create_result.id}]...")
    start_time = time.time()
    while True:
        if time.time() - start_time > settings.VIDEO_GENERATION_TIMEOUT:
            delete_video_generation_task(create_result.id)
            raise TimeoutError("视频生成超时")

        task_info = get_video_generation_task(create_result.id)

        if task_info.status == 'succeeded':
            logger.info(f"任务 {create_result.id} 成功完成")
            break
        if task_info.status == 'failed':
            delete_video_generation_task(create_result.id)
            raise VideoGenerationError(f"视频生成失败: {task_info.error}")

        logger.debug(f"任务状态: {task_info.status}, 等待 {settings.POLLING_INTERVAL} 秒后重试...")
        time.sleep(settings.POLLING_INTERVAL)

    # 下载视频
    video_url = task_info.content.video_url
    raw_video_path = task_dir / f"raw_video_{index}.mp4"
    logger.info(f"正在下载视频到 {raw_video_path}...")
    download_video(video_url, raw_video_path)

    return raw_video_path

    # except Exception as e:
    #     logger.error(f"视频生成失败: {str(e)}")
    #     raise VideoGenerationError(str(e))


def _generate_tts(text: str, task_dir: Path, idx: int) -> Path:
    """
    生成TTS语音文件
    :param text: 需要合成的文本
    :param task_dir: 输出目录
    :param idx: 场景索引
    :return: 生成的音频文件路径
    """
    try:
        logger.info(f"正在生成第 {idx} 段语音...")

        # 生成唯一请求ID
        reqid = str(uuid.uuid4())

        # 构建请求数据
        data = {
            "app": {
                "appid": settings.APPID,
                "token": settings.ACCESS_TOKEN,
                "cluster": "volcano_tts",
            },
            "user": {
                "uid": f"user_{idx}"  # 唯一用户标识
            },
            "audio": {
                "voice_type": settings.TTS_VOICE_TYPE,
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
            "Authorization": f"Bearer;{settings.ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Request-ID": reqid
        }

        # 发送请求
        response = requests.post(
            settings.TTS_API_ENDPOINT,
            headers=headers,
            json=data,
            timeout=settings.TTS_TIMEOUT
        )

        # 处理响应
        if response.status_code != 200:
            raise TTSGenerationError(f"API请求失败，状态码: {response.status_code}")

        response_data = response.json()
        if response_data.get("code") != 3000:
            raise TTSGenerationError(
                f"TTS生成失败，错误码: {response_data.get('code', 'unknown')}, "
                f"错误信息: {response_data.get('message', '无错误信息')}"
            )

        # 解码并保存音频
        audio_data = base64.b64decode(response_data["data"])
        audio_path = task_dir / f"audio_{idx}.mp3"

        with open(audio_path, "wb") as f:
            f.write(audio_data)

        logger.info(f"语音文件已保存到 {audio_path}")
        return audio_path

    except requests.exceptions.RequestException as e:
        raise TTSGenerationError(f"网络请求失败: {str(e)}")
    except KeyError as e:
        raise TTSGenerationError(f"响应数据格式错误: {str(e)}")
    except Exception as e:
        raise TTSGenerationError(f"未知错误: {str(e)}")


def _merge_audio_video(video_path: Path, audio_path: Path, task_dir: Path, index: int) -> Path:
    """合并音视频"""
    try:
        logger.info(f"开始合并第 {index} 个音视频...")
        output_path = task_dir / f"merged_{index}.mp4"

        # 加载视频和音频
        video = VideoFileClip(str(video_path))
        audio = AudioFileClip(str(audio_path))

        # 以音频时长为准处理视频
        if video.duration > audio.duration:
            # 视频时长超过音频时长，裁剪视频
            video = video.subclip(0, audio.duration)
        elif video.duration < audio.duration:
            # 视频时长小于音频时长，复制最后一帧画面补足时长
            last_frame = video.get_frame(video.duration - 1)
            extra_clip = ImageClip(last_frame).set_duration(audio.duration - video.duration)
            video = concatenate_videoclips([video, extra_clip])

        # 设置音频
        final_clip = video.set_audio(audio)

        # 输出设置
        final_clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            threads=4,
            verbose=False,
            logger=None  # 禁用 moviepy 日志
        )

        logger.info(f"合并完成: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"音视频合并失败: {str(e)}")
        raise
    finally:
        # 确保资源释放
        if 'video' in locals():
            video.close()
        if 'audio' in locals():
            audio.close()
        if 'final_clip' in locals():
            final_clip.close()


def combine_videos(video_paths: List[Path], task_dir: Path) -> Path:
    """合并所有视频片段"""
    try:
        logger.info("开始合并最终视频...")
        clips = []

        # 加载所有片段
        for path in video_paths:
            clip = VideoFileClip(str(path))
            clips.append(clip)

        # 合并视频
        final_clip = concatenate_videoclips(clips, method="compose")
        output_path = task_dir / "final_output.mp4"

        # 写入文件
        final_clip.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            threads=4,
            verbose=False,
            logger=None
        )

        logger.info(f"最终视频已生成: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"视频合并失败: {str(e)}")
        raise
    finally:
        # 确保资源释放
        for clip in clips:
            clip.close()
        if 'final_clip' in locals():
            final_clip.close()


# 建议的配置项（app/config/settings.py）
"""
# 视频生成配置
VIDEO_GENERATION_MODEL_EP = "ep-xxxxxx"  # 模型接入点
VIDEO_GENERATION_TIMEOUT = 600  # 秒
POLLING_INTERVAL = 5  # 秒

# TTS配置
TTS_API_ENDPOINT = "https://openspeech.bytedance.com/api/v1/tts"
TTS_VOICE_TYPE = "zh_male_M392_conversation_wvae_bigtts"
TTS_TIMEOUT = 30  # 秒

# 重试策略
MAX_RETRIES = 3
"""

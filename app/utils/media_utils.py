from moviepy.editor import *
import logging


def adjust_audio_duration(audio_path: str, target_duration: float) -> str:
    """调整音频时长适配视频"""
    try:
        audio = AudioFileClip(audio_path)
        if audio.duration < target_duration:
            # 添加静音填充
            silence = AudioClip(lambda t: [0, 0], duration=target_duration - audio.duration)
            new_audio = CompositeAudioClip([audio, silence.set_start(audio.duration)])
        else:
            new_audio = audio.subclip(0, target_duration)

        output_path = audio_path.replace(".mp3", "_adjusted.mp3")
        new_audio.write_audiofile(output_path)
        return output_path
    except Exception as e:
        logging.error(f"音频处理失败: {str(e)}")
        return audio_path
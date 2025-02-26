import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")  # 阿里云API Key
    DEEPSEEK_MODEL = "deepseek-v3"  # 指定模型版本

    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    VOLCANO_AK = os.getenv("VOLCANO_ACCESS_KEY")
    VOLCANO_SK = os.getenv("VOLCANO_SECRET_KEY")
    TTS_API_KEY = os.getenv("TTS_API_KEY")
    DOUYIN_TOKEN = os.getenv("DOUYIN_ACCESS_TOKEN")

    DEEPSEEK_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    VOLCANO_IMAGE_SERVICE = "cv"  # 文生图服务标识
    VOLCANO_VIDEO_URL = "https://open.volcengineapi.com/vod/v1/video_ai/gen"
    DOUYIN_UPLOAD_URL = "https://open.douyin.com/api/v2/video/upload/"

    # TTS 相关配置
    APPID = os.getenv("APPID")  # 新增 APPID 配置
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")  # 新增 ACCESS_TOKEN 配置
    TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"  # 修改 TTS 请求 URL

    VIDEO_GENERATION_API_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
    VIDEO_GENERATION_API_QUERY_URL = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/{}"
    VIDEO_GENERATION_MODEL_EP = os.getenv("VIDEO_GENERATION_MODEL_EP")


settings = Settings()
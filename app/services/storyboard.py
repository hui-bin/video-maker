import json
from app.schemas import SceneScript
from app.utils.api_clients import deepseek_request


def generate_scenes(content: str) -> list[SceneScript]:
    prompt = f"""请将以下内容转换为6个视频分镜（JSON数组格式）：
    {content}

    每个分镜需要包含：
    - description: 画面描述（40字左右，具体包含场景、人物动作、镜头角度）
    - narration: 解说文案（50字左右，口语化表达）

    示例格式：
    [
        {{"description": "航拍城市全景，镜头缓缓推近到写字楼", "narration": "在快节奏的现代都市中，人们每天都在面临新的挑战"}},
        {{"description": "办公室内景，白领在电脑前皱眉查看数据", "narration": "据统计，超过60%的上班族表示工作压力主要来自..."}}
    ]"""

    try:
        result = deepseek_request(prompt)
        # 处理可能的markdown代码块
        cleaned_result = result.replace("```json", "").replace("```", "").strip()
        scenes = json.loads(cleaned_result)
        return [SceneScript(**s) for s in scenes]
    except json.JSONDecodeError as e:
        raise ValueError(f"分镜解析失败：{str(e)}\n原始响应：{result}")
    except Exception as e:
        raise ValueError("分镜生成失败：" + str(e))
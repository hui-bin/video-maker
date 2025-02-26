import os
import logging
import base64
import requests
from volcenginesdkarkruntime import Ark

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 检查并获取 API Key

client = Ark(api_key=api_key)

# 初始化客户端
def encode_image_to_base64(image_path):
    """
    将图片编码为 Base64 字符串
    :param image_path: 图片路径
    :return: Base64 编码的图片字符串
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        logging.error(f"图片编码为 Base64 失败: {e}")
        raise

def create_video_generation_task(model_id, text_prompt, image_base64):
    """
    创建视频生成任务
    :param model_id: 推理接入点 ID
    :param text_prompt: 文本提示词
    :param image_base64: Base64 编码的图片
    :return: 创建任务的结果
    """
    try:
        logging.info("正在创建视频生成任务...")
        create_result = client.content_generation.tasks.create(
            model=model_id,
            content=[
                {
                    "type": "text",
                    "text": text_prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_base64
                    }
                }
            ]
        )
        logging.info(f"视频生成任务创建成功，任务 ID: {create_result.id}")
        return create_result
    except Exception as e:
        logging.error(f"创建视频生成任务失败: {e}")
        raise

def get_video_generation_task(task_id):
    """
    获取视频生成任务信息
    :param task_id: 任务 ID
    :return: 任务信息
    """
    try:
        logging.info(f"正在获取任务 {task_id} 的信息...")
        get_result = client.content_generation.tasks.get(task_id=task_id)
        logging.info(f"成功获取任务 {task_id} 的信息: {get_result}")
        return get_result
    except Exception as e:
        logging.error(f"获取任务 {task_id} 的信息失败: {e}")
        raise

def list_video_generation_tasks(page_num, page_size, status=None, model=None, task_ids=None):
    """
    列出视频生成任务列表
    :param page_num: 页码
    :param page_size: 每页数据量
    :param status: 任务状态
    :param model: 推理接入点 ID
    :param task_ids: 任务 ID 列表
    :return: 任务列表
    """
    try:
        logging.info("正在列出视频生成任务列表...")
        params = {
            "page_num": page_num,
            "page_size": page_size
        }
        if status:
            params["status"] = status
        if model:
            params["model"] = model
        if task_ids:
            params["task_ids"] = task_ids
        list_result = client.content_generation.tasks.list(**params)
        logging.info(f"成功列出视频生成任务列表: {list_result}")
        return list_result
    except Exception as e:
        logging.error(f"列出视频生成任务列表失败: {e}")
        raise

def delete_video_generation_task(task_id):
    """
    删除视频生成任务
    :param task_id: 任务 ID
    """
    try:
        logging.info(f"正在删除任务 {task_id}...")
        client.content_generation.tasks.delete(task_id=task_id)
        logging.info(f"任务 {task_id} 删除成功")
    except Exception as e:
        logging.error(f"删除任务 {task_id} 失败: {e}")
        raise

def download_video(video_url, save_path):
    """
    下载视频到本地
    :param video_url: 视频下载 URL
    :param save_path: 保存路径
    """
    try:
        logging.info(f"正在从 {video_url} 下载视频到 {save_path}...")
        response = requests.get(video_url)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        logging.info(f"视频下载成功，保存到 {save_path}")
    except Exception as e:
        logging.error(f"视频下载失败: {e}")
        raise

MAX_RETRIES = 3

if __name__ == "__main__":
    # 配置参数
    model_id = "ep-20250225213834-pgc9c"
    text_prompt = "龙与地下城女骑士背景是起伏的平原，目光从镜头转向平原"
    image_path = "../../test/2.png"
    if not os.path.exists(image_path):
        logging.error(f"未找到图片文件 {image_path}")
        raise FileNotFoundError(f"未找到图片文件 {image_path}")
    image_base64 = encode_image_to_base64(image_path)

    retries = 0
    while retries < MAX_RETRIES:
        # 创建任务
        create_result = create_video_generation_task(model_id, text_prompt, image_base64)

        # 等待任务完成
        import time
        while True:
            task_info = get_video_generation_task(create_result.id)
            if task_info.status == 'succeeded':
                break
            elif task_info.status == 'failed':
                logging.error(f"任务 {create_result.id} 失败: {task_info.error}")
                break
            time.sleep(5)  # 每 5 秒检查一次任务状态

        if task_info.status == 'succeeded':
            # 下载视频
            print(f"task_info: {task_info}")
            video_url = task_info.content.video_url  # 修改此处
            if video_url:
                save_path = "../../test/generated_video.mp4"
                download_video(video_url, save_path)
            break
        else:
            retries += 1
            if retries < MAX_RETRIES:
                logging.info(f"任务失败，正在进行第 {retries + 1} 次重试...")
            else:
                logging.error("达到最大重试次数，任务仍然失败。")

    # 列出任务列表
    list_result = list_video_generation_tasks(page_num=1, page_size=10, status="queued")

    # 删除任务
    if create_result:
        delete_video_generation_task(create_result.id)
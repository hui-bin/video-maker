import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks
from fastapi import HTTPException

from app.schemas import VideoRequest

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI()
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "tmp"

# 初始化服务模块
from app.services import (
    content,
    storyboard,
    image_gen,
    video_gen,
    publisher
)


@app.post("/create_video")
async def create_video(
        request: VideoRequest,
        background_tasks: BackgroundTasks
):
    task_id = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    os.makedirs(task_dir, exist_ok=True)

    background_tasks.add_task(_process_video, request, task_dir)
    return {"task_id": task_id}


@app.post("/process_content")
async def process_content(request: VideoRequest):
    task_id = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    os.makedirs(task_dir, exist_ok=True)

    try:
        logging.info(f"开始文案扩写")
        processed_content = content.process_input(
            request.input_content,
            request.is_url
        )
        logging.info(f"内容处理完成，长度：{len(processed_content)}字符")
        logging.info(f"扩展的内容是：{(processed_content)}")
        return {"processed_content": processed_content, "task_dir": str(task_dir)}
    except Exception as e:
        logging.error(f"内容处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail="内容处理失败")


@app.post("/generate_scenes")
async def generate_scenes(request: VideoRequest, task_dir: str):
    task_dir = Path(task_dir)
    try:
        logging.info(f"开始执行分镜生成")
        processed_content = content.process_input(
            request.input_content,
            request.is_url
        )
        scenes = storyboard.generate_scenes(processed_content)
        logging.info(f"分镜描述是：{(scenes)}")
        return {"scenes": [scene.dict() for scene in scenes], "task_dir": str(task_dir)}
    except Exception as e:
        logging.error(f"分镜生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail="分镜生成失败")


image_generator = image_gen.ImageGenerator()


@app.post("/generate_images")
async def generate_images(scenes: list, task_dir: str):
    task_dir = Path(task_dir)
    try:
        logging.info(f"开始执行图片生成")
        image_paths = image_generator.generate_images(scenes, task_dir)
        return {"image_paths": [str(path) for path in image_paths], "task_dir": str(task_dir)}
    except Exception as e:
        logging.error(f"图片生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail="图片生成失败")


@app.post("/generate_videos")
async def generate_videos(scenes: list, image_paths: list, task_dir: str):
    task_dir = Path(task_dir)
    # try:
    logging.info(f"开始执行视频生成")
    video_paths = video_gen.generate_videos(scenes, image_paths, task_dir)
    return {"video_paths": [str(path) for path in video_paths], "task_dir": str(task_dir)}
    # except Exception as e:
    #     logging.error(f"视频生成失败: {str(e)}")
    #     raise HTTPException(status_code=500, detail="视频生成失败")


@app.post("/combine_videos")
async def combine_videos(video_paths: list, task_dir: str):
    task_dir = Path(task_dir)
    try:
        logging.info(f"开始执行视频合并")
        final_path = video_gen.combine_videos(video_paths, task_dir)
        return {"final_path": str(final_path), "task_dir": str(task_dir)}
    except Exception as e:
        logging.error(f"视频合并失败: {str(e)}")
        raise HTTPException(status_code=500, detail="视频合并失败")


@app.post("/publish_video")
async def publish_video(final_path: str, schedule_time: str = None):
    final_path = Path(final_path)
    try:
        logging.info(f"开始执行视频发布")
        if final_path.exists():
            response = publisher.publish_video(final_path, schedule_time)
            return response
        else:
            raise Exception("最终视频文件生成失败")
    except Exception as e:
        logging.error(f"视频发布失败: {str(e)}")
        raise HTTPException(status_code=500, detail="视频发布失败")


async def _process_video(request: VideoRequest, task_dir: Path):
    try:
        # 记录任务开始
        logging.info(f"开始处理任务 {task_dir.name}")

        # 1. 内容处理
        # content_response = await process_content(request)  # 使用 await 获取结果
        # processed_content = content_response["processed_content"]
        # logging.info(f"文案扩写结果 {processed_content}")

        # 2. 分镜生成
        scenes_response = await generate_scenes(request, str(task_dir))  # 使用 await 获取结果
        scenes = scenes_response["scenes"]
        logging.info(f"分镜结果： {scenes}，文件路径：{str(task_dir)}")

        # scenes = [
        #     {
        #         "description": "航拍城市夜景，镜头聚焦到写字楼窗口内年轻白领加班场景",
        #         "narration": "在繁华都市的深夜，一盏盏灯光下是奋斗者的身影。白象方便面，用温暖陪伴每一个追梦人"
        #     },
        #     {
        #         "description": "特写镜头：年轻白领打开白象方便面，热气缓缓升起",
        #         "narration": "一碗热气腾腾的白象方便面，既是深夜的美味，也是疲惫时最好的慰藉。这就是白象，懂你的每一份需求"
        #     },
        #     {
        #         "description": "工厂全景，镜头推进展示现代化生产线，工人们认真工作",
        #         "narration": "作为中国民族品牌，白象始终秉持高标准、严要求。每一碗面都凝聚着我们的匠心与承诺"
        #     },
        #     {
        #         "description": "特写镜头：大骨熬制过程，汤色浓郁，配料新鲜",
        #         "narration": "精选优质大骨，经过6小时慢火熬制，这是白象大骨面的制胜秘诀。无添加，更健康，让您吃得放心"
        #     },
        #     {
        #         "description": "超市货架前，年轻人选购白象方便面，面带微笑",
        #         "narration": "2022年，白象方便面销量增长超30%，越来越多的年轻人选择国货，选择白象。这是品牌的力量，更是民族自信的体现"
        #     },
        #     {
        #         "description": "品牌logo特写，配以国货当自强字样，画面渐隐",
        #         "narration": "白象，用行动诠释国货担当。未来，我们将继续坚持品质与创新，为消费者带来更多美味与温暖"
        #     }
        # ]

        # 3. 图片生成
        image_paths_response = await generate_images(scenes, str(task_dir))  # 使用 await 获取结果
        image_paths = image_paths_response["image_paths"]
        logging.info(f"图片生成路径结果 {image_paths}")
        logging.info(f"分镜结果： {scenes}，文件路径：{str(task_dir)}")
        # task_dir = "/Users/bink/xin/code/python/video-maker/tmp/f716c386-c09f-46a0-acb5-0fafab8536cd"
        # image_paths=['/Users/bink/xin/code/python/video-maker/tmp/f716c386-c09f-46a0-acb5-0fafab8536cd/scene_0.jpg',
        #  '/Users/bink/xin/code/python/video-maker/tmp/f716c386-c09f-46a0-acb5-0fafab8536cd/scene_1.jpg',
        #  '/Users/bink/xin/code/python/video-maker/tmp/f716c386-c09f-46a0-acb5-0fafab8536cd/scene_2.jpg',
        #  '/Users/bink/xin/code/python/video-maker/tmp/f716c386-c09f-46a0-acb5-0fafab8536cd/scene_3.jpg',
        #  '/Users/bink/xin/code/python/video-maker/tmp/f716c386-c09f-46a0-acb5-0fafab8536cd/scene_4.jpg',
        #  '/Users/bink/xin/code/python/video-maker/tmp/f716c386-c09f-46a0-acb5-0fafab8536cd/scene_5.jpg']
        # 4. 视频生成
        video_paths_response = await generate_videos(scenes, image_paths, str(task_dir))  # 使用 await 获取结果
        video_paths = video_paths_response["video_paths"]
        logging.info(f"视频生成结果 {video_paths}")

        # 5. 视频合成
        final_path_response = await combine_videos(video_paths, str(task_dir))  # 使用 await 获取结果
        final_path = final_path_response["final_path"]
        logging.info(f"视频合成结果 {final_path}")

        # 6. 发布
        # publish_response = await publish_video(final_path, request.schedule_time)  # 使用 await 获取结果

        # 清理临时文件（可选）
        # shutil.rmtree(task_dir)

        return final_path

    except Exception as e:
        logging.error(f"任务失败：{str(e)}", exc_info=True)
        # 可以添加邮件/通知等错误处理逻辑
        # raise  # 保持异常传播

# 添加以下代码，使文件可以直接运行
if __name__ == "__main__":
    import uvicorn
    
    # 确保tmp目录存在
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # 打印启动信息
    print(f"启动服务器...")
    print(f"API文档可在 http://127.0.0.1:8000/docs 访问")
    print(f"临时文件将保存在 {TEMP_DIR}")
    
    # 启动服务器
    uvicorn.run(app, host="0.0.0.0", port=8000)

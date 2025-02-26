import os
import logging
from pathlib import Path
from volcengine.visual.VisualService import VisualService
from app.config import settings
from app.schemas import SceneScript
import requests
logger = logging.getLogger(__name__)


class ImageGenerator:
    def __init__(self):
        self.service = VisualService()
        self._setup_credentials()

    def _setup_credentials(self):
        """配置火山引擎认证信息"""
        self.service.set_ak(settings.VOLCANO_AK)
        self.service.set_sk(settings.VOLCANO_SK)

    def generate_images(self, scenes, output_dir):
        image_paths = []
        for idx, scene in enumerate(scenes):
            try:
                img_path = self._generate_single_image(scene, output_dir, idx)
                image_paths.append(img_path)
            except Exception as e:
                print(f"图片生成失败: {e}")
                # 可以根据业务需求添加重试逻辑或其他处理
        return image_paths

    def _generate_single_image(self, scene: SceneScript, output_dir: Path, index: int) -> Path:
        """生成单个分镜图片"""
        try:
            # 构建请求参数
            form = {
                "req_key": "high_aes_general_v21_L",
                "prompt": f'"{scene["description"]}"',
                "model_version": "general_v2.1_L",
                "width": 384,
                "height": 512,
                "use_sr": True,
                "return_url": True,
                "req_schedule_conf": "general_v20_9B_pe",
                "logo_info": {
                    "add_logo": True,
                    "position": 0,
                    "language": 0,
                    "opacity": 0.2
                }
            }

            # 调用同步接口
            response = self.service.cv_process(form)
            # try:
            #     res_json = json.loads(response)
            #     if res_json.get("status") != 200:
            #         raise Exception(f'图片审核未通过: {res_json.get("message")}')
            # except json.JSONDecodeError:
            #     raise Exception(f'响应内容不是有效的 JSON 格式: {response}')
            #     # 处理成功响应
            # img_path = os.path.join(output_dir, f"scene_{idx + 1}.jpg")
            # # 保存图片逻辑
            # with open(img_path, 'wb') as f:
            #     # 写入图片数据
            #     pass
            # print(f"成功生成分镜{idx + 1}图片: {img_path}")
            # return img_path

            # 处理响应
            if response["code"] != 10000:
                raise ValueError(f'API错误: {response.get("message", "未知错误")}')

            if not response["data"].get("image_urls"):
                raise ValueError("未返回有效图片URL")

            # 下载图片
            img_url = response["data"]["image_urls"][0]
            img_data = requests.get(img_url, timeout=15).content

            # 保存文件
            img_path = output_dir / f"scene_{index}.jpg"
            with open(img_path, "wb") as f:
                f.write(img_data)

            logger.info(f"成功生成分镜{index}图片: {img_path}")
            return img_path

        except requests.exceptions.RequestException as e:
            logger.error(f"分镜{index}下载失败: {str(e)}")
            raise
        except KeyError as e:
            logger.error(f"响应格式错误: {str(e)}")
            raise ValueError("无效的API响应格式")
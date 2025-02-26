import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.utils.api_clients import deepseek_request

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def process_input(content: str, is_url: bool) -> str:
    try:
        if is_url:
            result = _summarize_website(content)
        else:
            result = _expand_topic(content)

        # 验证结果长度
        if len(result) < 100:
            raise ValueError("生成内容过短，可能未成功")

        return result
    except Exception as e:
        logger.error(f"内容处理失败: {str(e)}")
        raise


def _summarize_website(url: str) -> str:
    prompt = f"""请严格按照以下要求处理：
    1. 用中文总结新闻内容
    2. 保留关键事实和数据
    3. 输出长度在300-500字之间
    原始内容来源：{url}"""

    return deepseek_request(prompt)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(ConnectionError)
)
def _expand_topic(topic: str) -> str:
    prompt = f"""请按照以下要求扩写主题：
    1. 使用自然流畅的中文
    2. 包含具体案例或数据支撑
    3. 结构清晰（引言-论点-结论）
    4. 输出约500字
    主题：{topic}"""

    return deepseek_request(prompt)
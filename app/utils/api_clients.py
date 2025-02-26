import requests
import json
import hmac
import hashlib
from datetime import datetime
from app.config import settings
from openai import OpenAI


def deepseek_request(prompt: str) -> str:
    client = OpenAI(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DEEPSEEK_URL
    )

    try:
        completion = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        # # 阿里云返回结构处理
        # if hasattr(completion.choices[0].message, 'reasoning_content'):
        #     print(f"[DEBUG] 思考过程: {completion.choices[0].message.reasoning_content}")

        return completion.choices[0].message.content

    except Exception as e:
        error_msg = f"DeepSeek API请求失败: {str(e)}"
        if hasattr(e, 'response'):
            error_msg += f"\n响应状态码: {e.response.status_code}"
            error_msg += f"\n响应内容: {e.response.text}"
        raise ConnectionError(error_msg) from e


def volcano_sign_request(method: str, path: str, params: dict, service: str = "cv") -> dict:
    """火山引擎V4签名（返回字典headers）"""
    region = "cn-north-1"
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # 根据服务类型选择host
    host_map = {
        "cv": "visual.volcengineapi.com",
        "imagex": "open.volcengineapi.com"
    }
    host = host_map.get(service, "open.volcengineapi.com")

    # 规范请求参数
    signed_headers = "content-type;host;x-date"
    canonical_headers = f"content-type:application/json\nhost:{host}\nx-date:{timestamp}\n"

    # 处理查询参数
    query_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    canonical_uri = f"{path}?{query_str}" if query_str else path

    # 构建规范请求
    canonical_request = "\n".join([
        method.upper(),
        canonical_uri,
        "",
        canonical_headers,
        signed_headers,
        "UNSIGNED-PAYLOAD"
    ])

    # 生成签名
    string_to_sign = "\n".join([
        "HMAC-SHA256",
        timestamp,
        f"{service}/{region}/request",
        hashlib.sha256(canonical_request.encode()).hexdigest()
    ])

    signing_key = hmac.new(
        settings.VOLCANO_SK.encode(),
        timestamp[:8].encode(),
        hashlib.sha256
    ).digest()

    signature = hmac.new(
        signing_key,
        string_to_sign.encode(),
        hashlib.sha256
    ).hexdigest()

    return {
        "X-Date": timestamp,
        "Authorization": f"HMAC-SHA256 Credential={settings.VOLCANO_AK}/{timestamp[:8]}/{region}/{service}/request, SignedHeaders={signed_headers}, Signature={signature}",
        "Content-Type": "application/json"
    }
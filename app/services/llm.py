"""DeepSeek 大模型网关（BACKEND_SPEC §6.3）：

- JSON 模式：response_format=json_object + thinking disabled
- 解析容错：正则提取首个 {...} 再反序列化（模型可能包裹 markdown 代码块）
- 超时控制：默认 30s（§4 导语）
- 失败统一抛 LLMError → 上层规则引擎兜底，接口永远 200（§4.5）
"""
import json
import re

from openai import OpenAI

from app.config import settings


class LLMError(Exception):
    """大模型调用失败（未配置 Key / 超时 / 5xx / 输出解析失败），触发规则降级"""


def _client() -> OpenAI:
    if not settings.deepseek_api_key:
        raise LLMError("未配置 DEEPSEEK_API_KEY")
    # DeepSeek 兼容 OpenAI SDK，base_url 指向 https://api.deepseek.com 即可
    return OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        timeout=settings.llm_timeout_s,
        max_retries=0,  # 重试策略由上层兜底逻辑接管，避免重复扣费
    )


def extract_json(content: str) -> dict:
    """从模型输出中提取首个 JSON 对象（兼容 markdown 包裹与前后多余文本）"""
    m = re.search(r"\{[\s\S]*\}", content or "")
    if not m:
        raise LLMError("模型输出中未找到 JSON")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise LLMError(f"JSON 反序列化失败: {e}")


def chat_json(system_prompt: str, user_prompt: str, *, temperature: float = 0.7, max_tokens: int = 1000) -> dict:
    """调用 DeepSeek chat/completions，返回解析后的 JSON dict；任何失败都抛 LLMError"""
    try:
        resp = _client().chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            extra_body={"thinking": {"type": "disabled"}},  # DeepSeek 私有参数，对齐前端 §4 导语
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        content = resp.choices[0].message.content
    except LLMError:
        raise
    except Exception as e:  # 超时 / 网络 / 4xx / 5xx 统一归一
        raise LLMError(f"DeepSeek 调用失败: {e}")
    return extract_json(content)

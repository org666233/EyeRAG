"""
LLM 客户端封装（含自动重试）
支持双 Provider：
  - DeepSeek  (OpenAI 兼容接口)
  - MiniMax   (Anthropic SDK 兼容接口)

切换：修改 .env 中 LLM_PROVIDER=deepseek 或 LLM_PROVIDER=minimax

重试策略（适用于全部 generate / stream 调用）：
  - HTTP 429 / 500 / 502 / 503 / 529 → 指数退避重试，最多 MAX_RETRIES 次
  - 连接超时 / 网络断开 → 同上
  - 其他 4xx 错误 → 直接抛出，不重试
"""

import asyncio
from typing import AsyncGenerator, Optional
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()

# ── 重试配置 ───────────────────────────────────────────────────────────────────
MAX_RETRIES  = 5     # 最大重试次数
BASE_DELAY   = 15.0  # 首次等待秒数（后续翻倍：15 → 30 → 60 → 120 → 240）
RETRYABLE_STATUS = {429, 500, 502, 503, 529}

# ── 客户端单例 ─────────────────────────────────────────────────────────────────
_openai_client    = None
_anthropic_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        if not settings.llm_api_key:
            logger.warning("⚠️  LLM_API_KEY 未配置")
        _openai_client = AsyncOpenAI(
            api_key=settings.llm_api_key or "sk-placeholder",
            base_url=settings.llm_api_base_url,
        )
        logger.info(f"✅ DeepSeek 客户端初始化: {settings.llm_api_base_url} / {settings.llm_model_name}")
    return _openai_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("使用 MiniMax 需安装 anthropic 库：pip install anthropic")
        if not settings.minimax_api_key:
            logger.warning("⚠️  MINIMAX_API_KEY 未配置")
        _anthropic_client = anthropic.AsyncAnthropic(
            api_key=settings.minimax_api_key or "sk-placeholder",
            base_url=settings.minimax_api_base_url,
        )
        logger.info(f"✅ MiniMax 客户端初始化: {settings.minimax_api_base_url} / {settings.minimax_model_name}")
    return _anthropic_client


# ── 统一重试包装器 ────────────────────────────────────────────────────────────

def _is_retryable(exc: Exception) -> tuple[bool, int]:
    """
    判断异常是否可重试，返回 (retryable, status_code)。
    优先用 status_code 属性判断，避免依赖具体子类名称
    （新版 Anthropic SDK 的 529 抛 OverloadedError 而非 APIStatusError）。
    """
    # 直接从异常取 HTTP 状态码（Anthropic / OpenAI SDK 均有此属性）
    status = getattr(exc, "status_code", None)
    if status is not None:
        return status in RETRYABLE_STATUS, status

    exc_type = type(exc).__name__
    exc_module = type(exc).__module__ or ""

    # Anthropic SDK 按名称兜底
    if any(k in exc_type for k in ("RateLimitError", "APITimeoutError",
                                    "APIConnectionError", "OverloadedError",
                                    "InternalServerError")):
        return True, 0
    # OpenAI 兼容
    if "openai" in exc_module and any(k in exc_type for k in ("RateLimit", "Timeout", "Connection")):
        return True, 0
    # 通用网络错误
    if any(k in exc_type for k in ("Timeout", "Connection", "Network")):
        return True, 0

    return False, 0


async def _retry(coro_factory, label: str = "LLM"):
    """
    对一个 async 调用做指数退避重试。
    coro_factory: 无参 callable，每次调用返回新的 coroutine。
    """
    last_exc: Exception = RuntimeError("未执行")
    for attempt in range(MAX_RETRIES):
        try:
            return await coro_factory()

        except Exception as exc:
            retryable, status = _is_retryable(exc)
            if not retryable:
                raise  # 不可重试（如 400 参数错误），直接抛出

            last_exc = exc
            delay = BASE_DELAY * (2 ** attempt)
            status_str = f"HTTP {status}" if status else type(exc).__name__
            logger.warning(
                f"{label}: {status_str} → 第 {attempt+1}/{MAX_RETRIES} 次重试，"
                f"等待 {delay:.0f}s ..."
            )
            await asyncio.sleep(delay)

    raise RuntimeError(f"{label}: 已达最大重试次数 {MAX_RETRIES}，最后错误: {last_exc}")


# ── 消息格式转换（OpenAI → Anthropic）────────────────────────────────────────

def _to_anthropic_format(messages: list[dict]) -> tuple[str, list[dict]]:
    system_prompt = ""
    user_messages: list[dict] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_prompt = msg.get("content", "")
        else:
            user_messages.append({"role": msg["role"], "content": msg.get("content", "")})
    return system_prompt, user_messages


# ── 同步生成 ──────────────────────────────────────────────────────────────────

async def generate(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: Optional[str] = None,
) -> str:
    provider = settings.llm_provider.lower()
    if provider == "minimax":
        return await _generate_minimax(messages, temperature, max_tokens, model)
    return await _generate_deepseek(messages, temperature, max_tokens, model)


async def _generate_deepseek(messages, temperature, max_tokens, model):
    client = _get_openai_client()
    model_name = model or settings.llm_model_name

    async def _call():
        response = await client.chat.completions.create(
            model=model_name, messages=messages,
            temperature=temperature, max_tokens=max_tokens, stream=False,
        )
        content = response.choices[0].message.content or ""
        logger.info(f"DeepSeek 生成完成: {len(content)} 字符")
        return content

    return await _retry(_call, label="DeepSeek generate")


async def _generate_minimax(messages, temperature, max_tokens, model):
    client = _get_anthropic_client()
    model_name = model or settings.minimax_model_name
    system_prompt, user_messages = _to_anthropic_format(messages)

    async def _call():
        response = await client.messages.create(
            model=model_name, max_tokens=max_tokens,
            temperature=temperature, system=system_prompt,
            messages=user_messages,
        )
        # MiniMax 可能包含 ThinkingBlock，只取第一个 TextBlock
        content = next((b.text for b in response.content if b.type == "text"), "")
        logger.info(f"MiniMax 生成完成: {len(content)} 字符")
        return content

    return await _retry(_call, label="MiniMax generate")


# ── 流式生成 ──────────────────────────────────────────────────────────────────

async def generate_stream(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    provider = settings.llm_provider.lower()
    if provider == "minimax":
        async for chunk in _stream_minimax(messages, temperature, max_tokens, model):
            yield chunk
    else:
        async for chunk in _stream_deepseek(messages, temperature, max_tokens, model):
            yield chunk


async def _stream_deepseek(messages, temperature, max_tokens, model):
    client = _get_openai_client()
    model_name = model or settings.llm_model_name
    try:
        stream = await client.chat.completions.create(
            model=model_name, messages=messages,
            temperature=temperature, max_tokens=max_tokens, stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"DeepSeek 流式生成失败: {e}")
        yield f"\n\n[错误: DeepSeek API 调用失败 - {str(e)}]"


async def _stream_minimax(messages, temperature, max_tokens, model):
    client = _get_anthropic_client()
    model_name = model or settings.minimax_model_name
    system_prompt, user_messages = _to_anthropic_format(messages)
    try:
        async with client.messages.stream(
            model=model_name, max_tokens=max_tokens,
            temperature=temperature, system=system_prompt,
            messages=user_messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
    except Exception as e:
        logger.error(f"MiniMax 流式生成失败: {e}")
        yield f"\n\n[错误: MiniMax API 调用失败 - {str(e)}]"


def get_llm_client():
    if settings.llm_provider.lower() == "minimax":
        return _get_anthropic_client()
    return _get_openai_client()

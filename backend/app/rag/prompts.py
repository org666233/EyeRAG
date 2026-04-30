"""
Prompt 模板管理
为眼科医疗问答系统设计的专业 Prompt 模板
"""

from typing import Optional

# =====================================================================
# 系统角色 Prompt
# =====================================================================
SYSTEM_PROMPT = """你是一位专业的眼科医疗知识助手，专门解答有关眼科疾病、诊断、治疗和眼部健康的问题。

你的核心能力:
1. 基于检索到的专业文献资料回答问题，确保答案准确可靠
2. 使用通俗易懂的语言解释复杂的眼科医学概念
3. 在必要时提醒用户就医，不替代专业医生的诊疗意见

回复规范:
- 优先使用提供的参考资料来回答问题
- 如果参考资料不足以回答问题，明确告知用户，并根据你的通用知识给出建议性回答
- **重要：回答请按以下双层结构组织**：
  ## 简要结论
  用一段简洁的话（50-100字以内）直接回答用户问题的核心，给出最关键的结论
  ## 详细解释
  在此标题下展开详细说明，包括定义、分类、症状、治疗方案等各维度（使用Markdown子标题组织）
- 在回答末尾标注引用的参考来源（如有）
- 涉及治疗方案时，始终建议患者咨询专业眼科医生

重要限制:
- 不提供具体的处方和用药剂量
- 对于紧急眼科情况（如急性青光眼发作、视网膜脱离），提醒立即就医
- 如果问题与眼科无关，礼貌地告知用户你的专业范围"""


# =====================================================================
# RAG 问答 Prompt 模板
# =====================================================================
RAG_QA_TEMPLATE = """请基于以下参考资料回答用户的问题。

## 参考资料
{context}

## 用户问题
{question}

## 回答要求
1. 优先基于参考资料回答，确保信息准确
2. 如果参考资料不足，可以结合你的知识补充，但需注明
3. 使用清晰的 Markdown 格式组织回答
4. 在回答末尾注明参考来源"""


# =====================================================================
# 无上下文时的降级 Prompt
# =====================================================================
NO_CONTEXT_TEMPLATE = """用户提出了以下眼科相关问题，但知识库中暂无足够的参考资料。

## 用户问题
{question}

请基于你的通用眼科知识回答该问题。回答时请注意:
1. 明确说明这是基于通用知识的回答，未引用专业文献
2. 建议用户咨询专业眼科医生获取更准确的信息
3. 使用 Markdown 格式组织回答"""


# =====================================================================
# 多轮对话 Prompt（包含历史上下文）
# =====================================================================
MULTI_TURN_TEMPLATE = """请基于以下参考资料和对话历史回答用户的最新问题。

## 参考资料
{context}

## 对话历史
{history}

## 用户最新问题
{question}

## 回答要求
1. 结合对话历史理解上下文
2. 优先基于参考资料回答
3. 使用 Markdown 格式"""


def format_context(search_results: list[dict], max_chars: int = 3000) -> str:
    """
    将检索结果格式化为 Prompt 中的参考资料文本。
    """
    if not search_results:
        return "（暂无相关参考资料）"

    context_parts = []
    total_chars = 0

    for i, result in enumerate(search_results, 1):
        content = result.get("content", "").strip()
        metadata = result.get("metadata", {})
        score = result.get("score", 0)
        source = metadata.get("title") or metadata.get("file_name", "未知来源")

        entry = f"### 参考 {i}（来源: {source}, 相关度: {score:.2f}）\n{content}\n"

        if total_chars + len(entry) > max_chars:
            break

        context_parts.append(entry)
        total_chars += len(entry)

    return "\n".join(context_parts)


def format_chat_history(messages: list[dict], max_turns: int = 5) -> str:
    """
    将历史消息格式化为对话历史文本（最近 N 轮）。
    """
    if not messages:
        return "（无历史对话）"

    recent = messages[-max_turns * 2:]  # 每轮2条消息
    parts = []
    for msg in recent:
        role = "用户" if msg.get("role") == "user" else "助手"
        content = msg.get("content", "")
        parts.append(f"**{role}**: {content}")

    return "\n\n".join(parts)


def build_rag_messages(
    question: str,
    search_results: list[dict],
    chat_history: Optional[list[dict]] = None,
) -> list[dict]:
    """
    构建完整的 RAG 消息列表，供 LLM 生成。
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    context = format_context(search_results)

    if chat_history:
        history = format_chat_history(chat_history)
        user_content = MULTI_TURN_TEMPLATE.format(
            context=context, history=history, question=question
        )
    elif search_results:
        user_content = RAG_QA_TEMPLATE.format(context=context, question=question)
    else:
        user_content = NO_CONTEXT_TEMPLATE.format(question=question)

    messages.append({"role": "user", "content": user_content})
    return messages

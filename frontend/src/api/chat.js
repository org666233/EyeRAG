/**
 * 聊天 API 模块
 * 支持: SSE 流式请求、会话管理
 */

import request from '@/utils/request'
import { getToken } from '@/api/auth.js'

const BASE = '/chat'

/**
 * 保存消息接口（流结束后显式调用）
 */
export function saveMessages(payload) {
    return request.post(`${BASE}/messages`, payload)
}

/**
 * 发送聊天消息（SSE 流式）
 * 返回 controller（可调用 controller.abort() 取消请求）
 */
export function sendMessageStream(data, { onContent, onSources, onRelated, onDone, onError }) {
    const controller = new AbortController()
    const token = getToken()

    fetch('/api/chat/completions', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ ...data, stream: true }),
        signal: controller.signal,
    })
        .then(async (response) => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`)

            const reader = response.body.getReader()
            const decoder = new TextDecoder()
            let buffer = ''

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                buffer += decoder.decode(value, { stream: true })
                const lines = buffer.split('\n')
                buffer = lines.pop() || ''

                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue
                    try {
                        const payload = JSON.parse(line.slice(6))
                        if (payload.type === 'content' && onContent) {
                            onContent(payload.content)
                        } else if (payload.type === 'sources' && onSources) {
                            onSources(
                                payload.sources,
                                payload.conversation_id,
                                payload.retrieval_decision,
                                payload.search_results,
                                payload.context_count,
                            )
                        } else if (payload.type === 'related' && onRelated) {
                            onRelated(payload.questions)
                        } else if (payload.type === 'done' && onDone) {
                            onDone(payload.content, payload.response_time_ms)
                        }
                    } catch (_) {}
                }
            }
        })
        .catch((err) => {
            if (err.name !== 'AbortError' && onError) onError(err)
        })

    return controller
}

/** 获取会话列表 */
export function getConversations() {
    return request.get(`${BASE}/conversations`)
}

/** 获取单个会话历史 */
export function getConversation(id) {
    return request.get(`${BASE}/conversations/${id}`)
}

/** 修改会话标题 */
export function updateConversationTitle(id, title) {
    return request.patch(`${BASE}/conversations/${id}/title`, { title })
}

/** 删除会话 */
export function deleteConversation(id) {
    return request.delete(`${BASE}/conversations/${id}`)
}

/** 导出会话为纯文本 */
export function exportConversation(conv) {
    const lines = [`# ${conv.title || '对话记录'}`, `导出时间: ${new Date().toLocaleString()}`, '---']
    for (const msg of conv.messages || []) {
        lines.push(`\n【${msg.role === 'user' ? '用户' : 'AI'}】\n${msg.content}`)
        if (msg.sources?.length) {
            lines.push(`\n参考来源: ${msg.sources.map(s => s.title).join('、')}`)
        }
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${conv.title || '对话'}_${Date.now()}.txt`
    a.click()
    URL.revokeObjectURL(url)
}

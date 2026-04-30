/**
 * 答案反馈 API 模块
 */

import request from '@/utils/request'

const BASE = '/feedback'

export function submitFeedback(messageId, rating, comment = '') {
    return request.post(BASE, { message_id: messageId, rating, comment })
}

export function getMessageFeedback(messageId) {
    return request.get(`${BASE}/message/${messageId}`)
}

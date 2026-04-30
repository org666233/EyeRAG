/**
 * 收藏夹 API 模块
 */

import request from '@/utils/request'

const BASE = '/favorites'

export function addFavorite(messageId) {
    return request.post(BASE, { message_id: messageId })
}

export function listFavorites() {
    return request.get(BASE)
}

export function removeFavorite(favoriteId) {
    return request.delete(`${BASE}/${favoriteId}`)
}

export function checkFavorite(messageId) {
    return request.get(`${BASE}/check/${messageId}`)
}

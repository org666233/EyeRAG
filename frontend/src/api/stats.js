/**
 * 统计看板 API 模块
 */

import request from '@/utils/request'

export function getOverview() {
    return request.get('/stats/overview')
}

export function getTrend() {
    return request.get('/stats/trend')
}

export function getGlobalStats() {
    return request.get('/stats/global')
}

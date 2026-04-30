/**
 * 管理后台 API 模块
 */

import request from '@/utils/request'

const BASE = '/admin'

/** 系统总览 */
export function getAdminOverview() {
    return request.get(`${BASE}/stats/overview`)
}

/** 检索决策分布 */
export function getDecisionDistribution(days = 30) {
    return request.get(`${BASE}/stats/decision-distribution`, { params: { days } })
}

/** 响应耗时趋势 */
export function getResponseTimeTrend(days = 7) {
    return request.get(`${BASE}/stats/response-time`, { params: { days } })
}

/** 反馈趋势 */
export function getFeedbackTrend(days = 7) {
    return request.get(`${BASE}/stats/feedback-trend`, { params: { days } })
}

/** Top 查询 */
export function getTopQueries(limit = 20, days = 30) {
    return request.get(`${BASE}/stats/top-queries`, { params: { limit, days } })
}

/** 各来源文档的检索决策分布 */
export function getDecisionBySource(days = 30) {
    return request.get(`${BASE}/stats/decision-by-source`, { params: { days } })
}

/** 用户列表 */
export function getUserList(page = 1, pageSize = 20, keyword = '') {
    return request.get(`${BASE}/users`, { params: { page, page_size: pageSize, keyword } })
}

/** 切换用户激活状态 */
export function toggleUserActive(userId) {
    return request.patch(`${BASE}/users/${userId}/toggle-active`)
}

/** 删除用户 */
export function deleteUser(userId) {
    return request.delete(`${BASE}/users/${userId}`)
}

/** 创建管理员 */
export function createAdminUser(payload) {
    return request.post(`${BASE}/users`, payload)
}

/** 获取模型配置 */
export function getModelConfig() {
    return request.get(`${BASE}/model-config`)
}

/** 更新 LLM 配置 */
export function updateModelConfig(payload) {
    return request.post(`${BASE}/model-config`, payload)
}

/**
 * 检索历史 API 模块
 */

import request from '@/utils/request'

const BASE = '/search-history'

/**
 * 获取检索历史列表（分页）
 * @param {number} page - 页码
 * @param {number} pageSize - 每页条数
 * @param {string} keyword - 关键词搜索
 * @param {string} decision - 检索决策过滤: proceed / retry / fallback
 */
export function getSearchHistoryList(page = 1, pageSize = 20, keyword = '', decision = '') {
    return request.get(BASE, {
        params: { page, page_size: pageSize, keyword, decision },
    })
}

/**
 * 获取检索历史详情（包括搜索结果内容）
 */
export function getSearchHistoryDetail(id) {
    return request.get(`${BASE}/${id}`)
}

/**
 * 删除单条检索历史记录
 */
export function deleteSearchHistory(id) {
    return request.delete(`${BASE}/${id}`)
}

/**
 * 清空所有检索历史
 */
export function clearSearchHistory() {
    return request.delete(BASE)
}

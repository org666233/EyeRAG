/**
 * 知识库管理 API 模块
 */

import request from '@/utils/request'

const BASE = '/knowledge'

/** 获取知识库统计 */
export function getStats() {
    return request.get(`${BASE}/stats`)
}

/** 获取文档列表 */
export function getDocuments() {
    return request.get(`${BASE}/documents`)
}

/** 上传文档 */
export function uploadDocument(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`${BASE}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    })
}

/** 删除文档 */
export function deleteDocument(fileName) {
    return request.delete(`${BASE}/documents/${fileName}`)
}

/** 搜索知识库 */
export function searchKnowledge(query, topK = 5) {
    return request.post(`${BASE}/search`, { query, top_k: topK })
}

/** 获取文档预览内容 */
export function getDocumentPreview(fileName) {
    return request.get(`${BASE}/documents/${fileName}/preview`)
}

/** 下载文档文件 */
export function downloadDocument(fileName) {
    return `${import.meta.env.VITE_API_BASE_URL || '/api'}${BASE}/documents/${fileName}/download`
}

/** 带认证令牌的文档下载（触发浏览器下载） */
export async function downloadDocumentFile(fileName) {
    const token = localStorage.getItem('token')
    const base = import.meta.env.VITE_API_BASE_URL || ''
    const url = `${base}/api${BASE}/documents/${encodeURIComponent(fileName)}/download`
    const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` },
    })
    if (!res.ok) throw new Error('下载失败')
    const blob = await res.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = fileName
    a.click()
    URL.revokeObjectURL(a.href)
}

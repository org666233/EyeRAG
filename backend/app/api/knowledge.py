"""
知识库管理 API 路由
"""

import asyncio
import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.schemas.knowledge import (
    DocumentInfo, KnowledgeStats, IngestResponse, SearchRequest,
    SearchResponse, SearchResult, DocumentPreview,
)
from app.rag.vector_store import get_vector_store
from app.rag.document_loader import DocumentLoader
from app.rag.text_splitter import RecursiveCharacterTextSplitter
from app.models.doc_stats import DocStats
from app.models.user import User
from app.services.auth import get_current_user
from app.config import get_settings
from app.utils.logger import logger

router = APIRouter(prefix="/knowledge", tags=["knowledge"])
settings = get_settings()

DATA_DIR = Path("data/documents")

loader = DocumentLoader()
splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.chunk_size,
    chunk_overlap=settings.chunk_overlap,
)


@router.get("/stats", response_model=KnowledgeStats)
async def get_stats():
    """获取知识库统计信息"""
    vs = get_vector_store()
    return await asyncio.to_thread(vs.get_stats)


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents(
    session: AsyncSession = Depends(get_db),
):
    """获取所有已入库的文档列表（含热度信息）"""
    vs = get_vector_store()
    docs = await asyncio.to_thread(vs.list_documents)

    # 查询热度统计
    result = await session.execute(select(DocStats))
    stats_map = {s.file_name: s for s in result.scalars().all()}

    enriched = []
    for doc in docs:
        stats = stats_map.get(doc["file_name"])
        enriched.append({
            **doc,
            "view_count": stats.view_count if stats else 0,
            "hit_count": stats.hit_count if stats else 0,
        })
    return enriched


@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """上传并导入文档到知识库"""
    allowed_types = {".pdf", ".txt", ".md", ".markdown"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 {suffix}，支持: {', '.join(allowed_types)}"
        )

    # 保存到 data/documents/uploads/
    upload_dir = DATA_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    save_path = upload_dir / file.filename

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    logger.info(f"文件上传: {file.filename} ({len(content)/1024:.1f} KB)")

    # 导入到向量库
    try:
        docs = loader.load_file(save_path)
        chunks = splitter.split_documents(docs)
        vs = get_vector_store()
        count = vs.add_documents(chunks)
        return IngestResponse(
            file_name=file.filename,
            chunk_count=count,
            message=f"成功导入 {count} 个文本块",
        )
    except Exception as e:
        logger.error(f"文件导入失败: {e}")
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")


@router.delete("/documents/{file_name}")
async def delete_document(file_name: str):
    """从知识库删除指定文档的所有向量"""
    vs = get_vector_store()
    deleted = await asyncio.to_thread(vs.delete_by_source, file_name)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"未找到文件 {file_name} 的向量数据")

    # 尝试删除磁盘文件
    for subdir in DATA_DIR.iterdir():
        if subdir.is_dir():
            fp = subdir / file_name
            if fp.exists():
                fp.unlink()
                logger.info(f"删除文件: {fp}")

    return {"message": f"已删除 {file_name} 的 {deleted} 个向量块"}


@router.get("/documents/{file_name}/preview")
async def preview_document(
    file_name: str,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """文档预览：返回该文档的所有文本块内容（增加浏览次数）"""
    vs = get_vector_store()

    # 获取该文档的向量块（get() 不支持 distances，仅 query() 支持）
    try:
        collection = vs.collection
        results = await asyncio.to_thread(
            collection.get,
            where={"file_name": file_name},
            include=["documents", "metadatas"],
        )
    except Exception as e:
        logger.error(f"ChromaDB get 失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文档失败: {str(e)}")

    docs = results.get("documents", [])
    metas = results.get("metadatas", [])

    if not docs:
        raise HTTPException(status_code=404, detail=f"文档 {file_name} 无文本块记录")

    # 更新浏览次数
    result = await session.execute(
        select(DocStats).where(DocStats.file_name == file_name)
    )
    stats = result.scalar_one_or_none()
    if not stats:
        stats = DocStats(file_name=file_name, view_count=0, hit_count=0)
        session.add(stats)
    stats.view_count += 1
    await session.commit()

    # 组装返回
    chunks = []
    total_chars = 0
    for i, (content, meta) in enumerate(zip(docs, metas)):
        chunks.append({
            "chunk_index": i + 1,
            "content": content,
            "metadata": meta,
        })
        total_chars += len(content)

    file_type = metas[0].get("file_type", "") if metas else ""
    source_name = metas[0].get("source_name", "") if metas else ""

    return DocumentPreview(
        file_name=file_name,
        file_type=file_type,
        source_name=source_name,
        chunk_count=len(docs),
        view_count=stats.view_count,
        hit_count=stats.hit_count,
        chunks=chunks,
        total_chars=total_chars,
    )


@router.get("/documents/{file_name}/download")
async def download_document(
    file_name: str,
):
    """下载文档文件"""
    # 搜索文件路径
    search_paths = [
        DATA_DIR / file_name,
        DATA_DIR / "uploads" / file_name,
    ]

    file_path = None
    for sp in search_paths:
        if sp.exists():
            file_path = sp
            break

    if not file_path:
        raise HTTPException(status_code=404, detail=f"文件 {file_name} 不存在于磁盘")

    return FileResponse(
        path=str(file_path),
        filename=file_name,
        media_type="application/octet-stream",
    )


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """向量相似度检索（调试用）"""
    vs = get_vector_store()
    results = vs.search(query=request.query, top_k=request.top_k)
    return SearchResponse(
        query=request.query,
        results=[SearchResult(**r) for r in results],
        total=len(results),
    )


@router.post("/ingest-directory")
async def ingest_directory(path: str = Query(default="data/documents")):
    """
    批量导入目录下所有支持的文档（管理用途）。
    """
    dir_path = Path(path)
    if not dir_path.is_dir():
        raise HTTPException(status_code=400, detail=f"目录不存在: {path}")

    docs = loader.load_directory(dir_path, recursive=True)
    if not docs:
        return {"message": "目录中没有找到可导入的文档"}

    chunks = splitter.split_documents(docs)
    vs = get_vector_store()
    count = vs.add_documents(chunks)

    return {
        "message": f"成功导入 {len(docs)} 个文档，生成 {count} 个文本块",
        "document_count": len(docs),
        "chunk_count": count,
    }

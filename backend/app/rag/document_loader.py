"""
文档加载模块
支持格式: PDF, TXT, Markdown, HTML (基础)
提取文档元数据: 文件名、来源、页码等
"""

import os
from pathlib import Path
from typing import Union
from dataclasses import dataclass, field
from app.utils.logger import logger


@dataclass
class Document:
    """文档数据类，包含文本内容和元数据"""
    page_content: str
    metadata: dict = field(default_factory=dict)

    def __repr__(self):
        snippet = self.page_content[:80].replace("\n", " ")
        return f"Document(source={self.metadata.get('source', 'N/A')!r}, content={snippet!r}...)"


class DocumentLoader:
    """
    多格式文档加载器。
    支持: PDF, TXT, Markdown (.md), 纯文本 (.text)
    """

    def load_file(self, file_path: Union[str, Path]) -> list[Document]:
        """
        加载单个文件，返回 Document 列表（PDF 按页分割）。
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()
        logger.info(f"加载文件: {path.name} (类型: {suffix})")

        if suffix == ".pdf":
            return self._load_pdf(path)
        elif suffix in (".txt", ".md", ".text", ".markdown"):
            return self._load_text(path)
        else:
            logger.warning(f"不支持的文件格式 {suffix}，尝试以纯文本读取")
            return self._load_text(path)

    def load_directory(self, dir_path: Union[str, Path], recursive: bool = True) -> list[Document]:
        """
        批量加载目录下所有支持的文档。
        """
        dir_path = Path(dir_path)
        if not dir_path.is_dir():
            raise NotADirectoryError(f"不是有效目录: {dir_path}")

        pattern = "**/*" if recursive else "*"
        supported = {".pdf", ".txt", ".md", ".text", ".markdown"}

        documents = []
        file_paths = sorted([
            p for p in dir_path.glob(pattern)
            if p.is_file() and p.suffix.lower() in supported
        ])

        logger.info(f"目录 {dir_path} 共找到 {len(file_paths)} 个文档")

        for fp in file_paths:
            try:
                docs = self.load_file(fp)
                documents.extend(docs)
            except Exception as e:
                logger.error(f"加载 {fp.name} 失败: {e}")

        logger.info(f"成功加载 {len(documents)} 个文档片段（来自 {len(file_paths)} 个文件）")
        return documents

    # -----------------------------------------------------------------
    # 内部方法
    # -----------------------------------------------------------------

    def _load_pdf(self, path: Path) -> list[Document]:
        """使用 PyPDF2 按页加载 PDF"""
        try:
            import PyPDF2
        except ImportError:
            raise ImportError("请安装 PyPDF2: pip install pypdf2")

        documents = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            total_pages = len(reader.pages)

            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                text = text.strip()
                if not text:
                    continue

                documents.append(Document(
                    page_content=text,
                    metadata={
                        "source": str(path),
                        "file_name": path.name,
                        "file_type": "pdf",
                        "page": page_num + 1,
                        "total_pages": total_pages,
                    }
                ))

        logger.info(f"PDF {path.name}: 加载了 {len(documents)}/{total_pages} 页")
        return documents

    def _load_text(self, path: Path) -> list[Document]:
        """加载纯文本 / Markdown 文件"""
        # 尝试多种编码
        for encoding in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
            try:
                text = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            logger.error(f"无法解码文件 {path.name}")
            return []

        text = text.strip()
        if not text:
            return []

        # 从文件头提取 Source/Title 元数据 (download_data.py 写入的格式)
        lines = text.split("\n")
        metadata = {
            "source": str(path),
            "file_name": path.name,
            "file_type": path.suffix.lstrip("."),
        }
        for line in lines[:5]:
            if line.startswith("Source:"):
                metadata["source_name"] = line[7:].strip()
            elif line.startswith("Title:"):
                metadata["title"] = line[6:].strip()
            elif line.startswith("URL:"):
                metadata["url"] = line[4:].strip()

        return [Document(page_content=text, metadata=metadata)]

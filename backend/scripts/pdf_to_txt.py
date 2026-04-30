#!/usr/bin/env python3
"""
PDF 转 TXT 工具 - 解析 AAO PPP 等临床指南 PDF
使用 PyMuPDF (fitz) 提取文本
"""

import re
import sys
from pathlib import Path


def extract_text_from_pdf(pdf_path: Path, max_pages: int = None) -> str:
    """从 PDF 提取文本"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("需要安装 PyMuPDF: pip install pymupdf")
        sys.exit(1)

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)

    if max_pages:
        total_pages = min(total_pages, max_pages)

    text_parts = []

    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()

        # 清理文本
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        if text:
            text_parts.append(f"\n--- Page {page_num + 1} ---\n{text}")

    doc.close()

    return '\n'.join(text_parts)


def convert_pdf(pdf_path: Path, output_dir: Path = None) -> Path:
    """转换单个 PDF 为 TXT"""
    if output_dir is None:
        output_dir = pdf_path.parent

    # 输出文件名
    output_path = output_dir / f"{pdf_path.stem}.txt"

    print(f"处理: {pdf_path.name}")

    text = extract_text_from_pdf(pdf_path)

    if len(text) < 500:
        print(f"  ⚠️ 内容过少 ({len(text)} chars)，可能需要 OCR")
        # 保存原始内容
        output_path.write_text(text, encoding='utf-8')
        return output_path

    # 添加元数据头
    full_content = f"""---
source: aao_ppp
title: {pdf_path.stem}
file: {pdf_path.name}
type: clinical_guideline_ppp
---

{text}
"""

    output_path.write_text(full_content, encoding='utf-8')
    print(f"  ✅ 已保存: {output_path.name} ({len(text)} chars)")

    return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description="PDF 转 TXT 工具")
    parser.add_argument("path", nargs="?", default="data/documents/guidelines",
                        help="PDF 文件或目录路径")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--max-pages", "-m", type=int, default=None,
                        help="最大页数（用于测试）")

    args = parser.parse_args()

    path = Path(args.path)
    output_dir = Path(args.output) if args.output else None

    if path.is_file() and path.suffix.lower() == '.pdf':
        # 单个文件
        convert_pdf(path, output_dir)
    elif path.is_dir():
        # 目录中的所有 PDF
        pdf_files = list(path.glob("*.pdf"))
        if not pdf_files:
            print(f"目录中没有 PDF 文件: {path}")
            return

        print(f"找到 {len(pdf_files)} 个 PDF 文件")
        print("=" * 50)

        for pdf_file in pdf_files:
            convert_pdf(pdf_file, output_dir)
            print()
    else:
        print(f"无效路径: {path}")


if __name__ == "__main__":
    main()

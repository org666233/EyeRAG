#!/usr/bin/env python3
"""
中文医学网站爬虫 v5 - 带详细调试
"""

import re
import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"
BASE_DIR.mkdir(parents=True, exist_ok=True)

DEBUG = True  # 开启调试


@dataclass
class Article:
    title: str
    url: str
    content: str
    disease: str
    source: str


def fetch_page(url: str, timeout: int = 30) -> Optional[str]:
    """获取网页"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    import urllib.request
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                try:
                    return content.decode(enc)
                except:
                    continue
            return content.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"获取失败: {e}")
        return None


def crawl_xwyy():
    """爬取寻医问药网"""
    url = "https://jib.xywy.com/html/yanke.html"
    html = fetch_page(url)
    if not html:
        logger.error("无法获取页面")
        return []

    # 提取疾病链接
    pattern = r'href=["\'](/il_sii_\d+\.htm)["\'][^>]*>([^<]+)<'
    matches = re.findall(pattern, html)

    disease_urls = []
    seen = set()
    for href, name in matches:
        full_url = f"https://jib.xywy.com{href}"
        if full_url not in seen:
            seen.add(full_url)
            disease_urls.append((full_url, name.strip()))

    logger.info(f"找到 {len(disease_urls)} 个疾病")

    # 爬取
    saved = []
    for i, (article_url, disease_name) in enumerate(disease_urls[:50], 1):
        logger.info(f"[{i}/{len(disease_urls[:50])}] {disease_name}")

        article_html = fetch_page(article_url)
        if not article_html:
            logger.info(f"  ❌ 获取失败")
            continue

        # 移除脚本和样式
        article_html = re.sub(r'<script[^>]*>.*?</script>', '', article_html, flags=re.DOTALL)
        article_html = re.sub(r'<style[^>]*>.*?</style>', '', article_html, flags=re.DOTALL)

        # 提取标题
        title = disease_name
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_html, re.DOTALL)
        if title_match:
            extracted_title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            if extracted_title:
                title = extracted_title

        # 提取正文 - 尝试多种选择器
        content = ""
        selector_used = None

        selectors = [
            (r'<div[^>]*class="jib-content"[^>]*>(.*?)</div>', 'jib-content'),
            (r'<div[^>]*class="jib-art[^"]*"[^>]*>(.*?)</div>', 'jib-art*'),
            (r'<div[^>]*class="jib-con"[^>]*>(.*?)</div>', 'jib-con'),
            (r'<div[^>]*class="jib-art-left"[^>]*>(.*?)</div>', 'jib-art-left'),
            (r'<div[^>]*class="article[^"]*"[^>]*>(.*?)</div>', 'article*'),
            (r'<article[^>]*>(.*?)</article>', 'article tag'),
            (r'<div[^>]*id="content"[^>]*>(.*?)</div>', 'id=content'),
            (r'<div[^>]*class="con"[^>]*>(.*?)</div>', 'class=con'),
        ]

        for pattern, selector_name in selectors:
            match = re.search(pattern, article_html, re.DOTALL)
            if match:
                potential_content = match.group(1)
                if len(potential_content) > len(content):
                    content = potential_content
                    selector_used = selector_name

        if DEBUG:
            print(f"  选择器: {selector_used}, 内容长度: {len(content)}")

        if not content:
            logger.info(f"  ⚠️ 未找到正文，保存 HTML 供分析...")
            debug_file = BASE_DIR / f"debug_{disease_name}.html"
            debug_file.write_text(article_html[:50000], encoding='utf-8')
            continue

        # 转换为文本
        text = content
        text = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n## \2\n', text, flags=re.DOTALL)
        text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)
        text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', text, flags=re.DOTALL)
        text = re.sub(r'<br\s*/?>', '\n', text)
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'&\w+;', ' ', text)
        text = re.sub(r'\s{2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        if DEBUG and len(text) < 200:
            print(f"  ⚠️ 内容过少: {len(text)} chars")
            print(f"  前 100 字符: {text[:100]}")

        if len(text) < 200:
            continue

        # 保存
        disease_id = article_url.split('_')[-1].replace('.htm', '')
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', title)[:50]
        filename = f"xywy_{disease_id}_{safe_title}.txt"
        filepath = BASE_DIR / filename

        content_text = f"""---
source: xywy
title: {title}
url: {article_url}
disease: {disease_name}
disease_id: {disease_id}
type: medical_encyclopedia
---

{text}
"""
        filepath.write_text(content_text, encoding='utf-8')
        saved.append(filepath)
        logger.info(f"  ✅ {title[:40]} ({len(text)} chars)")

        time.sleep(1.5)

    return saved


def main():
    logger.info("=" * 60)
    logger.info("寻医问药网爬虫 v5 (调试模式)")
    logger.info("=" * 60)

    saved = crawl_xwyy()

    logger.info("=" * 60)
    logger.info(f"完成! 保存 {len(saved)} 篇")


if __name__ == "__main__":
    main()

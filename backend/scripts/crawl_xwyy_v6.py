#!/usr/bin/env python3
"""
中文医学网站爬虫 v6 - 爬取子页面
寻医问药网 /il_sii/ 子页面格式
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


@dataclass
class Article:
    title: str
    url: str
    content: str
    disease: str
    category: str
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


def extract_text_from_html(html: str) -> str:
    """从 HTML 提取纯文本"""
    # 移除脚本和样式
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)

    # 转换标签为文本
    text = html
    text = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n## \2\n', text, flags=re.DOTALL)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&\w+;', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def get_content_from_page(html: str) -> str:
    """从页面提取正文内容"""
    # 尝试多种选择器
    selectors = [
        r'<div[^>]*class="jib-navbar-bd[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="jib-nav-articl[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="jib-art[^"]*"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>',
    ]

    content = ""
    for pattern in selectors:
        match = re.search(pattern, html, re.DOTALL)
        if match and len(match.group(1)) > 200:
            content += match.group(1) + "\n"

    if not content:
        # 获取整个 body
        match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        if match:
            content = match.group(1)

    return content


def crawl_xwyy():
    """爬取寻医问药网 - 爬取子页面"""
    # 疾病列表页
    list_url = "https://jib.xywy.com/html/yanke.html"
    html = fetch_page(list_url)
    if not html:
        logger.error("无法获取疾病列表页")
        return []

    # 提取疾病链接
    pattern = r'href=["\'](/il_sii_\d+\.htm)["\'][^>]*>([^<]+)<'
    matches = re.findall(pattern, html)

    diseases = []
    seen = set()
    for href, name in matches:
        disease_id = href.split('_')[-1].replace('.htm', '')
        full_url = f"https://jib.xywy.com{href}"
        if full_url not in seen:
            seen.add(full_url)
            diseases.append({
                'id': disease_id,
                'name': name.strip(),
                'url': full_url
            })

    logger.info(f"找到 {len(diseases)} 个疾病")

    # 子页面类型
    sub_pages = [
        ('gaishu', '概述'),
        ('cause', '病因'),
        ('symptom', '症状'),
        ('inspect', '检查'),
        ('diagnosis', '诊断'),
        ('treat', '治疗'),
        ('prevent', '预防'),
        ('neopathy', '并发症'),
        ('nurse', '护理'),
    ]

    saved = []

    # 只爬取前 30 个疾病
    for i, disease in enumerate(diseases[:30], 1):
        disease_id = disease['id']
        disease_name = disease['name']

        logger.info(f"[{i}/{len(diseases[:30])}] {disease_name} (ID: {disease_id})")

        all_content = []

        for page_type, page_name in sub_pages:
            sub_url = f"https://jib.xywy.com/il_sii/{page_type}/{disease_id}.htm"
            sub_html = fetch_page(sub_url)

            if not sub_html:
                continue

            # 提取标题
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', sub_html, re.DOTALL)
            if title_match:
                title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            else:
                title = f"{disease_name} - {page_name}"

            # 提取内容
            content = get_content_from_page(sub_html)
            text = extract_text_from_html(content)

            if len(text) > 100:
                all_content.append(f"\n{'='*40}\n{page_name}\n{'='*40}\n\n{text}")
                logger.info(f"  ✅ {page_name}: {len(text)} chars")
            else:
                logger.info(f"  ⏭️ {page_name}: 内容过少")

            time.sleep(0.8)

        if all_content:
            # 保存完整文章
            full_text = f"""---
source: xywy
title: {disease_name}
disease_id: {disease_id}
type: medical_encyclopedia
---

# {disease_name}

{''.join(all_content)}
"""
            safe_name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', disease_name)[:30]
            filename = f"xywy_{disease_id}_{safe_name}.txt"
            filepath = BASE_DIR / filename

            filepath.write_text(full_text, encoding='utf-8')
            saved.append(filepath)
            logger.info(f"  💾 保存: {filename} ({len(full_text)} chars)")
        else:
            logger.info(f"  ❌ 未获取到任何内容")

        time.sleep(1)

    return saved


def main():
    logger.info("=" * 60)
    logger.info("寻医问药网爬虫 v6 (子页面模式)")
    logger.info("=" * 60)

    saved = crawl_xwyy()

    logger.info("=" * 60)
    logger.info(f"完成! 保存 {len(saved)} 篇")
    if saved:
        logger.info("保存的文件:")
        for f in saved:
            logger.info(f"  {f.name}")


if __name__ == "__main__":
    main()

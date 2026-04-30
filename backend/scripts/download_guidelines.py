#!/usr/bin/env python3
"""
下载眼科临床指南
支持: NICE, AAO PPP, 中华医学会指南等网页内容
"""

import re
import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents" / "guidelines"
BASE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Guideline:
    name: str
    url: str
    disease: str
    source: str


GUIDELINES = [
    # NICE 指南 (免费公开)
    Guideline(
        name="NICE NG81 - 青光眼诊断与管理指南",
        url="https://www.nice.org.uk/guidance/ng81/chapter/Recommendations",
        disease="glaucoma",
        source="nice"
    ),
    Guideline(
        name="NICE NG82 - 年龄相关性黄斑变性指南",
        url="https://www.nice.org.uk/guidance/ng82/chapter/Recommendations",
        disease="amd",
        source="nice"
    ),
    Guideline(
        name="NICE NG242 - 糖尿病视网膜病变管理与监测指南",
        url="https://www.nice.org.uk/guidance/ng242/chapter/Recommendations",
        disease="diabetic_retinopathy",
        source="nice"
    ),

    # AAO Preferred Practice Patterns (直接 PDF 链接)
    Guideline(
        name="AAO PPP - 原发性开角型青光眼 2025",
        url="https://www.aao.org/education/preferred-practice-pattern/primary-open-angle-glaucoma-ppp",
        disease="glaucoma",
        source="aao"
    ),
    Guideline(
        name="AAO PPP - 年龄相关性黄斑变性",
        url="https://www.aao.org/education/preferred-practice-pattern/age-related-macular-degeneration-ppp",
        disease="amd",
        source="aao"
    ),
    Guideline(
        name="AAO PPP - 白内障",
        url="https://www.aao.org/education/preferred-practice-pattern/cataract-in-the-adult-eye-ppp",
        disease="cataract",
        source="aao"
    ),
    Guideline(
        name="AAO PPP - 糖尿病视网膜病变",
        url="https://www.aao.org/education/preferred-practice-pattern/diabetic-retinopathy-ppp",
        disease="diabetic_retinopathy",
        source="aao"
    ),
    Guideline(
        name="AAO PPP - 屈光不正与老视",
        url="https://www.aao.org/education/preferred-practice-pattern/refractive-errors-refractive-surgery-ppp",
        disease="refractive_error",
        source="aao"
    ),

    # 更多 AAO PPP
    Guideline(
        name="AAO PPP - 干眼病",
        url="https://www.aao.org/education/preferred-practice-pattern/dry-eye-syndrome-ppp",
        disease="dry_eye",
        source="aao"
    ),
    Guideline(
        name="AAO PPP - 角膜混浊",
        url="https://www.aao.org/education/preferred-practice-pattern/corneal-opacification-ppp",
        disease="cornea",
        source="aao"
    ),
    Guideline(
        name="AAO PPP - 视网膜脱离",
        url="https://www.aao.org/education/preferred-practice-pattern/retinal-detachment-ppp",
        disease="retinal_detachment",
        source="aao"
    ),
]


def fetch_url(url: str, timeout: int = 30) -> Optional[str]:
    """获取网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        logger.warning(f"获取失败 {url}: {e}")
        return None


def extract_main_content(html: str, source: str) -> str:
    """从网页提取主要内容"""
    import re

    # 移除脚本和样式
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    if source == "nice":
        # NICE 页面结构：内容在 article 或 .guidance类中
        patterns = [
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="guidance"[^>]*>(.*?)</div>',
            r'<div[^>]*class="article-content"[^>]*>(.*?)</div>',
            r'<main[^>]*>(.*?)</main>',
        ]
    elif source == "aao":
        # AAO 页面结构
        patterns = [
            r'<article[^>]*>(.*?)</article>',
            r'<div[^>]*class="content"[^>]*>(.*?)</div>',
            r'<main[^>]*>(.*?)</main>',
        ]
    else:
        patterns = [r'<main[^>]*>(.*?)</main>', r'<article[^>]*>(.*?)</article>']

    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            html = match.group(1)
            break

    # 转换为文本
    text = html
    text = re.sub(r'<h1[^>]*>.*?</h1>', '\n# ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h2[^>]*>(.*?)</h2>', r'\n## \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h3[^>]*>(.*?)</h3>', r'\n### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<h4[^>]*>(.*?)</h4>', r'\n#### \1\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def download_guideline(guideline: Guideline) -> bool:
    """下载单个指南"""
    filename = f"{guideline.source}_{guideline.disease}_{guideline.name.split(' - ')[0].replace(' ', '_')}.txt"
    filepath = BASE_DIR / filename

    if filepath.exists() and filepath.stat().st_size > 1024:
        logger.info(f"跳过（已存在）: {guideline.name}")
        return True

    logger.info(f"下载: {guideline.name}")
    html = fetch_url(guideline.url)

    if not html:
        logger.error(f"❌ 获取失败: {guideline.name}")
        return False

    content = extract_main_content(html, guideline.source)

    if len(content) < 500:
        logger.warning(f"⚠ 内容过少 ({len(content)} chars): {guideline.name}")
        # 保存原始 HTML 供调试
        debug_path = BASE_DIR / f"debug_{filename.replace('.txt', '.html')}"
        debug_path.write_text(html[:5000])
        return False

    # 添加头部信息
    full_content = f"""---
source: {guideline.source}
title: {guideline.name}
url: {guideline.url}
disease: {guideline.disease}
type: clinical_guideline
---

{content}
"""

    filepath.write_text(full_content, encoding='utf-8')
    logger.info(f"✅ 已保存: {guideline.name} ({len(content)} chars)")
    return True


def main():
    logger.info("=" * 60)
    logger.info("眼科临床指南下载工具")
    logger.info(f"保存目录: {BASE_DIR}")
    logger.info("=" * 60)

    success = 0
    failed = 0

    for i, guideline in enumerate(GUIDELINES, 1):
        if download_guideline(guideline):
            success += 1
        else:
            failed += 1
        time.sleep(1)  # 礼貌延迟

    logger.info("=" * 60)
    logger.info(f"下载完成! 成功: {success}, 失败: {failed}")
    logger.info(f"文件保存在: {BASE_DIR}")

    # 列出已下载的文件
    files = list(BASE_DIR.glob("*.txt"))
    if files:
        logger.info(f"\n已下载 {len(files)} 个指南文件:")
        for f in sorted(files):
            size = f.stat().st_size / 1024
            logger.info(f"  {f.name} ({size:.1f} KB)")


if __name__ == "__main__":
    main()

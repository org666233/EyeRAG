#!/usr/bin/env python3
"""
调试单个页面 - 检查内容结构
"""

import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.crawl_xwyy_v4 import fetch_page


def debug_page(url: str):
    """调试单个页面"""
    print(f"URL: {url}")
    print("=" * 60)

    html = fetch_page(url)
    if not html:
        print("获取失败!")
        return

    print(f"HTML 长度: {len(html)} chars")
    print("=" * 60)

    # 移除脚本和样式
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 提取标题
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if title_match:
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        print(f"标题: {title}")

    print("=" * 60)
    print("尝试不同的选择器:")
    print("=" * 60)

    # 尝试各种选择器
    selectors = [
        (r'<div[^>]*class="jib-content"[^>]*>(.*?)</div>', 'jib-content'),
        (r'<div[^>]*class="jib-art[^"]*"[^>]*>(.*?)</div>', 'jib-art*'),
        (r'<div[^>]*class="article[^"]*"[^>]*>(.*?)</div>', 'article*'),
        (r'<article[^>]*>(.*?)</article>', 'article'),
        (r'<div[^>]*id="content"[^>]*>(.*?)</div>', 'id=content'),
        (r'<div[^>]*class="jib-art-left"[^>]*>(.*?)</div>', 'jib-art-left'),
        (r'<div[^>]*class="jib-con"[^>]*>(.*?)</div>', 'jib-con'),
        (r'<div[^>]*class="con"[^>]*>(.*?)</div>', 'class=con'),
    ]

    for pattern, name in selectors:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            content = match.group(1)
            print(f"\n✅ {name}: 找到 {len(content)} chars")

            # 提取纯文本
            text = re.sub(r'<[^>]+>', '', content)
            text = re.sub(r'\s+', ' ', text).strip()
            print(f"   纯文本: {len(text)} chars")
            print(f"   前 200 字符: {text[:200]}...")
        else:
            print(f"\n❌ {name}: 未找到")

    # 保存完整 HTML 供分析
    debug_file = Path(__file__).parent.parent / "data" / "debug_article.html"
    debug_file.write_text(html[:50000], encoding='utf-8')
    print(f"\n" + "=" * 60)
    print(f"完整 HTML 已保存: {debug_file}")


if __name__ == "__main__":
    # 测试几个页面
    test_urls = [
        "https://jib.xywy.com/il_sii_9375.htm",  # 飞蚊症
        "https://jib.xywy.com/il_sii_9493.htm",  # 黄斑变性
        "https://jib.xywy.com/il_sii_2749.htm",  # 原发性开角型青光眼
    ]

    for url in test_urls:
        print("\n" + "#" * 60)
        debug_page(url)
        print()

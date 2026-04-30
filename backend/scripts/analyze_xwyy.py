#!/usr/bin/env python3
"""
分析寻医问药网页结构
"""

import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.crawl_chinese_medical_v2 import fetch_page

url = "https://jib.xywy.com/html/yanke.html"
html = fetch_page(url)

if html:
    # 保存完整 HTML
    debug_file = Path(__file__).parent.parent / "data" / "debug_xwyy.html"
    debug_file.write_text(html, encoding='utf-8')
    print(f"已保存: {debug_file}")

    # 分析链接模式
    print("\n=== 分析链接结构 ===")

    # 找所有 yanke 相关的链接
    links = re.findall(r'href=["\']([^"\']*)["\']', html)
    yanke_links = [l for l in links if 'yanke' in l.lower()]

    print(f"总链接数: {len(links)}")
    print(f"yanke 相关链接: {len(yanke_links)}")

    if yanke_links:
        print("\n前 20 个 yanke 链接:")
        seen = set()
        count = 0
        for link in yanke_links:
            if link not in seen and count < 20:
                seen.add(link)
                print(f"  {link}")
                count += 1
    else:
        print("\n没有找到 yanke 相关链接，检查页面结构...")

        # 尝试提取疾病名称
        diseases = re.findall(r'>([^<]{3,20}(?:炎|病|症|综合征|瘤|障|伤|疝|疡|疹|疹))<', html)
        if diseases:
            print(f"\n找到 {len(diseases)} 个可能的疾病名称:")
            for d in diseases[:20]:
                print(f"  {d}")
else:
    print("获取失败")

#!/usr/bin/env python3
"""
调试脚本 - 检查网站是否可访问
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.crawl_chinese_medical_v2 import fetch_page, get_xwyy_disease_list


def test_fetch():
    """测试网页获取"""
    print("=" * 60)
    print("测试 1: 寻医问药网获取")
    print("=" * 60)

    url = "https://jib.xywy.com/html/yanke.html"
    print(f"URL: {url}")

    html = fetch_page(url)

    if html:
        print(f"✅ 获取成功，内容长度: {len(html)} chars")
        print(f"前 500 字符:")
        print(html[:500])
    else:
        print("❌ 获取失败")
        print("\n可能原因:")
        print("1. 网络连接问题")
        print("2. 网站禁止访问（IP 被封）")
        print("3. 需要 VPN 或代理")


def test_parse():
    """测试解析"""
    print("\n" + "=" * 60)
    print("测试 2: 解析疾病列表")
    print("=" * 60)

    diseases = get_xwyy_disease_list()

    if diseases:
        print(f"✅ 找到 {len(diseases)} 个疾病")
        print("\n前 10 个:")
        for i, d in enumerate(diseases[:10], 1):
            print(f"  {i}. {d['name']} - {d['url']}")
    else:
        print("❌ 未找到疾病")
        print("\n检查 HTML 内容...")

        url = "https://jib.xywy.com/html/yanke.html"
        html = fetch_page(url)
        if html:
            # 保存 HTML 供分析
            debug_file = Path(__file__).parent.parent / "data" / "debug_xwyy.html"
            debug_file.write_text(html[:10000], encoding='utf-8')
            print(f"已保存 HTML 前 10000 字符到: {debug_file}")
            print("请检查该文件，看看是否有疾病链接")


def test_single_article():
    """测试单个文章"""
    print("\n" + "=" * 60)
    print("测试 3: 获取单个文章")
    print("=" * 60)

    from scripts.crawl_chinese_medical_v2 import parse_xwyy_article

    # 尝试获取一个具体的疾病页面
    test_urls = [
        "https://jib.xywy.com/yanke/bai neoyan.html",
        "https://jib.xywy.com/yanke/jinshiyan.html",
        "https://jib.xywy.com/yanke/qingguangyan.html",
    ]

    for url in test_urls:
        print(f"\n尝试: {url}")
        html = fetch_page(url)
        if html:
            article = parse_xwyy_article(html, url)
            if article:
                print(f"✅ 成功: {article.title} ({len(article.content)} chars)")
                break
            else:
                print("⚠️ HTML 获取成功但解析失败")
        else:
            print("❌ 获取失败")


if __name__ == "__main__":
    test_fetch()
    test_parse()
    test_single_article()

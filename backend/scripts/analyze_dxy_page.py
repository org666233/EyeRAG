#!/usr/bin/env python3
"""
分析丁香园疾病列表页
"""

import re
import json
import urllib.request

def fetch_page(url: str) -> str:
    """获取网页"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode('utf-8', errors='ignore')


def main():
    # 眼科疾病列表页
    url = "https://www.dxy.com/diseases/list/yanke"

    print(f"请求: {url}")
    html = fetch_page(url)
    print(f"页面大小: {len(html)} 字符")

    # 保存完整页面
    with open('/Users/org/Documents/Final/RAG/backend/data/dxy_yanke.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("已保存页面到 data/dxy_yanke.html")

    # 查找 __NEXT_DATA__ 或类似的数据
    next_data = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if next_data:
        print("\n✅ 找到 __NEXT_DATA__")
        data = json.loads(next_data.group(1))
        print(f"数据大小: {len(str(data))} 字符")

        # 保存
        with open('/Users/org/Documents/Final/RAG/backend/data/dxy_next_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("已保存到 data/dxy_next_data.json")

        # 分析数据
        if 'props' in data:
            print(f"\nprops keys: {list(data['props'].keys())}")
        if 'pageProps' in data.get('props', {}):
            print(f"pageProps keys: {list(data['props']['pageProps'].keys())}")

    # 查找 window.__INITIAL_STATE__ 或类似
    init_state = re.search(r'window\.(\w+)\s*=\s*(\{.*?\});', html, re.DOTALL)
    if init_state:
        print(f"\n✅ 找到 window.{init_state.group(1)}")

    # 查找 JSON 数据
    json_patterns = [
        r'"diseases"\s*:\s*\[(.*?)\]',
        r'"diseaseList"\s*:\s*\[(.*?)\]',
        r'"items"\s*:\s*\[(.*?)\]',
        r'"data"\s*:\s*\{(.*?)\}',
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, html)
        if matches:
            print(f"\n找到匹配 {pattern}: {len(matches)} 个")

    # 查找疾病 ID 和名称
    disease_pattern = r'"id"\s*:\s*(\d+)[^}]*"name"\s*:\s*"([^"]+)"'
    diseases = re.findall(disease_pattern, html)
    if diseases:
        print(f"\n✅ 直接从 HTML 找到 {len(diseases)} 个疾病")
        for disease_id, name in diseases[:20]:
            print(f"  {disease_id}: {name}")

    # 查找所有 /disease/XXXXX/detail 格式的 URL
    disease_urls = re.findall(r'/disease/(\d+)/detail', html)
    if disease_urls:
        print(f"\n✅ 找到 {len(disease_urls)} 个 disease URL")
        unique_urls = list(set(disease_urls))
        print(f"去重后: {len(unique_urls)} 个")

        # 保存到文件
        with open('/Users/org/Documents/Final/RAG/backend/data/documents/chinese_medical/dxy_yanke_ids.txt', 'w') as f:
            for disease_id in sorted(unique_urls, key=int):
                f.write(f"https://dxy.com/disease/{disease_id}/detail\n")
        print("已保存到 dxy_yanke_ids.txt")


if __name__ == "__main__":
    main()

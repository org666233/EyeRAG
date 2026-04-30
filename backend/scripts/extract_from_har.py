#!/usr/bin/env python3
"""
从 dxy.com1.har 提取疾病数据
这个 HAR 文件对应 https://dxy.com/diseases/3880 (眼科疾病列表)
"""

import re
import json
from pathlib import Path

def extract_from_har(har_path: str):
    with open(har_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)

    all_text = ""
    disease_urls = set()
    disease_ids = set()

    # 遍历所有请求
    for entry in har_data.get('log', {}).get('entries', []):
        response = entry.get('response', {})
        content = response.get('content', {})

        # 获取响应文本
        text = content.get('text', '')
        if text:
            all_text += text + "\n"

    print(f"HAR 总文本大小: {len(all_text)} 字符")

    # 查找疾病 ID 和 URL
    # 模式: /disease/数字/detail
    url_matches = re.findall(r'/disease/(\d+)/detail', all_text)
    disease_ids.update(url_matches)

    # 模式: diseaseId 后面跟着数字
    id_matches = re.findall(r'diseaseId["\s:]+(\d+)', all_text)
    disease_ids.update(id_matches)

    # 模式: disId
    disid_matches = re.findall(r'disId["\s:]+(\d+)', all_text)
    disease_ids.update(disid_matches)

    print(f"找到疾病 ID: {len(disease_ids)} 个")

    if disease_ids:
        # 生成 URL
        for disease_id in disease_ids:
            disease_urls.add(f"https://dxy.com/disease/{disease_id}/detail")

        # 保存
        output_dir = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"

        urls_file = output_dir / "dxy_yanke_urls.txt"
        with open(urls_file, 'w') as f:
            for url in sorted(disease_urls, key=lambda x: int(x.split('/')[-2])):
                f.write(url + '\n')
        print(f"已保存: {urls_file}")

        print(f"\n前 20 个疾病 ID:")
        for i, did in enumerate(sorted(disease_ids, key=int)[:20], 1):
            print(f"  {i}. {did}")
    else:
        print("\n没有找到疾病 ID，尝试其他方法...")

        # 保存全部文本供分析
        debug_file = Path(__file__).parent.parent / "data" / "dxy_har_text.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(all_text)
        print(f"已保存全部文本到: {debug_file}")


if __name__ == "__main__":
    import sys
    har_file = sys.argv[1] if len(sys.argv) > 1 else "/Users/org/Documents/Final/RAG/backend/scripts/dxy.com1.har"

    print("=" * 60)
    print("提取丁香园疾病数据")
    print("=" * 60)

    extract_from_har(har_file)

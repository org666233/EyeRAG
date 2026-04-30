#!/usr/bin/env python3
"""
从 HAR 文件提取丁香园疾病列表
"""

import re
import json
from pathlib import Path

def extract_diseases_from_har(har_path: str):
    """从 HAR 文件提取疾病信息"""

    with open(har_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"HAR 文件大小: {len(content)} 字符")

    # 查找疾病 ID 和名称
    disease_urls = set()

    # 模式1: /disease/数字/detail
    urls = re.findall(r'/disease/(\d+)/detail', content)
    disease_urls.update(urls)

    # 模式2: diseaseId 格式
    disease_ids = re.findall(r'diseaseId["\']?\s*:\s*["\']?(\d+)', content)
    disease_urls.update(disease_ids)

    print(f"\n找到 {len(disease_urls)} 个疾病 ID")

    if disease_urls:
        unique_ids = sorted(disease_urls, key=int)

        # 保存完整列表
        output_file = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical" / "dxy_yanke_full.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 丁香园眼科疾病列表\n")
            f.write(f"# 共 {len(unique_ids)} 个疾病\n\n")
            for disease_id in unique_ids:
                url = f"https://dxy.com/disease/{disease_id}/detail"
                f.write(f"{url}\n")

        print(f"已保存: {output_file}")

        # 同时保存为纯 URL 列表
        urls_file = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical" / "dxy_yanke_urls.txt"
        with open(urls_file, 'w', encoding='utf-8') as f:
            for disease_id in unique_ids:
                f.write(f"https://dxy.com/disease/{disease_id}/detail\n")

        print(f"URL列表已保存: {urls_file}")

        print(f"\n前 20 个疾病 ID:")
        for i, disease_id in enumerate(unique_ids[:20], 1):
            print(f"  {i}. {disease_id}")

    # 尝试提取疾病名称
    print("\n尝试提取疾病名称...")

    # 从 HAR 内容中查找 JSON 数据块
    json_blocks = re.findall(r'\{[^{}]*"id"[^{}]*"name"[^{}]*\}', content)
    print(f"找到 {len(json_blocks)} 个 JSON 块")

    # 提取疾病名称
    disease_names = re.findall(r'"name"\s*:\s*"([^"]+)"', content)
    print(f"找到 {len(disease_names)} 个名称")

    # 过滤可能的疾病名称
    valid_names = []
    for name in disease_names:
        if 2 < len(name) < 30 and not any(x in name for x in ['http', 'www', 'dxy', '.com', '医生', '丁香']):
            valid_names.append(name)

    valid_names = list(set(valid_names))
    print(f"去重后 {len(valid_names)} 个")

    # 保存名称
    if valid_names:
        names_file = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical" / "dxy_yanke_names.txt"
        with open(names_file, 'w', encoding='utf-8') as f:
            for name in sorted(valid_names):
                f.write(f"{name}\n")
        print(f"名称已保存: {names_file}")

    return unique_ids


if __name__ == "__main__":
    import sys

    har_file = sys.argv[1] if len(sys.argv) > 1 else "/Users/org/Documents/Final/RAG/backend/scripts/dxy.com1.har"

    print("=" * 60)
    print("从 HAR 文件提取丁香园疾病列表")
    print("=" * 60)

    extract_diseases_from_har(har_file)

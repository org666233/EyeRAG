#!/usr/bin/env python3
"""
深度分析 HAR 文件，提取所有可能的疾病数据
"""

import re
import json
from pathlib import Path

def deep_extract_from_har(har_path: str):
    """深度提取 HAR 文件中的数据"""

    with open(har_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"HAR 文件大小: {len(content)} 字符")

    # 提取所有 response 内容的 URL
    # 查找响应中的文本

    results = {
        'disease_urls': set(),
        'disease_ids': set(),
        'disease_names': set(),
        'json_data': []
    }

    # 方法1: 查找数字 ID 模式
    # /disease/12345/detail
    url_pattern = r'/disease/(\d+)/detail'
    matches = re.findall(url_pattern, content)
    results['disease_ids'].update(matches)
    print(f"\n方法1 - /disease/ID/detail 模式: 找到 {len(matches)} 个")

    # 方法2: 查找纯数字 ID（在疾病相关的上下文中）
    # 查找 "id": 12345 或 "diseaseId": 12345 格式
    id_patterns = [
        r'"(?:diseaseId|id|disId)"\s*:\s*(\d{4,7})',
        r'"disId"\s*:\s*(\d+)',
        r'"disease_id"\s*:\s*(\d+)',
    ]

    for pattern in id_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            print(f"模式 {pattern}: 找到 {len(matches)} 个")
            results['disease_ids'].update(matches)

    # 方法3: 查找可能的疾病名称（上下文中有 disease/doctor/medical 关键词）
    # 提取所有 JSON 对象
    json_strings = re.findall(r'\{[^{}]{50,2000}\}', content)

    for js in json_strings[:500]:  # 只检查前500个
        # 查找包含疾病信息的JSON
        if any(kw in js for kw in ['diseaseId', 'disId', 'disease_id', 'diseaseName', 'disName']):
            # 提取ID
            ids = re.findall(r'(?:diseaseId|disId|disease_id|"id")\s*:\s*(\d+)', js)
            results['disease_ids'].update(ids)

            # 提取名称
            names = re.findall(r'(?:diseaseName|disName|disease_name|"name")\s*:\s*"([^"]+)"', js)
            for name in names:
                if 2 < len(name) < 30 and '\u4e00' <= name[0] <= '\u9fff':
                    results['disease_names'].add(name)

    print(f"\n总共找到 {len(results['disease_ids'])} 个疾病 ID")
    print(f"总共找到 {len(results['disease_names'])} 个疾病名称")

    # 生成疾病 URL
    for disease_id in results['disease_ids']:
        results['disease_urls'].add(f"https://dxy.com/disease/{disease_id}/detail")

    # 保存结果
    output_dir = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 保存 URL 列表
    if results['disease_urls']:
        urls_file = output_dir / "dxy_extracted_urls.txt"
        with open(urls_file, 'w') as f:
            for url in sorted(results['disease_urls'], key=lambda x: int(x.split('/')[-2])):
                f.write(url + '\n')
        print(f"\n✅ 疾病链接已保存: {urls_file} ({len(results['disease_urls'])} 个)")

    # 保存 ID 列表
    if results['disease_ids']:
        ids_file = output_dir / "dxy_extracted_ids.txt"
        with open(ids_file, 'w') as f:
            for disease_id in sorted(results['disease_ids'], key=int):
                f.write(disease_id + '\n')
        print(f"✅ 疾病ID已保存: {ids_file} ({len(results['disease_ids'])} 个)")

    # 保存名称列表
    if results['disease_names']:
        names_file = output_dir / "dxy_extracted_names.txt"
        with open(names_file, 'w', encoding='utf-8') as f:
            for name in sorted(results['disease_names']):
                f.write(name + '\n')
        print(f"✅ 疾病名称已保存: {names_file} ({len(results['disease_names'])} 个)")

    # 显示样本
    if results['disease_ids']:
        print(f"\n前 30 个疾病 ID:")
        for i, disease_id in enumerate(sorted(results['disease_ids'], key=int)[:30], 1):
            print(f"  {i}. {disease_id}")

    return results


if __name__ == "__main__":
    import sys

    har_file = sys.argv[1] if len(sys.argv) > 1 else "/Users/org/Documents/Final/RAG/backend/scripts/dxy.com1.har"

    print("=" * 60)
    print("深度分析 HAR 文件")
    print("=" * 60)

    results = deep_extract_from_har(har_file)

    print("\n" + "=" * 60)
    print("分析完成")
    print(f"疾病链接: {len(results['disease_urls'])} 个")
    print(f"疾病ID: {len(results['disease_ids'])} 个")
    print(f"疾病名称: {len(results['disease_names'])} 个")
    print("=" * 60)

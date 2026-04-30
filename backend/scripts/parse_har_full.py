#!/usr/bin/env python3
"""
完整解析 HAR 文件，包括处理压缩内容
"""

import re
import json
import zlib
import base64
from pathlib import Path

def decode_response_content(content: dict, headers: list) -> str:
    """解码响应内容（处理 gzip/br 压缩）"""
    text = content.get('text', '')
    if not text:
        return ''

    encoding = content.get('encoding', '')
    mime_type = content.get('mimeType', '')

    # 检查 Transfer-Encoding
    for h in headers:
        if h.get('name', '').lower() == 'transfer-encoding':
            if 'chunked' in h.get('value', '').lower():
                # 需要解码
                pass

    # 如果是 gzip 压缩
    if 'gzip' in mime_type.lower() or 'gzip' in str(headers).lower():
        try:
            decoded = zlib.decompress(text.encode('latin-1'), 16 + zlib.MAX_WBITS)
            return decoded.decode('utf-8', errors='ignore')
        except:
            pass

    return text


def extract_diseases(har_path: str):
    with open(har_path, 'r', encoding='utf-8') as f:
        har_data = json.load(f)

    all_content = []
    disease_urls = set()
    disease_ids = set()

    for entry in har_data.get('log', {}).get('entries', []):
        request = entry.get('request', {})
        response = entry.get('response', {})

        url = request.get('url', '')
        headers = response.get('headers', [])
        content = response.get('content', {})

        text = content.get('text', '')

        if not text:
            continue

        # 解码内容
        try:
            decoded = decode_response_content(content, headers)
            if decoded:
                all_content.append(decoded)
            else:
                all_content.append(text)
        except:
            all_content.append(text)

    full_text = '\n'.join(all_content)

    # 查找疾病 URL 和 ID
    url_pattern = r'dxy\.com/disease/(\d+)/detail'
    matches = re.findall(url_pattern, full_text)
    disease_ids.update(matches)
    print(f"找到 dxy.com/disease URL 模式: {len(matches)} 个")

    # 查找 "id": 数字 模式
    id_pattern = r'"id"\s*:\s*(\d{4,7})'
    matches = re.findall(id_pattern, full_text)
    print(f"找到 'id': 数字 模式: {len(matches)} 个")

    # 查找疾病相关关键词周围的 ID
    disease_context = re.findall(r'disease.{0,100}"id"\s*:\s*(\d+)', full_text, re.DOTALL)
    print(f"在 disease 上下文找到: {len(disease_context)} 个")

    # 尝试查找 JSON 数据中的疾病信息
    json_pattern = r'\{[^{}]*"id"[^{}]*\d{4,7}[^{}]*\}'
    json_matches = re.findall(json_pattern, full_text)
    print(f"找到 JSON 对象: {len(json_matches)} 个")

    if disease_ids:
        for did in disease_ids:
            disease_urls.add(f"https://dxy.com/disease/{did}/detail")

        output_dir = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"
        urls_file = output_dir / "dxy_yanke_urls.txt"
        with open(urls_file, 'w') as f:
            for url in sorted(disease_urls, key=lambda x: int(x.split('/')[-2])):
                f.write(url + '\n')
        print(f"\n✅ 已保存 {len(disease_urls)} 个疾病 URL: {urls_file}")
    else:
        # 直接搜索数字
        all_nums = re.findall(r'\b(\d{4,7})\b', full_text)
        num_counts = {}
        for n in all_nums:
            num_counts[n] = num_counts.get(n, 0) + 1

        # 找出出现多次的数字（可能是疾病ID）
        repeated = [(k, v) for k, v in num_counts.items() if v >= 2]
        repeated.sort(key=lambda x: -x[1])

        print(f"\n出现多次的数字 (可能是疾病ID):")
        for num, count in repeated[:30]:
            print(f"  {num}: 出现 {count} 次")

        # 保存前50个作为候选
        if repeated:
            output_dir = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"
            candidates = [r[0] for r in repeated[:100] if 1000 < int(r[0]) < 100000]
            urls_file = output_dir / "dxy_candidates.txt"
            with open(urls_file, 'w') as f:
                for did in candidates:
                    f.write(f"https://dxy.com/disease/{did}/detail\n")
            print(f"\n已保存 {len(candidates)} 个候选 URL: {urls_file}")


if __name__ == "__main__":
    har_file = "/Users/org/Documents/Final/RAG/backend/scripts/dxy.com1.har"
    extract_diseases(har_file)

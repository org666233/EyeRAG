#!/usr/bin/env python3
"""
丁香园眼科疾病详情爬虫
"""

import re
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"
BASE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class DiseaseArticle:
    id: str
    title: str
    url: str
    content: str
    source: str = "丁香园"


def extract_disease_id(url: str) -> str:
    """从URL提取疾病ID"""
    match = re.search(r'/disease/(\d+)/', url)
    return match.group(1) if match else "unknown"


def crawl_single_disease(driver, url: str) -> Optional[DiseaseArticle]:
    """爬取单个疾病页面"""
    disease_id = extract_disease_id(url)

    try:
        driver.get(url)
        time.sleep(2)  # 等待页面加载

        # 获取页面源码
        page_source = driver.page_source

        # 提取标题
        title_match = re.search(r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h1>', page_source, re.DOTALL)
        if not title_match:
            title_match = re.search(r'<title>(.*?)</title>', page_source)
        title = re.sub(r'<[^>]+>', '', title_match.group(1) if title_match else f"疾病{disease_id}").strip()

        # 提取正文内容
        # 尝试多种内容容器
        content_patterns = [
            r'<div[^>]*class="[^"]*(?:content|article|detail)[^"]*"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
            r'<main[^>]*>(.*?)</main>',
        ]

        content = ""
        for pattern in content_patterns:
            match = re.search(pattern, page_source, re.DOTALL | re.IGNORECASE)
            if match:
                raw_content = match.group(1)
                # 清理HTML标签
                content = re.sub(r'<[^>]+>', '\n', raw_content)
                content = re.sub(r'\n\s*\n', '\n', content)
                content = content.strip()
                if len(content) > 100:
                    break

        # 如果没找到内容，尝试获取整个body
        if not content or len(content) < 100:
            body_match = re.search(r'<body[^>]*>(.*?)</body>', page_source, re.DOTALL)
            if body_match:
                raw = body_match.group(1)
                # 移除脚本和样式
                raw = re.sub(r'<script[^>]*>.*?</script>', '', raw, flags=re.DOTALL)
                raw = re.sub(r'<style[^>]*>.*?</style>', '', raw, flags=re.DOTALL)
                raw = re.sub(r'<nav[^>]*>.*?</nav>', '', raw, flags=re.DOTALL)
                raw = re.sub(r'<footer[^>]*>.*?</footer>', '', raw, flags=re.DOTALL)
                content = re.sub(r'<[^>]+>', ' ', raw)
                content = re.sub(r'\s+', ' ', content).strip()

        # 限制内容长度
        if len(content) > 50000:
            content = content[:50000]

        return DiseaseArticle(
            id=disease_id,
            title=title,
            url=url,
            content=content,
            source="丁香园"
        )

    except Exception as e:
        logger.warning(f"爬取失败 {url}: {e}")
        return None


def main():
    # 读取疾病链接
    urls_file = BASE_DIR / "dxy_yanke_diseases.txt"
    if not urls_file.exists():
        logger.error(f"未找到文件: {urls_file}")
        return

    with open(urls_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    logger.info(f"共 {len(urls)} 个疾病链接")

    # 启动浏览器
    logger.info("启动浏览器...")
    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)

    try:
        # 手动登录提示
        logger.info("请在浏览器中登录丁香园...")
        input("登录后按 Enter 继续...")

        results = []
        failed = []

        for i, url in enumerate(urls, 1):
            logger.info(f"[{i}/{len(urls)}] 爬取: {url}")

            article = crawl_single_disease(driver, url)
            if article:
                results.append(article)
                logger.info(f"  标题: {article.title[:50]}...")
                logger.info(f"  内容长度: {len(article.content)} 字符")
            else:
                failed.append(url)
                logger.info(f"  失败!")

            # 每10个保存一次
            if i % 10 == 0:
                save_results(results, failed)
                logger.info(f"  已保存进度...")

            time.sleep(1)  # 礼貌性延迟

        # 最终保存
        save_results(results, failed)

        logger.info(f"\n完成! 成功: {len(results)}, 失败: {len(failed)}")

    finally:
        driver.quit()


def save_results(results: List[DiseaseArticle], failed: List[str]):
    """保存结果"""
    if not results:
        return

    # 保存为JSONL
    jsonl_file = BASE_DIR / "dxy_yanke_articles.jsonl"
    with open(jsonl_file, 'w', encoding='utf-8') as f:
        for article in results:
            f.write(json.dumps(asdict(article), ensure_ascii=False) + '\n')

    # 保存失败的链接
    if failed:
        failed_file = BASE_DIR / "dxy_yanke_failed.txt"
        with open(failed_file, 'w') as f:
            for url in failed:
                f.write(url + '\n')

    logger.info(f"已保存 {len(results)} 条记录到 {jsonl_file}")


if __name__ == "__main__":
    main()

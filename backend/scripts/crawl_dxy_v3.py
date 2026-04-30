#!/usr/bin/env python3
"""
丁香园爬虫 v3 - 超级版
支持多种策略获取疾病列表
"""

import re
import time
import json
import logging
from pathlib import Path
from typing import Optional, Set
import urllib.request

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"


def fetch_with_headers(url: str) -> Optional[str]:
    """带Headers的HTTP请求"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"请求失败: {url} - {e}")
        return None


def analyze_api_endpoints():
    """分析丁香园的API端点"""
    logger.info("分析丁香园 API...")

    # 获取疾病列表页
    html = fetch_with_headers("https://www.dxy.com/diseases/list/yanke")
    if not html:
        logger.error("无法获取疾病列表页")
        return [], []

    # 查找 API URL
    api_patterns = [
        r'api["\']?\s*:\s*["\']([^"\']+)["\']',
        r'baseURL["\']?\s*:\s*["\']([^"\']+)["\']',
        r'url\s*:\s*["\']([^"\']*disease[^"\']*)["\']',
        r'fetch\(["\']([^"\']+)["\']',
        r'axios\.get\(["\']([^"\']+)["\']',
    ]

    api_urls = []
    for pattern in api_patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        api_urls.extend(matches)

    # 去重并过滤
    api_urls = list(set([u for u in api_urls if 'http' in u or u.startswith('/')]))

    logger.info(f"找到 {len(api_urls)} 个可能的 API URL")

    # 尝试常见的疾病列表 API
    possible_apis = [
        "https://www.dxy.com/api/diseases?category=yanke",
        "https://www.dxy.com/api/disease/list?department=yanke",
        "https://api.dxy.com/diseases/yanke",
    ]

    for api in possible_apis:
        logger.info(f"尝试: {api}")
        result = fetch_with_headers(api)
        if result and len(result) > 100:
            logger.info(f"  ✅ 成功! 返回 {len(result)} 字符")
            # 解析 JSON
            try:
                data = json.loads(result)
                logger.info(f"  数据类型: {type(data)}")
            except:
                pass

    return api_urls, []


def get_diseases_from_page() -> tuple[Set[str], Set[str]]:
    """从页面获取疾病列表"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)

    disease_urls = set()
    disease_names = set()

    try:
        logger.info("请在浏览器中手动登录丁香园...")
        input("登录完成后按 Enter 继续...")

        # 访问疾病列表页
        logger.info("访问: https://www.dxy.com/diseases/list/yanke")
        driver.get("https://www.dxy.com/diseases/list/yanke")

        # 等待页面加载
        logger.info("等待页面加载...")
        time.sleep(8)

        # 滚动加载所有内容
        logger.info("滚动页面加载所有疾病...")
        last_height = driver.execute_script("return document.body.scrollHeight")

        for scroll_round in range(10):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # 点击可能的"加载更多"按钮
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for btn in buttons:
                    if "加载" in btn.text or "更多" in btn.text:
                        btn.click()
                        time.sleep(1)
            except:
                pass

            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                logger.info(f"  页面已滚动到底部 (第 {scroll_round + 1} 次)")
                break
            last_height = new_height

        # 保存页面源码用于调试
        debug_file = BASE_DIR / "dxy_yanke_page.html"
        debug_file.write_text(driver.page_source[:200000], encoding='utf-8')
        logger.info(f"页面源码已保存: {debug_file}")

        # 提取所有疾病链接
        all_links = driver.find_elements(By.TAG_NAME, "a")

        for link in all_links:
            try:
                href = link.get_attribute('href')
                text = link.text.strip()

                if href and '/disease/' in href:
                    disease_urls.add(href)

                if text and 2 < len(text) < 20:
                    disease_names.add(text)
            except:
                pass

        logger.info(f"从页面找到 {len(disease_urls)} 个疾病链接")
        logger.info(f"找到 {len(disease_names)} 个疾病名称")

        # 保存疾病列表
        urls_file = BASE_DIR / "dxy_yanke_urls.txt"
        with open(urls_file, 'w', encoding='utf-8') as f:
            for url in sorted(disease_urls):
                f.write(url + '\n')
        logger.info(f"链接已保存: {urls_file}")

        names_file = BASE_DIR / "dxy_yanke_names.txt"
        with open(names_file, 'w', encoding='utf-8') as f:
            for name in sorted(disease_names):
                f.write(name + '\n')
        logger.info(f"名称已保存: {names_file}")

    finally:
        driver.quit()

    return disease_urls, disease_names


def crawl_diseases(disease_urls: Set[str], max_count: int = 200):
    """爬取疾病详情页"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By

    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)

    saved = []
    urls_list = sorted(disease_urls)[:max_count]

    try:
        for i, url in enumerate(urls_list, 1):
            logger.info(f"[{i}/{len(urls_list)}] {url}")

            try:
                driver.get(url)
                time.sleep(3)

                title = driver.title.strip()

                # 尝试多种选择器获取正文
                content = ""
                selectors = [
                    ".article-content",
                    "[class*='content']",
                    "article",
                    "main",
                    ".disease-detail",
                    ".detail-wrapper",
                ]

                for selector in selectors:
                    try:
                        elem = driver.find_element(By.CSS_SELECTOR, selector)
                        text = elem.text
                        if len(text) > 300:
                            content = text
                            break
                    except:
                        continue

                if not content or len(content) < 200:
                    content = driver.page_source
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = re.sub(r'\s+', ' ', content)

                if len(content) < 200:
                    logger.info(f"  ⚠️ 内容太少")
                    continue

                disease_id = url.split('/')[-2]

                filename = f"dxy_{disease_id}.txt"
                filepath = BASE_DIR / filename

                content_text = f"""---
source: dxy
title: {title}
url: {url}
disease_id: {disease_id}
type: medical_article
---

{content}
"""
                filepath.write_text(content_text, encoding='utf-8')
                saved.append(filepath)
                logger.info(f"  ✅ {title[:50]} ({len(content)} chars)")

            except Exception as e:
                logger.warning(f"  ❌ {e}")

            time.sleep(2)

    finally:
        driver.quit()

    return saved


def main():
    import argparse
    parser = argparse.ArgumentParser(description="丁香园爬虫 v3")
    parser.add_argument("--max", type=int, default=200, help="最大爬取数量")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("丁香园爬虫 v3 - 超级版")
    logger.info("=" * 60)

    # 步骤1: 获取疾病列表
    logger.info("\n>>> 步骤1: 获取疾病列表...")
    disease_urls, disease_names = get_diseases_from_page()

    if not disease_urls:
        logger.error("无法获取疾病列表，退出")
        return

    # 步骤2: 爬取疾病详情
    logger.info(f"\n>>> 步骤2: 爬取 {min(len(disease_urls), args.max)} 个疾病详情...")
    saved = crawl_diseases(disease_urls, args.max)

    logger.info("=" * 60)
    logger.info(f"完成! 保存 {len(saved)} 篇")


if __name__ == "__main__":
    main()

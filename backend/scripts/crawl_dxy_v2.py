#!/usr/bin/env python3
"""
丁香园爬虫 v2 - 改进版
使用更智能的等待策略获取所有眼科疾病
"""

import re
import time
import logging
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"


def crawl_dxy_v2():
    """丁香园爬虫 v2"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        logger.error("需要安装 selenium: pip install selenium")
        return []

    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)

    try:
        logger.info("请在浏览器中手动登录丁香园...")
        input("登录完成后按 Enter 继续...")

        # 方法1: 访问眼科疾病列表页
        logger.info("访问眼科疾病列表页...")
        driver.get("https://www.dxy.com/diseases/list/yanke")
        time.sleep(5)  # 等待 5 秒

        # 方法2: 尝试滚动页面加载更多内容
        logger.info("滚动页面加载更多内容...")
        for scroll_round in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            logger.info(f"  滚动第 {scroll_round + 1} 次...")

        # 尝试点击"加载更多"按钮（如果有）
        try:
            while True:
                load_more_btn = driver.find_elements(By.XPATH,
                    "//button[contains(text(), '加载更多')] | //a[contains(text(), '加载更多')]")
                if load_more_btn:
                    load_more_btn[0].click()
                    time.sleep(2)
                    logger.info("  点击了'加载更多'按钮")
                else:
                    break
        except Exception as e:
            logger.info(f"  没有找到'加载更多'按钮: {e}")

        # 获取页面上的所有疾病链接
        all_disease_urls = set()
        all_disease_names = []

        # 方法3: 直接分析页面源码中的 API 调用
        page_source = driver.page_source

        # 查找 disease ID 模式
        disease_ids = re.findall(r'/disease/(\d+)', page_source)
        for disease_id in disease_ids:
            all_disease_urls.add(f"https://dxy.com/disease/{disease_id}/detail")

        # 查找疾病名称
        name_patterns = [
            r'"name"\s*:\s*"([^"]+)"',
            r'class="[^"]*disease[^"]*"[^>]*>([^<]+)<',
            r'<a[^>]*href="/disease/\d+"[^>]*>([^<]+)<',
        ]

        for pattern in name_patterns:
            matches = re.findall(pattern, page_source)
            for name in matches:
                name = name.strip()
                if 2 < len(name) < 30 and not name.startswith('http'):
                    all_disease_names.append(name)

        logger.info(f"从页面找到 {len(all_disease_urls)} 个疾病链接")

        # 保存疾病列表
        diseases_file = BASE_DIR / "dxy_yanke_diseases.txt"
        with open(diseases_file, 'w', encoding='utf-8') as f:
            for url in sorted(all_disease_urls):
                f.write(url + '\n')
        logger.info(f"疾病列表已保存: {diseases_file}")

        if not all_disease_urls:
            logger.error("未找到任何疾病链接！")
            logger.error("丁香园可能需要登录才能查看疾病列表")
            return []

        # 爬取每个疾病
        saved = []
        disease_list = sorted(all_disease_urls)

        for i, article_url in enumerate(disease_list, 1):
            logger.info(f"[{i}/{len(disease_list)}] {article_url}")

            try:
                driver.get(article_url)
                time.sleep(3)  # 等待页面加载

                title = driver.title.strip()

                # 尝试获取正文
                content = ""
                selectors = [
                    ".article-content",
                    ".disease-content",
                    "article",
                    "main",
                    ".main-content",
                    ".content-wrapper",
                    ".detail-content",
                ]

                for selector in selectors:
                    try:
                        elem = driver.find_element(By.CSS_SELECTOR, selector)
                        content = elem.text
                        if len(content) > 500:
                            break
                    except:
                        continue

                if not content or len(content) < 200:
                    # 获取整个页面文本
                    content = driver.page_source
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = re.sub(r'\s+', ' ', content)

                if len(content) < 200:
                    logger.info(f"  ⚠️ 内容太少，跳过")
                    continue

                disease_id = article_url.split('/')[-2]

                filename = f"dxy_{disease_id}.txt"
                filepath = BASE_DIR / filename

                content_text = f"""---
source: dxy
title: {title}
url: {article_url}
disease_id: {disease_id}
type: medical_article
---

{content}
"""
                filepath.write_text(content_text, encoding='utf-8')
                saved.append(filepath)
                logger.info(f"  ✅ {title[:40]} ({len(content)} chars)")

            except Exception as e:
                logger.warning(f"  ❌ {e}")

            time.sleep(2)

        return saved

    finally:
        logger.info("关闭浏览器...")
        driver.quit()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="丁香园爬虫 v2")
    parser.add_argument("--max", type=int, default=200, help="最大爬取数量")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("丁香园爬虫 v2 - 改进版")
    logger.info("=" * 60)

    saved = crawl_dxy_v2()

    logger.info("=" * 60)
    logger.info(f"完成! 保存 {len(saved)} 篇")

    if saved:
        logger.info("前 5 个文件:")
        for f in saved[:5]:
            logger.info(f"  {f.name}")
        if len(saved) > 5:
            logger.info(f"  ... 共 {len(saved)} 个文件")


if __name__ == "__main__":
    main()

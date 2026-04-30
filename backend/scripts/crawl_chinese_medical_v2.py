#!/usr/bin/env python3
"""
中文医学网站爬虫 v2
- 寻医问药网 (xywy.com) - 无需登录
- 丁香园 (dxy.com) - 需要登录（Selenium 模式）
"""

import re
import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"
BASE_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Article:
    title: str
    url: str
    content: str
    disease: str
    source: str


# ============================================================
# 寻医问药网 (xywy.com)
# ============================================================

def fetch_page(url: str, timeout: int = 30) -> Optional[str]:
    """获取网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }

    import urllib.request
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            # 尝试多种编码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                try:
                    return content.decode(encoding)
                except:
                    continue
            return content.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"获取失败 {url}: {e}")
        return None


def get_xwyy_disease_list() -> list[dict]:
    """获取寻医问药眼科疾病列表"""
    url = "https://jib.xywy.com/html/yanke.html"
    html = fetch_page(url)
    if not html:
        return []

    diseases = []

    # 多种匹配模式
    patterns = [
        # 标准链接格式
        r'<a[^>]+href=["\']([^"\']*yanke[^"\']*)["\'][^>]*>([^<]{2,20})</a>',
        # 更通用的匹配
        r'href=["\']([^"\']*)["\'][^>]*>\s*([^<]{2,15}炎|[^<]{2,15}病|[^<]{2,15}综合征|[^<]{2,15}症)\s*<',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)
        for href, name in matches:
            name = name.strip()
            if len(name) >= 2 and len(name) <= 20:
                # 补全完整 URL
                if not href.startswith('http'):
                    href = "https://jib.xywy.com" + href
                # 过滤非疾病链接
                if 'yanke' in href and 'html' in href:
                    diseases.append({'name': name, 'url': href})

    # 去重
    seen = {}
    unique = []
    for d in diseases:
        if d['url'] not in seen:
            seen[d['url']] = True
            unique.append(d)

    return unique


def parse_xwyy_article(html: str, url: str) -> Optional[Article]:
    """解析寻医问药文章"""
    # 移除脚本和样式
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 提取标题
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    if not title_match:
        title_match = re.search(r'<title>(.*?)</title>', html)
    title = re.sub(r'<[^>]+>', '', title_match.group(1) if title_match else "未知标题").strip()

    # 提取正文内容 - 尝试多个选择器
    content = ""
    selectors = [
        r'<div[^>]*class="jib-content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="article-content"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*id="article"[^>]*>(.*?)</div>',
    ]

    for pattern in selectors:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match and len(match.group(1)) > 500:
            content = match.group(1)
            break

    if not content:
        return None

    # 转换为文本
    text = content
    text = re.sub(r'<h([1-6])[^>]*>(.*?)</h\1>', r'\n## \2\n', text, flags=re.DOTALL)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&\w+;', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    if len(text) < 200:
        return None

    # 提取疾病名
    disease = "unknown"
    if '/yanke/' in url:
        parts = url.split('/')
        for i, p in enumerate(parts):
            if p == 'yanke' and i + 1 < len(parts):
                disease = parts[i + 1].replace('.html', '')
                break

    return Article(title=title, url=url, content=text, disease=disease, source="xywy")


# ============================================================
# 丁香园 (dxy.com) - Selenium 模式
# ============================================================

def crawl_dxy_with_selenium(driver, disease_url: str) -> Optional[Article]:
    """使用 Selenium 爬取丁香园文章"""
    try:
        driver.get(disease_url)
        time.sleep(3)

        # 检查登录状态
        if 'login' in driver.current_url.lower():
            return None

        title = ""
        try:
            title_elem = driver.find_element("css selector", "h1, .disease-title, [class*='title']")
            title = title_elem.text.strip()
        except:
            pass

        if not title:
            try:
                title = driver.title.strip()
            except:
                title = "未知标题"

        # 获取正文
        content = ""
        try:
            content_elem = driver.find_element("css selector",
                ".article-content, .content, article, .detail-content, [class*='content']")
            content = content_elem.text
        except:
            pass

        if not content or len(content) < 100:
            # 获取整个页面文本
            content = driver.page_source
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content)

        disease = disease_url.split('/')[-1].replace('.html', '')

        return Article(title=title, url=disease_url, content=content,
                      disease=disease, source="dxy")

    except Exception as e:
        logger.warning(f"爬取失败 {disease_url}: {e}")
        return None


def get_dxy_diseases(driver) -> list[str]:
    """获取丁香园眼科疾病列表"""
    url = "https://www.dxy.com/diseases/list/yanke"
    driver.get(url)
    time.sleep(5)

    urls = []
    try:
        # 查找所有疾病链接
        links = driver.find_elements("css selector", "a[href*='/disease/']")
        for link in links:
            href = link.get_attribute('href')
            if href and '/disease/' in href:
                urls.append(href)
    except Exception as e:
        logger.warning(f"获取疾病列表失败: {e}")

    return list(set(urls))


# ============================================================
# 通用工具
# ============================================================

def save_article(article: Article) -> Path:
    """保存文章"""
    source_dir = BASE_DIR / article.source
    source_dir.mkdir(parents=True, exist_ok=True)

    safe_title = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', article.title)[:50]
    filename = f"{article.disease}_{safe_title}.txt"
    filepath = source_dir / filename

    content = f"""---
source: {article.source}
title: {article.title}
url: {article.url}
disease: {article.disease}
type: medical_article
---

{article.content}
"""

    filepath.write_text(content, encoding='utf-8')
    return filepath


# ============================================================
# 主函数
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="中文医学网站爬虫")
    parser.add_argument("--source", choices=["xywy", "dxy", "all"], default="xywy")
    parser.add_argument("--max", type=int, default=30)

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("中文医学网站爬虫 v2")
    logger.info("=" * 60)

    if args.source in ["xywy", "all"]:
        logger.info("\n>>> 爬取寻医问药网...")
        diseases = get_xwyy_disease_list()
        logger.info(f"找到 {len(diseases)} 个疾病")

        if not diseases:
            logger.error("获取疾病列表失败，检查网络连接")
        else:
            saved = 0
            for i, d in enumerate(diseases[:args.max], 1):
                logger.info(f"[{i}/{len(diseases[:args.max])}] {d['name']}")
                html = fetch_page(d['url'])
                if html:
                    article = parse_xwyy_article(html, d['url'])
                    if article:
                        save_article(article)
                        saved += 1
                        logger.info(f"  ✅ ({len(article.content)} chars)")
                    else:
                        logger.info(f"  ⚠️ 解析失败")
                else:
                    logger.info(f"  ❌ 获取失败")
                time.sleep(1.5)
            logger.info(f"寻医问药: 保存 {saved} 篇")

    if args.source in ["dxy", "all"]:
        logger.info("\n>>> 爬取丁香园（需要 Selenium）...")
        logger.info("提示: 先手动在浏览器登录丁香园，然后运行:")
        logger.info("  python -c \"from scripts.crawl_chinese_medical_v2 import *; import selenium_main; selenium_main.run()\"")


if __name__ == "__main__":
    main()


# ============================================================
# Selenium 专用函数
# ============================================================

def selenium_main():
    """Selenium 主函数（需要先手动登录）"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        print("需要安装: pip install selenium")
        return

    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)

    try:
        logger.info("请在打开的浏览器中登录丁香园...")
        logger.info("登录完成后按 Enter 继续...")
        input()

        logger.info("获取疾病列表...")
        urls = get_dxy_diseases(driver)
        logger.info(f"找到 {len(urls)} 个疾病链接")

        saved = 0
        for i, url in enumerate(urls[:30], 1):
            logger.info(f"[{i}/{len(urls[:30])}] {url}")
            article = crawl_dxy_with_selenium(driver, url)
            if article:
                save_article(article)
                saved += 1
                logger.info(f"  ✅ ({len(article.content)} chars)")
            else:
                logger.info(f"  ⚠️ 跳过")
            time.sleep(2)

        logger.info(f"丁香园: 保存 {saved} 篇")

    finally:
        logger.info("关闭浏览器...")
        driver.quit()

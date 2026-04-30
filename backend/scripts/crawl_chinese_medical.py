#!/usr/bin/env python3
"""
中文医学网站爬虫
- 寻医问药网 (xywy.com) - 无需登录
- 丁香园 (dxy.com) - 需要登录（Selenium 模式）
"""

import re
import time
import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Iterator
from urllib.parse import urljoin, urlparse

import urllib.request
import urllib.error

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
# 寻医问药网 (xywy.com) - 无需登录
# ============================================================

def fetch_xwyy(url: str, timeout: int = 30) -> Optional[str]:
    """获取寻医问药网页"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://jib.xywy.com/',
    }

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 检测编码
            content = resp.read()
            # 先尝试 utf-8
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                # 尝试 gb2312/gbk
                try:
                    return content.decode('gbk')
                except:
                    return content.decode('gb18030', errors='ignore')
    except Exception as e:
        logger.warning(f"获取失败 {url}: {e}")
        return None


def get_xwyy_disease_list(base_url: str) -> list[dict]:
    """获取眼科疾病列表"""
    html = fetch_xwyy(base_url)
    if not html:
        return []

    diseases = []

    # 提取疾病链接
    patterns = [
        r'<a[^>]+href="(/yanke/[^"]+)"[^>]*>([^<]+)</a>',
        r'href="(https?://jib\.xywy\.com/yanke/[^"]+)"[^>]*>([^<]+)</a>',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html)
        for href, name in matches:
            name = name.strip()
            if len(name) >= 2 and '科' not in name[:4]:  # 过滤科室名
                diseases.append({
                    'name': name,
                    'url': urljoin(base_url, href) if href.startswith('/') else href
                })

    # 去重
    seen = set()
    unique = []
    for d in diseases:
        if d['url'] not in seen:
            seen.add(d['url'])
            unique.append(d)

    return unique


def parse_xwyy_article(html: str, url: str) -> Optional[Article]:
    """解析寻医问药文章"""
    # 移除脚本和样式
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # 提取标题
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL)
    title = re.sub(r'<[^>]+>', '', title_match.group(1)) if title_match else "未知标题"
    title = title.strip()

    # 提取主要内容
    content_patterns = [
        r'<div[^>]*class="jib-content[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*class="content[^"]*"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>',
    ]

    content = ""
    for pattern in content_patterns:
        match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
        if match:
            content = match.group(1)
            break

    if not content:
        return None

    # 转换为文本
    text = content
    text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'\n## \1\n', text, flags=re.DOTALL)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'\n- \1', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&\w+;', ' ', text)  # HTML 实体
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    if len(text) < 200:
        return None

    # 从 URL 或标题推断疾病名
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    disease = path_parts[-1] if path_parts else "unknown"

    return Article(
        title=title,
        url=url,
        content=text,
        disease=disease,
        source="xywy"
    )


def crawl_xwyy_article(url: str) -> Optional[Article]:
    """爬取单个文章"""
    html = fetch_xwyy(url)
    if not html:
        return None
    return parse_xwyy_article(html, url)


# ============================================================
# 丁香园 (dxy.com) - Selenium 模式
# ============================================================

def crawl_dxy_selenium(url: str, driver) -> Optional[Article]:
    """使用 Selenium 爬取丁香园文章（需要登录）"""
    try:
        driver.get(url)
        time.sleep(3)  # 等待页面加载

        # 检查是否需要登录
        page_source = driver.page_source
        if 'login' in driver.current_url.lower() or '请登录' in page_source:
            logger.warning("需要登录，请先在浏览器中登录丁香园")
            return None

        title_elem = driver.find_element("css selector", "h1")
        title = title_elem.text.strip()

        # 获取正文内容
        content_elem = driver.find_element("css selector", ".article-content, .content, article")
        content = content_elem.text

        parsed = urlparse(url)
        disease = parsed.path.split('/')[-1] if parsed.path else "unknown"

        return Article(
            title=title,
            url=url,
            content=content,
            disease=disease,
            source="dxy"
        )

    except Exception as e:
        logger.warning(f"Selenium 爬取失败 {url}: {e}")
        return None


# ============================================================
# 通用工具
# ============================================================

def save_article(article: Article, base_dir: Path = None) -> Path:
    """保存文章到文件"""
    if base_dir is None:
        base_dir = BASE_DIR / article.source
    base_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    safe_title = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', article.title)[:50]
    filename = f"{article.disease}_{safe_title}.txt"
    filepath = base_dir / filename

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


def crawl_xwyy_yanke(max_articles: int = 50):
    """爬取寻医问药眼科疾病"""
    base_url = "https://jib.xywy.com/html/yanke.html"

    logger.info("获取眼科疾病列表...")
    diseases = get_xwyy_disease_list(base_url)

    if not diseases:
        logger.error("无法获取疾病列表")
        return []

    logger.info(f"找到 {len(diseases)} 个眼科疾病")

    saved = []
    for i, disease in enumerate(diseases[:max_articles], 1):
        logger.info(f"[{i}/{min(len(diseases), max_articles)}] 爬取: {disease['name']}")

        article = crawl_xwyy_article(disease['url'])
        if article:
            path = save_article(article)
            saved.append(path)
            logger.info(f"  ✅ 已保存: {path.name} ({len(article.content)} chars)")
        else:
            logger.warning(f"  ❌ 爬取失败: {disease['name']}")

        time.sleep(1)  # 礼貌延迟

    return saved


def crawl_dxy_yanke(max_articles: int = 50, use_selenium: bool = False, driver=None):
    """爬取丁香园眼科疾病"""
    # 丁香园疾病列表 API
    api_url = "https://www.dxy.com/diseases/list/yanke"

    logger.info(f"获取丁香园眼科疾病列表 (Selenium: {use_selenium})...")

    if use_selenium and driver:
        # Selenium 模式
        driver.get(api_url)
        time.sleep(5)

        # 获取所有疾病链接
        links = driver.find_elements("css selector", "a[href*='/disease/']")
        disease_urls = [link.get_attribute('href') for link in links]

    else:
        # 普通模式 - 可能需要登录
        html = fetch_xwyy(api_url)
        if not html:
            logger.error("无法访问丁香园，请使用 Selenium 模式")
            return []

        # 提取疾病链接
        disease_urls = re.findall(r'href="(https?://www\.dxy\.com/disease/[^"]+)"', html)

    logger.info(f"找到 {len(disease_urls)} 个疾病链接")

    saved = []
    for i, url in enumerate(disease_urls[:max_articles], 1):
        logger.info(f"[{i}/{min(len(disease_urls), max_articles)}] 爬取: {url}")

        if use_selenium and driver:
            article = crawl_dxy_selenium(url, driver)
        else:
            html = fetch_xwyy(url)
            if html and '请登录' not in html:
                title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html)
                title = re.sub(r'<[^>]+>', '', title_match.group(1)) if title_match else "未知"
                content = re.sub(r'<[^>]+>', '', html)
                article = Article(title=title, url=url, content=content,
                                  disease=url.split('/')[-1], source="dxy")
            else:
                article = None

        if article:
            path = save_article(article)
            saved.append(path)
            logger.info(f"  ✅ 已保存: {path.name}")
        else:
            logger.warning(f"  ❌ 爬取失败")

        time.sleep(2)

    return saved


# ============================================================
# 主函数
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="中文医学网站爬虫")
    parser.add_argument("--source", choices=["xywy", "dxy", "all"], default="xywy",
                        help="数据源: xywy(寻医问药), dxy(丁香园), all")
    parser.add_argument("--max", type=int, default=30,
                        help="最大爬取文章数")
    parser.add_argument("--selenium", action="store_true",
                        help="使用 Selenium（用于需要登录的网站）")

    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("中文医学网站爬虫")
    logger.info(f"保存目录: {BASE_DIR}")
    logger.info("=" * 60)

    driver = None

    if args.selenium:
        try:
            from selenium import webdriver
            driver = webdriver.Chrome()
            logger.info("已启动 Chrome Selenium")
        except ImportError:
            logger.error("请安装 Selenium: pip install selenium")
            logger.error("并下载 ChromeDriver")
            return

    try:
        if args.source in ["xywy", "all"]:
            logger.info("\n" + "=" * 40)
            logger.info("爬取: 寻医问药网 (xywy.com)")
            logger.info("=" * 40)
            saved = crawl_xwyy_yanke(max_articles=args.max)
            logger.info(f"寻医问药: 已保存 {len(saved)} 篇")

        if args.source in ["dxy", "all"]:
            logger.info("\n" + "=" * 40)
            logger.info("爬取: 丁香园 (dxy.com)")
            logger.info("=" * 40)
            saved = crawl_dxy_yanke(max_articles=args.max,
                                    use_selenium=args.selenium,
                                    driver=driver)
            logger.info(f"丁香园: 已保存 {len(saved)} 篇")

    finally:
        if driver:
            driver.quit()

    logger.info("\n" + "=" * 60)
    logger.info("爬取完成!")


if __name__ == "__main__":
    main()

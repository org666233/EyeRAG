#!/usr/bin/env python3
"""
中文医学网站爬虫 v3 - 修复版
"""

import re
import time
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
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


def fetch_page(url: str, timeout: int = 30) -> Optional[str]:
    """获取网页"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Connection': 'keep-alive',
    }
    import urllib.request
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            for enc in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
                try:
                    return content.decode(enc)
                except:
                    continue
            return content.decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning(f"获取失败: {e}")
        return None


# ============================================================
# 寻医问药网
# ============================================================

def crawl_xwyy():
    """爬取寻医问药网"""
    url = "https://jib.xywy.com/html/yanke.html"
    html = fetch_page(url)
    if not html:
        logger.error("无法获取页面")
        return []

    # 查找疾病链接 - 多种模式
    disease_urls = set()

    # 模式1: /yanke/xxx.html
    pattern1 = re.findall(r'href=["\'](/yanke/[^"\']+\.html)["\']', html)
    disease_urls.update(pattern1)

    # 模式2: jib.xywy.com/yanke/xxx
    pattern2 = re.findall(r'href=["\'](https?://jib\.xywy\.com/yanke/[^"\']+)["\']', html)
    disease_urls.update(pattern2)

    # 模式3: 相对路径 yanke/xxx
    pattern3 = re.findall(r'href=["\'](yanke/[^"\']+\.html)["\']', html)
    disease_urls.update(pattern3)

    # 转换为完整 URL
    full_urls = []
    for url_path in disease_urls:
        if url_path.startswith('http'):
            full_urls.append(url_path)
        elif url_path.startswith('/yanke/'):
            full_urls.append(f"https://jib.xywy.com{url_path}")
        elif url_path.startswith('yanke/'):
            full_urls.append(f"https://jib.xywy.com/{url_path}")

    full_urls = list(set(full_urls))
    logger.info(f"找到 {len(full_urls)} 个疾病链接")

    # 保存调试信息
    if full_urls:
        debug_file = BASE_DIR / "xwyy_urls.txt"
        debug_file.write_text('\n'.join(full_urls[:100]), encoding='utf-8')
        logger.info(f"链接列表已保存: {debug_file}")

    saved = []
    for i, article_url in enumerate(full_urls[:50], 1):
        logger.info(f"[{i}/{len(full_urls[:50])}] {article_url}")

        article_html = fetch_page(article_url)
        if not article_html:
            logger.info(f"  ❌ 获取失败")
            continue

        # 解析文章
        article_html = re.sub(r'<script[^>]*>.*?</script>', '', article_html, flags=re.DOTALL)
        article_html = re.sub(r'<style[^>]*>.*?</style>', '', article_html, flags=re.DOTALL)

        # 提取标题
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', article_html, re.DOTALL)
        title = re.sub(r'<[^>]+>', '', title_match.group(1) if title_match else "").strip()
        if not title:
            title_match = re.search(r'<title>(.*?)</title>', article_html)
            title = re.sub(r'<[^>]+>', '', title_match.group(1) if title_match else "未知").strip()

        # 提取正文 - 尝试多个选择器
        content = ""
        for pattern in [
            r'<div[^>]*class="jib-content"[^>]*>(.*?)</div>',
            r'<div[^>]*class="article-content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="content"[^>]*>(.*?)</div>',
            r'<article[^>]*>(.*?)</article>',
        ]:
            match = re.search(pattern, article_html, re.DOTALL)
            if match and len(match.group(1)) > 500:
                content = match.group(1)
                break

        if not content:
            logger.info(f"  ⚠️ 未找到正文内容")
            continue

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
            logger.info(f"  ⚠️ 内容过少 ({len(text)} chars)")
            continue

        # 提取疾病名
        disease = article_url.split('/')[-1].replace('.html', '').replace('.htm', '')

        article = Article(title=title, url=article_url, content=text,
                         disease=disease, source="xywy")

        # 保存
        safe_title = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', title)[:50]
        filename = f"{disease}_{safe_title}.txt"
        filepath = BASE_DIR / filename

        content_text = f"""---
source: xywy
title: {title}
url: {article_url}
disease: {disease}
type: medical_article
---

{text}
"""
        filepath.write_text(content_text, encoding='utf-8')
        saved.append(filepath)
        logger.info(f"  ✅ {title[:30]}... ({len(text)} chars)")

        time.sleep(1.5)

    return saved


# ============================================================
# 丁香园
# ============================================================

def crawl_dxy():
    """爬取丁香园 - Selenium 版本"""
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

        # 访问疾病列表页
        driver.get("https://www.dxy.com/diseases/list/yanke")
        time.sleep(5)

        # 获取页面源码分析
        page_source = driver.page_source

        # 保存调试
        debug_file = BASE_DIR / "dxy_page_source.html"
        debug_file.write_text(page_source[:50000], encoding='utf-8')
        logger.info(f"页面源码已保存: {debug_file}")

        # 分析链接模式
        links = re.findall(r'href=["\']([^"\']*disease[^"\']*)["\']', page_source)
        logger.info(f"找到 {len(links)} 个 disease 相关链接")

        if links:
            # 去重
            unique_links = list(set([l for l in links if 'dxy.com' in l or l.startswith('/')]))
            logger.info(f"去重后: {len(unique_links)} 个")

            # 保存链接
            links_file = BASE_DIR / "dxy_links.txt"
            links_file.write_text('\n'.join(unique_links[:100]), encoding='utf-8')
            logger.info(f"链接列表: {links_file}")

        # 尝试多种方式获取疾病链接
        disease_urls = []

        # 方式1: 直接从页面源码匹配
        disease_urls.extend(re.findall(r'href=["\'](/disease/[^"\']+)["\']', page_source))

        # 方式2: 查找 JavaScript 渲染的链接
        try:
            # 等待页面加载完成
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "a"))
            )

            # 获取所有链接
            elements = driver.find_elements(By.TAG_NAME, "a")
            for elem in elements:
                try:
                    href = elem.get_attribute('href')
                    if href and '/disease/' in href:
                        disease_urls.append(href)
                except:
                    pass
        except Exception as e:
            logger.warning(f"Selenium 获取链接失败: {e}")

        disease_urls = list(set(disease_urls))
        logger.info(f"总共找到 {len(disease_urls)} 个疾病链接")

        if not disease_urls:
            logger.warning("未找到疾病链接，请检查 debug 文件")
            return []

        # 爬取文章
        saved = []
        for i, article_url in enumerate(disease_urls[:30], 1):
            logger.info(f"[{i}/{len(disease_urls[:30])}] {article_url}")

            try:
                driver.get(article_url)
                time.sleep(2)

                title = driver.title.strip()

                # 尝试获取正文
                try:
                    content_elem = driver.find_element(By.CSS_SELECTOR,
                        ".article-content, .content, article, main, .main-content")
                    content = content_elem.text
                except:
                    content = driver.page_source
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = re.sub(r'\s+', ' ', content)

                if len(content) < 100:
                    continue

                disease = article_url.split('/')[-1]

                filename = f"dxy_{disease}.txt"
                filepath = BASE_DIR / filename

                content_text = f"""---
source: dxy
title: {title}
url: {article_url}
disease: {disease}
type: medical_article
---

{content}
"""
                filepath.write_text(content_text, encoding='utf-8')
                saved.append(filepath)
                logger.info(f"  ✅ ({len(content)} chars)")

            except Exception as e:
                logger.warning(f"  ❌ {e}")

            time.sleep(2)

        return saved

    finally:
        driver.quit()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["xywy", "dxy", "all"], default="xywy")
    args = parser.parse_args()

    if args.source in ["xywy", "all"]:
        logger.info("=" * 60)
        logger.info("爬取寻医问药网...")
        logger.info("=" * 60)
        saved = crawl_xwyy()
        logger.info(f"完成! 保存 {len(saved)} 篇")

    if args.source in ["dxy", "all"]:
        logger.info("=" * 60)
        logger.info("爬取丁香园...")
        logger.info("=" * 60)
        saved = crawl_dxy()
        logger.info(f"完成! 保存 {len(saved)} 篇")


if __name__ == "__main__":
    main()

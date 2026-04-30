#!/usr/bin/env python3
"""
从丁香园提取眼科疾病列表（使用 Selenium 获取渲染后的内容）
"""

import re
import time
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"


def get_diseases_from_rendered_page():
    """从渲染后的页面获取疾病列表"""

    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)

    try:
        logger.info("请在浏览器中登录丁香园...")
        input("登录完成后按 Enter 继续...")

        # 访问眼科疾病列表页
        logger.info("访问: https://www.dxy.com/diseases/list/yanke")
        driver.get("https://www.dxy.com/diseases/list/yanke")

        # 等待初始加载
        logger.info("等待页面加载...")
        time.sleep(5)

        # 滚动页面到底部，触发懒加载
        logger.info("滚动页面加载所有内容...")

        last_height = 0
        scroll_attempts = 0
        max_attempts = 15

        while scroll_attempts < max_attempts:
            # 滚动到底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # 检查高度是否变化
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
                logger.info(f"  高度不变，尝试 {scroll_attempts}/{max_attempts}")

                # 尝试点击"加载更多"按钮
                try:
                    buttons = driver.find_elements(By.TAG_NAME, "button")
                    for btn in buttons:
                        if "加载" in btn.text or "更多" in btn.text:
                            btn.click()
                            time.sleep(2)
                            logger.info("  点击了加载更多按钮")
                except:
                    pass
            else:
                scroll_attempts = 0
                logger.info(f"  页面高度变化: {last_height} -> {new_height}")

            last_height = new_height

        # 额外等待确保所有内容加载
        logger.info("等待内容完全加载...")
        time.sleep(3)

        # 保存页面源码（包含渲染后的内容）
        debug_file = BASE_DIR / "dxy_yanke_rendered.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        logger.info(f"渲染后的页面已保存: {debug_file}")
        logger.info(f"页面大小: {len(driver.page_source)} 字符")

        # 提取疾病链接
        disease_urls = set()
        all_links = driver.find_elements(By.TAG_NAME, "a")

        logger.info(f"找到 {len(all_links)} 个链接")

        for link in all_links:
            try:
                href = link.get_attribute('href')
                if href and '/disease/' in href and '/detail' in href:
                    disease_urls.add(href)
            except:
                pass

        logger.info(f"疾病详情页链接: {len(disease_urls)} 个")

        # 保存链接列表
        if disease_urls:
            urls_file = BASE_DIR / "dxy_yanke_disease_urls.txt"
            with open(urls_file, 'w', encoding='utf-8') as f:
                for url in sorted(disease_urls):
                    f.write(url + '\n')
            logger.info(f"疾病链接已保存: {urls_file}")
            logger.info(f"前 10 个链接:")
            for url in sorted(disease_urls)[:10]:
                logger.info(f"  {url}")

        # 尝试提取疾病名称
        disease_names = set()

        for link in all_links:
            try:
                text = link.text.strip()
                # 过滤条件：2-20个字符，不包含特殊字符
                if 2 < len(text) < 20 and re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9]+$', text):
                    if '/disease/' in (link.get_attribute('href') or ''):
                        disease_names.add(text)
            except:
                pass

        if disease_names:
            names_file = BASE_DIR / "dxy_yanke_disease_names.txt"
            with open(names_file, 'w', encoding='utf-8') as f:
                for name in sorted(disease_names):
                    f.write(name + '\n')
            logger.info(f"疾病名称已保存: {names_file}")
            logger.info(f"共 {len(disease_names)} 个名称")

        return disease_urls

    finally:
        driver.quit()


def main():
    logger.info("=" * 60)
    logger.info("丁香园眼科疾病列表提取工具")
    logger.info("=" * 60)

    disease_urls = get_diseases_from_rendered_page()

    logger.info("=" * 60)
    if disease_urls:
        logger.info(f"成功提取 {len(disease_urls)} 个疾病链接")
    else:
        logger.info("未能提取到疾病链接，请检查调试文件")


if __name__ == "__main__":
    main()

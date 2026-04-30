#!/usr/bin/env python3
"""
使用 Selenium 提取丁香园眼科疾病列表 - 点击所有首字母按钮
"""

import time
import re
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents" / "chinese_medical"

INITIAL_LETTERS = ['B', 'C', 'D', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'W', 'X', 'Y', 'Z']


def main():
    logger.info("启动浏览器...")

    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(options=options)

    try:
        logger.info("请在浏览器中登录丁香园...")
        input("登录后按 Enter 继续...")

        url = "https://dxy.com/diseases/3880"
        logger.info(f"访问: {url}")
        driver.get(url)

        # 等待页面加载
        logger.info("等待页面加载...")
        time.sleep(5)

        # 滚动到顶部
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        # 找到所有 tag-button 元素
        all_buttons = driver.find_elements(By.CSS_SELECTOR, ".tag-button")
        logger.info(f"找到 {len(all_buttons)} 个 tag-button 元素")

        disease_urls = set()

        for letter in INITIAL_LETTERS:
            try:
                # 直接用 JavaScript 点击按钮，避免被拦截
                click_script = f"""
                    var buttons = document.querySelectorAll('.tag-button');
                    for (var btn of buttons) {{
                        if (btn.textContent.trim() === '{letter}' && btn.classList.contains('active') === false) {{
                            btn.click();
                            return true;
                        }}
                    }}
                    return false;
                """
                
                clicked = driver.execute_script(click_script)
                
                if clicked:
                    logger.info(f"点击: {letter}")
                    time.sleep(2)  # 等待数据加载

                    # 滚动加载
                    for _ in range(3):
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(0.3)

                    # 获取页面源码并提取疾病链接
                    page_source = driver.page_source
                    pattern = r'https://dxy\.com/disease/\d+/detail'
                    matches = re.findall(pattern, page_source)
                    
                    for match in matches:
                        disease_urls.add(match)

                    logger.info(f"  {letter}: 本次 {len(matches)} 个, 累计 {len(disease_urls)} 个")
                else:
                    logger.info(f"未找到按钮: {letter}")

            except Exception as e:
                logger.info(f"  {letter} 出错: {type(e).__name__}: {e}")

        logger.info(f"\n总计找到 {len(disease_urls)} 个疾病链接")

        # 保存
        if disease_urls:
            urls_file = BASE_DIR / "dxy_yanke_diseases.txt"
            sorted_urls = sorted(disease_urls, key=lambda x: int(re.search(r'/disease/(\d+)/', x).group(1)))
            with open(urls_file, 'w') as f:
                for url in sorted_urls:
                    f.write(url + '\n')
            logger.info(f"已保存: {urls_file}")

            logger.info("\n所有疾病:")
            for url in sorted_urls:
                logger.info(f"  {url}")

    finally:
        driver.quit()
        logger.info("完成!")


if __name__ == "__main__":
    main()

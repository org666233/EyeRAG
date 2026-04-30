#!/Users/org/miniconda3/bin/python3
"""
中文眼科医学内容爬取脚本 v2

来源及保存目录：
  1. 中文维基百科（zh.wikipedia.org） →  data/documents/zhwiki/
  2. 百度百科（baike.baidu.com）      →  data/documents/baidubaike/
  3. 医脉通指南（guide.medlive.cn）   →  data/documents/medlive/
     ⚠ 医脉通使用 Selenium 无头浏览器，需要 Chrome 已安装

用法（必须用 miniconda Python，依赖 bs4 / selenium）：
  /Users/org/miniconda3/bin/python3 scripts/crawl_chinese_ophthalm.py
  /Users/org/miniconda3/bin/python3 scripts/crawl_chinese_ophthalm.py --source zhwiki
  /Users/org/miniconda3/bin/python3 scripts/crawl_chinese_ophthalm.py --source baidubaike
  /Users/org/miniconda3/bin/python3 scripts/crawl_chinese_ophthalm.py --source medlive
"""

import argparse
import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

# ────────────────────────────── 全局配置 ──────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent / "data" / "documents"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 眼科搜索词（覆盖疾病、检查、手术、症状）
OPHTHALM_TERMS = [
    # 常见疾病
    "青光眼", "白内障", "糖尿病视网膜病变", "黄斑变性", "干眼症",
    "视网膜脱离", "弱视", "斜视", "近视", "结膜炎",
    "角膜炎", "葡萄膜炎", "飞蚊症", "早产儿视网膜病变", "圆锥角膜",
    "视神经炎", "老视", "虹膜炎", "眼底出血", "玻璃体混浊",
    "泪囊炎", "睑腺炎", "翼状胬肉", "眼眶蜂窝织炎", "色觉障碍",
    # 检查/手术
    "光学相干断层扫描", "眼底检查", "视野检查", "白内障手术",
    "近视手术", "玻璃体切除术", "角膜移植", "青光眼手术",
    # 症状
    "视力下降", "眼压升高", "视野缺损", "畏光", "夜盲症",
]


# ────────────────────────────── 通用工具 ──────────────────────────────

def _get(url: str, session: requests.Session, delay: float = 1.2,
         timeout: int = 15, params: dict = None) -> Optional[requests.Response]:
    time.sleep(delay)
    for attempt in range(3):
        try:
            resp = session.get(url, headers=HEADERS, timeout=timeout, params=params)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            wait = 3 * (attempt + 1)
            logger.warning(f"  [{attempt+1}/3] {url[:60]}: {e}，等待 {wait}s")
            time.sleep(wait)
    return None


def _uid(text: str, n: int = 6) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:n]


def _safe(text: str, maxlen: int = 40) -> str:
    return re.sub(r"[^\w一-鿿\-]", "_", text)[:maxlen]


def _infer_disease(text: str) -> str:
    for t in OPHTHALM_TERMS:
        if t in text:
            return t
    return "眼科"


def _save(directory: Path, filename: str, content: str,
          source: str, title: str, url: str,
          disease: str = "眼科", doc_type: str = "article") -> bool:
    """统一保存（带 YAML 前置元数据），已存在则跳过。"""
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / filename
    if filepath.exists() and filepath.stat().st_size > 300:
        return False  # 静默跳过
    content = re.sub(r"\n{3,}", "\n\n", content).strip()
    if len(content) < 100:
        return False
    text = (
        f"---\nsource: {source}\ntitle: {title}\nurl: {url}\n"
        f"disease: {disease}\ntype: {doc_type}\nlanguage: zh\n---\n\n{content}\n"
    )
    filepath.write_text(text, encoding="utf-8")
    logger.info(f"  ✅ {filename}  ({len(content):,} 字)")
    return True


# ════════════════════════════════════════════════════════════════════
#  来源 1：中文维基百科
#  使用 Wikipedia API 获取纯文本，无需解析 HTML
# ════════════════════════════════════════════════════════════════════

class ZhWikiCrawler:
    """
    通过 Wikipedia API 搜索眼科词条，提取纯文本全文。
    - 无反爬，稳定可靠
    - 内容质量接近英文 Wikipedia，适合基础概念和疾病综述
    """

    SAVE_DIR = BASE_DIR / "zhwiki"
    API = "https://zh.wikipedia.org/w/api.php"

    def __init__(self):
        self.session = requests.Session()
        self._saved_titles: set[str] = set()

    def _search(self, keyword: str, limit: int = 8) -> list[str]:
        """搜索关键词，返回匹配的文章标题列表。"""
        resp = _get(self.API, self.session, delay=0.8, params={
            "action": "query", "list": "search",
            "srsearch": keyword, "srlimit": limit,
            "srprop": "titlesnippet", "format": "json",
        })
        if not resp:
            return []
        hits = resp.json().get("query", {}).get("search", [])
        return [h["title"] for h in hits]

    def _fetch_article(self, title: str) -> Optional[str]:
        """用 API extracts 获取文章纯文本（无需 HTML 解析）。"""
        resp = _get(self.API, self.session, delay=1.0, params={
            "action": "query", "prop": "extracts",
            "titles": title, "explaintext": True,
            "exsectionformat": "plain", "format": "json",
        })
        if not resp:
            return None
        pages = resp.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if page.get("pageid", -1) == -1:
                return None  # 页面不存在
            return page.get("extract", "")
        return None

    def crawl(self) -> int:
        logger.info("=" * 55)
        logger.info("来源 1/3  中文维基百科（zh.wikipedia.org）")
        saved = 0

        for term in OPHTHALM_TERMS:
            titles = self._search(term, limit=5)
            for title in titles:
                if title in self._saved_titles:
                    continue
                self._saved_titles.add(title)

                # 过滤明显不相关的标题（机构、地名等）
                skip_keywords = ["医院", "学会", "大学", "公司", "股份", "市", "县", "镇"]
                if any(k in title for k in skip_keywords):
                    continue

                text = self._fetch_article(title)
                if not text or len(text) < 200:
                    continue

                url = f"https://zh.wikipedia.org/wiki/{quote(title)}"
                fname = f"zhwiki_{_safe(title)}.txt"
                if _save(
                    self.SAVE_DIR, fname, text,
                    source="zhwiki", title=title, url=url,
                    disease=_infer_disease(title + text[:200]),
                    doc_type="encyclopedia",
                ):
                    saved += 1

        logger.info(f"  中文维基 完成，保存 {saved} 篇\n")
        return saved


# ════════════════════════════════════════════════════════════════════
#  来源 2：百度百科
#  结构稳定，内容口语化，覆盖患者常见问法
# ════════════════════════════════════════════════════════════════════

class BaiduBaikeCrawler:
    """
    百度百科（baike.baidu.com）眼科疾病词条。
    内容比维基更贴近中文患者表达（症状描述、日常护理语言）。
    """

    BASE = "https://baike.baidu.com/item/"
    SAVE_DIR = BASE_DIR / "baidubaike"

    # 精选词条（直接病名 → 对应百度百科URL末尾词）
    ARTICLES = [
        "青光眼", "白内障", "糖尿病视网膜病变", "黄斑变性", "干眼症",
        "视网膜脱离", "弱视", "斜视", "近视", "结膜炎",
        "角膜炎", "葡萄膜炎", "飞蚊症", "圆锥角膜", "视神经炎",
        "老视", "虹膜炎", "眼底出血", "泪囊炎", "睑腺炎",
        "翼状胬肉", "夜盲症", "色觉障碍", "早产儿视网膜病变",
        "光学相干断层扫描", "眼底检查", "视野检查",
        "白内障手术", "近视手术", "角膜移植",
    ]

    def __init__(self):
        self.session = requests.Session()

    def _fetch(self, term: str) -> Optional[str]:
        url = f"{self.BASE}{quote(term)}"
        resp = _get(url, self.session, delay=1.5)
        if not resp:
            return None

        soup = BeautifulSoup(resp.text, "lxml")

        # 百度百科正文：MARK_MODULE 类的元素包含实际段落文本
        marks = soup.find_all(class_="MARK_MODULE")
        texts = [
            m.get_text(" ", strip=True) for m in marks
            if len(m.get_text(strip=True)) > 20
            and not m.get_text(strip=True).startswith("[")
        ]

        if not texts:
            # 回退：找所有 <p> 标签
            texts = [p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 30]

        return "\n\n".join(texts) if texts else None

    def crawl(self) -> int:
        logger.info("=" * 55)
        logger.info("来源 2/3  百度百科（baike.baidu.com）")
        saved = 0

        for term in self.ARTICLES:
            content = self._fetch(term)
            if not content:
                logger.warning(f"  跳过（无内容）: {term}")
                continue

            url = f"{self.BASE}{quote(term)}"
            fname = f"baidubaike_{_safe(term)}.txt"
            if _save(
                self.SAVE_DIR, fname, content,
                source="baidubaike", title=term, url=url,
                disease=_infer_disease(term),
                doc_type="encyclopedia",
            ):
                saved += 1

        logger.info(f"  百度百科 完成，保存 {saved} 篇\n")
        return saved


# ════════════════════════════════════════════════════════════════════
#  来源 3：医脉通指南（Selenium）
#  获取中文临床指南的标题 + 制定机构 + 摘要
# ════════════════════════════════════════════════════════════════════

class MedLiveCrawler:
    """
    医脉通指南频道（guide.medlive.cn）。
    全文需登录/付费，但指南摘要（200-600字）可免费获取。
    对 RAG 检索场景已有价值（包含疾病名、推荐级别、关键数字）。
    使用 Selenium 无头浏览器绕过 JS 渲染。
    """

    SAVE_DIR = BASE_DIR / "medlive"
    SEARCH_URL = "https://guide.medlive.cn/search?q={}"

    KEYWORDS = [
        "青光眼", "白内障", "干眼症", "糖尿病视网膜", "黄斑变性",
        "近视防控", "角膜病", "视网膜", "弱视", "结膜炎",
        "葡萄膜炎", "眼底", "眼外伤", "泪道", "早产儿视网膜",
    ]

    def __init__(self):
        self._seen_urls: set[str] = set()
        self._driver = None

    def _get_driver(self):
        if self._driver:
            return self._driver
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        self._driver = webdriver.Chrome(options=opts)
        return self._driver

    def _search(self, keyword: str) -> list[dict]:
        """获取搜索结果页的指南链接列表。"""
        driver = self._get_driver()
        driver.get(self.SEARCH_URL.format(quote(keyword)))
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "lxml")

        items = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "/guideline/" not in href and "/guidelinesub/" not in href:
                continue
            if not href.startswith("http"):
                href = "https://guide.medlive.cn" + href
            title = a.get_text(strip=True)
            # 过滤掉太短或重复的
            if len(title) < 6 or href in self._seen_urls:
                continue
            # 去掉 title 里混入的多余文字（"会员可通过APP阅读" 等）
            title = re.sub(r"(会员可通过APP阅读|站内免费|有解读|有其他版本).*", "", title).strip()
            if len(title) < 6:
                continue
            self._seen_urls.add(href)
            items.append({"title": title, "url": href})

        logger.info(f"  医脉通 [{keyword}]: 找到 {len(items)} 条")
        return items

    def _fetch_guideline(self, url: str, title: str) -> Optional[str]:
        """抓取单个指南页，提取：标题 + 制定机构 + 摘要。"""
        driver = self._get_driver()
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "lxml")

        body_text = soup.get_text("\n", strip=True)
        lines = [l.strip() for l in body_text.split("\n") if l.strip() and len(l.strip()) > 5]

        # 去掉导航噪音
        noise = {"首页", "订阅", "指南", "机构", "会员", "专题", "指南云盘",
                 "MedSeeker", "登录/注册", "北京医脉互通公司 版权所有"}
        lines = [l for l in lines if l not in noise and not l.startswith("©") and "beian" not in l]

        # 取所有有效行，遇到付费墙标记则截断
        STOP = re.compile(
            r"(临床指南APP|由于版权|购买了|请联系医脉通|此功能仅限VIP|于\d{4}-\d{2}-\d{2}上传)"
        )
        content_lines = []
        for line in lines:
            if STOP.search(line):
                break
            if len(line) > 8:
                content_lines.append(line)

        return "\n".join(content_lines) if content_lines else None

    def quit(self):
        if self._driver:
            self._driver.quit()
            self._driver = None

    def crawl(self) -> int:
        logger.info("=" * 55)
        logger.info("来源 3/3  医脉通（guide.medlive.cn，Selenium）")
        saved = 0

        try:
            for kw in self.KEYWORDS:
                for item in self._search(kw):
                    content = self._fetch_guideline(item["url"], item["title"])
                    if not content:
                        continue
                    disease = _infer_disease(item["title"])
                    fname = f"medlive_{_safe(item['title'])}_{_uid(item['url'])}.txt"
                    if _save(
                        self.SAVE_DIR, fname, content,
                        source="medlive", title=item["title"], url=item["url"],
                        disease=disease, doc_type="guideline_abstract",
                    ):
                        saved += 1
        finally:
            self.quit()

        logger.info(f"  医脉通 完成，保存 {saved} 篇\n")
        return saved


# ════════════════════════════════════════════════════════════════════
#  主函数
# ════════════════════════════════════════════════════════════════════

def _summary():
    logger.info("=" * 55)
    logger.info("保存目录汇总：")
    for name, sub in [("中文维基", "zhwiki"), ("百度百科", "baidubaike"), ("医脉通", "medlive")]:
        d = BASE_DIR / sub
        if d.exists():
            files = list(d.glob("*.txt"))
            kb = sum(f.stat().st_size for f in files) // 1024
            logger.info(f"  {name:8s} → {d.name}/  ({len(files)} 个 txt，~{kb} KB)")


def main():
    parser = argparse.ArgumentParser(description="中文眼科医学内容爬取（v2）")
    parser.add_argument(
        "--source",
        choices=["zhwiki", "baidubaike", "medlive", "all"],
        default="all",
    )
    args = parser.parse_args()

    crawlers = {
        "zhwiki":      ZhWikiCrawler,
        "baidubaike":  BaiduBaikeCrawler,
        "medlive":     MedLiveCrawler,
    }
    sources = list(crawlers.keys()) if args.source == "all" else [args.source]

    total = 0
    for name in sources:
        try:
            n = crawlers[name]().crawl()
            total += n
        except KeyboardInterrupt:
            logger.info("用户中断")
            break
        except Exception as e:
            logger.error(f"  {name} 出错: {e}", exc_info=True)

    _summary()
    logger.info(f"全部完成，共保存 {total} 个文档")


if __name__ == "__main__":
    main()

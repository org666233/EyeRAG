"""
眼科知识库数据采集脚本 v2.0
数据来源（按权威性排序）:
  1. EyeWiki (AAO) - 美国眼科学会官方百科，最权威，免费 MediaWiki API
  2. PubMed Central (PMC) - 开放获取全文学术综述
  3. Wikipedia - 基础背景知识补充

使用方法:
  python scripts/download_data.py --source all
  python scripts/download_data.py --source eyewiki
  python scripts/download_data.py --source pmc --max 10
  python scripts/download_data.py --source wikipedia
"""

import os
import sys
import time
import json
import argparse
import requests
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data" / "documents"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================================
# EyeWiki (AAO) — 最高优先级
# 美国眼科学会官方眼科百科，内容由持证眼科医生撰写和审核
# =====================================================================
EYEWIKI_API = "https://eyewiki.aao.org/api.php"

# 综合覆盖：疾病 + 手术 + 检查 + 解剖 + 药物 + 儿童眼科 + 急诊
EYEWIKI_PAGES = [
    # ── 青光眼 ─────────────────────────────────────────────────
    "Glaucoma", "Open-angle glaucoma", "Angle-closure glaucoma",
    "Normal tension glaucoma", "Secondary glaucoma",
    "Glaucoma suspect", "Glaucomatous optic neuropathy",
    "Trabeculectomy", "Glaucoma drainage devices",
    "Selective laser trabeculoplasty", "Argon laser trabeculoplasty",
    "Intraocular pressure", "Ocular hypertension",
    "Visual field testing in glaucoma",

    # ── 白内障 ─────────────────────────────────────────────────
    "Cataract", "Age-related cataract", "Congenital cataract",
    "Posterior subcapsular cataract", "Nuclear sclerosis",
    "Phacoemulsification", "Extracapsular cataract extraction",
    "Intraocular lens", "Multifocal intraocular lens",
    "Posterior capsule opacification", "Cataract surgery complications",

    # ── 视网膜疾病 ────────────────────────────────────────────
    "Age-related macular degeneration", "Wet AMD", "Dry AMD",
    "Diabetic retinopathy", "Diabetic macular edema",
    "Retinal detachment", "Rhegmatogenous retinal detachment",
    "Central retinal artery occlusion", "Branch retinal artery occlusion",
    "Central retinal vein occlusion", "Branch retinal vein occlusion",
    "Retinitis pigmentosa", "Choroidal neovascularization",
    "Epiretinal membrane", "Macular hole",
    "Vitreous hemorrhage", "Posterior vitreous detachment",
    "Central serous chorioretinopathy", "Macular pucker",
    "Retinoblastoma", "Choroidal melanoma",
    "Retinopathy of prematurity",
    "Fluorescein angiography", "Optical coherence tomography",
    "Intravitreal injection",

    # ── 角膜与眼表 ───────────────────────────────────────────
    "Corneal ulcer", "Bacterial keratitis", "Viral keratitis",
    "Acanthamoeba keratitis", "Fungal keratitis",
    "Keratoconus", "Corneal ectasia",
    "Corneal dystrophy", "Fuchs endothelial dystrophy",
    "Corneal transplant", "Penetrating keratoplasty",
    "DSAEK", "DMEK",
    "Dry eye syndrome", "Meibomian gland dysfunction",
    "Blepharitis", "Conjunctivitis", "Allergic conjunctivitis",
    "Pterygium", "Pinguecula", "Recurrent corneal erosion",
    "Stevens-Johnson syndrome", "Ocular surface disease",

    # ── 屈光与近视 ───────────────────────────────────────────
    "Myopia", "High myopia", "Myopia control",
    "Hyperopia", "Astigmatism", "Presbyopia",
    "LASIK", "PRK", "SMILE", "Refractive surgery",
    "Orthokeratology",

    # ── 葡萄膜炎 ────────────────────────────────────────────
    "Uveitis", "Anterior uveitis", "Intermediate uveitis",
    "Posterior uveitis", "Panuveitis",
    "HLA-B27 associated uveitis", "Sarcoidosis and the eye",
    "Vogt-Koyanagi-Harada disease",

    # ── 神经眼科 ────────────────────────────────────────────
    "Optic neuritis", "Papilledema", "Optic nerve hypoplasia",
    "Ischemic optic neuropathy", "Optic atrophy",
    "Idiopathic intracranial hypertension",
    "Diplopia", "Third nerve palsy", "Sixth nerve palsy",
    "Horner syndrome", "Nystagmus",

    # ── 儿童眼科 ────────────────────────────────────────────
    "Amblyopia", "Strabismus", "Esotropia", "Exotropia",
    "Pediatric cataract", "Pediatric glaucoma",
    "Nasolacrimal duct obstruction",

    # ── 眼眶与眼睑 ──────────────────────────────────────────
    "Orbital cellulitis", "Thyroid eye disease", "Graves orbitopathy",
    "Chalazion", "Hordeolum", "Dacryocystitis",
    "Ptosis", "Entropion", "Ectropion",
    "Orbital tumor", "Cavernous hemangioma of the orbit",

    # ── 检查与诊断技术 ───────────────────────────────────────
    "Slit lamp examination", "Fundus examination",
    "Tonometry", "Gonioscopy", "Visual field test",
    "Electroretinography", "Humphrey visual field",
    "Corneal topography", "B-scan ultrasonography",

    # ── 解剖基础 ────────────────────────────────────────────
    "Retina", "Macula", "Fovea", "Optic nerve",
    "Cornea", "Lens (anatomy)", "Iris (anatomy)",
    "Ciliary body", "Choroid", "Sclera",
    "Vitreous body", "Aqueous humor",
    "Trabecular meshwork",

    # ── 药物 ────────────────────────────────────────────────
    "Anti-VEGF therapy", "Bevacizumab", "Ranibizumab",
    "Aflibercept", "Brolucizumab",
    "Prostaglandin analogs", "Beta-blockers in glaucoma",
    "Carbonic anhydrase inhibitors",
    "Corticosteroids in ophthalmology",
    "Topical antibiotics in ophthalmology",

    # ── 全身病眼部表现 ───────────────────────────────────────
    "Diabetic eye disease", "Hypertensive retinopathy",
    "Sickle cell retinopathy", "Lupus and the eye",
    "Multiple sclerosis and the eye",
]


def download_eyewiki(max_pages: Optional[int] = None) -> int:
    """
    通过 EyeWiki MediaWiki API 下载眼科知识条目。
    EyeWiki 是 AAO 官方眼科百科，内容由眼科医生撰写，可免费访问。
    """
    eyewiki_dir = DATA_DIR / "eyewiki"
    eyewiki_dir.mkdir(exist_ok=True)

    pages_to_fetch = EYEWIKI_PAGES
    if max_pages:
        pages_to_fetch = pages_to_fetch[:max_pages]

    print(f"\n[EyeWiki] 计划下载 {len(pages_to_fetch)} 个眼科知识条目...")
    downloaded = 0
    skipped = 0
    failed = 0

    for i, page_title in enumerate(pages_to_fetch, 1):
        safe_name = page_title.replace("/", "_").replace(" ", "_")
        out_file = eyewiki_dir / f"{safe_name}.txt"

        if out_file.exists() and out_file.stat().st_size > 200:
            skipped += 1
            continue

        try:
            resp = requests.get(
                EYEWIKI_API,
                params={
                    "action": "query",
                    "titles": page_title,
                    "prop": "extracts",
                    "explaintext": True,
                    "exsectionformat": "plain",
                    "format": "json",
                },
                timeout=30,
                headers={"User-Agent": "OphthalmologyRAGBot/1.0 (graduate thesis project)"},
            )
            resp.raise_for_status()
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            got_content = False
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    # EyeWiki 没有，尝试 Wikipedia fallback
                    print(f"  [{i:3d}] ⚠  {page_title} — EyeWiki无此条目，跳过")
                    failed += 1
                    got_content = True
                    break

                extract = page_data.get("extract", "")
                if len(extract) < 200:
                    print(f"  [{i:3d}] ⚠  {page_title} — 内容过短({len(extract)}字符)")
                    failed += 1
                    got_content = True
                    break

                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(f"Source: EyeWiki (American Academy of Ophthalmology)\n")
                    f.write(f"Title: {page_data.get('title', page_title)}\n")
                    f.write(f"URL: https://eyewiki.aao.org/wiki/{page_title.replace(' ', '_')}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(extract)

                size_kb = out_file.stat().st_size / 1024
                print(f"  [{i:3d}] ✅ {page_title} ({size_kb:.1f} KB)")
                downloaded += 1
                got_content = True

            if not got_content:
                failed += 1

            time.sleep(0.4)  # 礼貌请求间隔

        except requests.exceptions.ConnectionError:
            print(f"  [{i:3d}] ❌ {page_title} — 网络连接失败，跳过")
            failed += 1
            time.sleep(1)
        except Exception as e:
            print(f"  [{i:3d}] ❌ {page_title} — {e}")
            failed += 1

    print(f"\n[EyeWiki] 完成: 新下载 {downloaded} | 已有跳过 {skipped} | 失败 {failed}")
    return downloaded + skipped


# =====================================================================
# PubMed Central (PMC) — 开放获取全文学术综述
# =====================================================================
PMC_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PMC_BIOC_URL = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"

# 眼科核心领域 MeSH 综述查询
OPHTHO_QUERIES = [
    "glaucoma[MeSH Terms] AND review[Publication Type]",
    "cataract[MeSH Terms] AND review[Publication Type]",
    "macular degeneration[MeSH Terms] AND review[Publication Type]",
    "diabetic retinopathy[MeSH Terms] AND review[Publication Type]",
    "dry eye syndromes[MeSH Terms] AND review[Publication Type]",
    "retinal detachment[MeSH Terms] AND review[Publication Type]",
    "uveitis[MeSH Terms] AND review[Publication Type]",
    "myopia[MeSH Terms] AND review[Publication Type]",
    "corneal disease[MeSH Terms] AND review[Publication Type]",
    "amblyopia[MeSH Terms] AND review[Publication Type]",
    "keratoconus[MeSH Terms] AND review[Publication Type]",
    "optic neuritis[MeSH Terms] AND review[Publication Type]",
    "retinitis pigmentosa[MeSH Terms] AND review[Publication Type]",
    "strabismus[MeSH Terms] AND review[Publication Type]",
    "LASIK[Title/Abstract] AND review[Publication Type]",
]


def download_pmc_articles(max_per_query: int = 5, email: str = "graduate_project@example.com") -> int:
    pmc_dir = DATA_DIR / "pmc"
    pmc_dir.mkdir(exist_ok=True)

    print(f"\n[PMC] 开始搜索开放获取眼科综述文献...")
    all_pmcids = []

    for query in OPHTHO_QUERIES:
        try:
            resp = requests.get(
                PMC_SEARCH_URL,
                params={
                    "db": "pmc",
                    "term": query + " AND open access[filter]",
                    "retmax": max_per_query,
                    "retmode": "json",
                    "tool": "OphthalmologyRAG",
                    "email": email,
                },
                timeout=30,
            )
            resp.raise_for_status()
            ids = resp.json().get("esearchresult", {}).get("idlist", [])
            print(f"  {query[:55]}... → {len(ids)} 篇")
            all_pmcids.extend(ids)
            time.sleep(0.4)
        except Exception as e:
            print(f"  ❌ 查询失败: {e}")

    all_pmcids = list(set(all_pmcids))
    print(f"\n[PMC] 共找到 {len(all_pmcids)} 篇不重复文献，开始下载全文...")

    downloaded = 0
    for pmcid in all_pmcids:
        out_file = pmc_dir / f"PMC{pmcid}.txt"
        if out_file.exists() and out_file.stat().st_size > 500:
            downloaded += 1
            continue

        try:
            bioc_url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_text/PMC{pmcid}/unicode"
            resp = requests.get(bioc_url, timeout=60)

            if resp.status_code == 200 and len(resp.text) > 500:
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(f"Source: PubMed Central\n")
                    f.write(f"PMCID: PMC{pmcid}\n")
                    f.write(f"URL: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmcid}/\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(resp.text)

                size_kb = out_file.stat().st_size / 1024
                print(f"  ✅ PMC{pmcid} ({size_kb:.1f} KB)")
                downloaded += 1
            else:
                print(f"  ⚠  PMC{pmcid} 无全文 (HTTP {resp.status_code})")

            time.sleep(0.5)

        except Exception as e:
            print(f"  ❌ PMC{pmcid}: {e}")

    return downloaded


# =====================================================================
# Wikipedia 补充（弥补 EyeWiki 缺失的条目）
# =====================================================================
WIKI_SUPPLEMENT = [
    # EyeWiki 没有或内容较少的解剖 / 基础条目
    "Visual acuity", "Color blindness", "Accommodation (eye)",
    "Pupillary light reflex", "Extraocular muscles",
    "Lacrimal apparatus", "Visual cortex", "Visual pathway",
    "Phototransduction", "Rod cell", "Cone cell",
    "Photoreceptor cell", "Retinal ganglion cell",
    "Binocular vision", "Depth perception",
    # 手术与技术
    "Optical coherence tomography", "Fundus photography",
    "Slit lamp", "Indirect ophthalmoscope",
    "Laser photocoagulation",
    # 全身相关
    "Hypertensive retinopathy", "Wilson disease",
    "Marfan syndrome", "Down syndrome and the eye",
]


def download_wikipedia_supplement(pages: list = None) -> int:
    wiki_dir = DATA_DIR / "wikipedia"
    wiki_dir.mkdir(exist_ok=True)

    if pages is None:
        pages = WIKI_SUPPLEMENT

    print(f"\n[Wikipedia] 下载补充条目 ({len(pages)} 个)...")
    downloaded = 0

    for page_title in pages:
        safe_name = page_title.replace(" ", "_").replace("/", "_")
        out_file = wiki_dir / f"{safe_name}.txt"

        if out_file.exists() and out_file.stat().st_size > 200:
            downloaded += 1
            continue

        try:
            resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": page_title,
                    "prop": "extracts",
                    "explaintext": True,
                    "format": "json",
                },
                timeout=30,
                headers={"User-Agent": "OphthalmologyRAGBot/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

            pages_data = data.get("query", {}).get("pages", {})
            for pid, pdata in pages_data.items():
                if pid == "-1":
                    continue
                extract = pdata.get("extract", "")
                if len(extract) < 200:
                    continue

                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(f"Source: Wikipedia\n")
                    f.write(f"Title: {pdata.get('title', page_title)}\n")
                    f.write(f"URL: https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(extract)

                size_kb = out_file.stat().st_size / 1024
                print(f"  ✅ {page_title} ({size_kb:.1f} KB)")
                downloaded += 1

            time.sleep(0.3)

        except Exception as e:
            print(f"  ❌ {page_title}: {e}")

    return downloaded


# =====================================================================
# 主入口
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="眼科知识库数据下载脚本 v2.0")
    parser.add_argument(
        "--source",
        choices=["all", "pmc", "wikipedia"],
        default="wikipedia",
        help="数据来源（默认 wikipedia，国内稳定；pmc 需能访问 NCBI）",
    )
    parser.add_argument("--max", type=int, default=5, help="PMC 每个查询最大下载篇数")
    parser.add_argument("--email", default="graduate_project@example.com", help="NCBI API 邮箱")
    args = parser.parse_args()

    total = 0

    if args.source in ("all", "wikipedia"):
        n = download_wikipedia_supplement()
        total += n
        print(f"\n[Wikipedia] 共处理 {n} 个条目")

    if args.source in ("all", "pmc"):
        n = download_pmc_articles(max_per_query=args.max, email=args.email)
        total += n
        print(f"\n[PMC] 共下载 {n} 篇文章")

    print(f"\n{'='*55}")
    print(f"✅ 下载完成！文件保存至 {DATA_DIR}")
    for subdir in sorted(DATA_DIR.iterdir()):
        if subdir.is_dir():
            files = list(subdir.glob("*.txt")) + list(subdir.glob("*.pdf"))
            total_size = sum(f.stat().st_size for f in files) / 1024 / 1024
            print(f"  {subdir.name:12s}: {len(files):4d} 个文件  ({total_size:.1f} MB)")
    print(f"\n下一步: cd backend && python scripts/ingest.py --dir data/documents")


if __name__ == "__main__":
    main()

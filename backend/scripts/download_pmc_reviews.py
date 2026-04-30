"""
眼科知识库 - PMC 综述文章自动下载脚本 v2.0
根据专家整理的高质量眼科综述列表，自动从 PubMed Central 下载全文

v2.0 新增疾病方向:
  - 结膜炎 (Conjunctivitis)
  - 翼状胬肉 (Pterygium)
  - 角膜炎 (Keratitis)
  - 角膜移植 (Corneal Transplant)
  - 早产儿视网膜病变 (ROP)
  - 斜视 (Strabismus)
  - 甲状腺相关眼病 (Thyroid Eye Disease)
  - 视网膜动脉阻塞 (RAO)
  - 泪器疾病 (Lacrimal Disease)
  - 黄斑疾病 (Macular Hole, ERM)
  - 眼表疾病 (Ocular Surface Disease)
  - 眼睑疾病 (Eyelid Disease)
  - 糖尿病性黄斑水肿 (DME)

使用方法:
    python scripts/download_pmc_reviews.py          # 下载所有文章
    python scripts/download_pmc_reviews.py --priority 1  # 只下载优先级1（核心病种）
    python scripts/download_pmc_reviews.py --priority 2  # 优先级1-2（核心+重要）
    python scripts/download_pmc_reviews.py --list         # 仅列出文章，不下载
"""

import os
import sys
import time
import argparse
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data" / "documents" / "pmc"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class PMCArticle:
    """PMC 文章元数据"""
    title: str
    pmcid: str
    year: int
    disease: str
    priority: int  # 1=核心, 2=重要, 3=补充

    @property
    def url(self) -> str:
        return f"https://www.ncbi.nlm.nih.gov/pmc/articles/{self.pmcid}/"

    @property
    def filename(self) -> str:
        safe_title = self.title[:40].replace("/", "_").replace(":", "_").replace("?", "_")
        return f"{self.disease[:15]}_{self.pmcid}_{safe_title}.txt"


# =====================================================================
# 高质量眼科综述文章列表（按优先级排序）
# 来源: PMC (PubMed Central) - 开放获取全文
# =====================================================================
PMC_ARTICLES: List[PMCArticle] = [
    # ========== 优先级一：核心疾病 ==========
    # 青光眼 (Glaucoma)
    PMCArticle(
        title="Exploring Glaucoma: From Pathogenesis to Emerging Diagnostic and Management Strategies",
        pmcid="PMC12440647",
        year=2025,
        disease="glaucoma",
        priority=1
    ),
    PMCArticle(
        title="Glaucoma: Current and New Therapeutic Approaches",
        pmcid="PMC11429057",
        year=2024,
        disease="glaucoma",
        priority=1
    ),
    PMCArticle(
        title="New Insights into Glaucoma—An Editorial Review",
        pmcid="PMC12898623",
        year=2026,
        disease="glaucoma",
        priority=1
    ),
    PMCArticle(
        title="Global incidence and risk factors for glaucoma",
        pmcid="PMC11544525",
        year=2024,
        disease="glaucoma",
        priority=1
    ),
    PMCArticle(
        title="Glaucoma – state of the art and perspectives on treatment",
        pmcid="PMC4927811",
        year=2016,
        disease="glaucoma",
        priority=1
    ),

    # 糖尿病视网膜病变 (Diabetic Retinopathy)
    PMCArticle(
        title="Diabetic Retinopathy: A review on its pathophysiology and novel treatment modalities",
        pmcid="PMC11287547",
        year=2024,
        disease="diabetic_retinopathy",
        priority=1
    ),
    PMCArticle(
        title="Advancement in Understanding Diabetic Retinopathy: A Comprehensive Review",
        pmcid="PMC10739189",
        year=2023,
        disease="diabetic_retinopathy",
        priority=1
    ),
    PMCArticle(
        title="Diabetic Retinopathy (DR): Mechanisms, Current Therapies, and Emerging Strategies",
        pmcid="PMC11898816",
        year=2025,
        disease="diabetic_retinopathy",
        priority=1
    ),
    PMCArticle(
        title="Diabetic Retinopathy: Pathophysiology and Treatments",
        pmcid="PMC6032159",
        year=2018,
        disease="diabetic_retinopathy",
        priority=1
    ),

    # 年龄相关性黄斑变性 (AMD)
    PMCArticle(
        title="Age-related macular degeneration",
        pmcid="PMC12878645",
        year=2025,
        disease="amd",
        priority=1
    ),
    PMCArticle(
        title="Age-Related Macular Degeneration: A Review",
        pmcid="PMC12935482",
        year=2025,
        disease="amd",
        priority=1
    ),
    PMCArticle(
        title="Recent developments in age-related macular degeneration",
        pmcid="PMC5573066",
        year=2017,
        disease="amd",
        priority=1
    ),
    PMCArticle(
        title="Age-Related Macular Degeneration",
        pmcid="PMC9369215",
        year=2022,
        disease="amd",
        priority=1
    ),

    # 白内障 (Cataract)
    PMCArticle(
        title="Cataract: Advances in surgery and whether surgery remains the only treatment",
        pmcid="PMC10577864",
        year=2021,
        disease="cataract",
        priority=1
    ),
    PMCArticle(
        title="Cataract and surgery for cataract",
        pmcid="PMC1502210",
        year=2006,
        disease="cataract",
        priority=1
    ),
    PMCArticle(
        title="A Review of Laser-Assisted Versus Traditional Phacoemulsification",
        pmcid="PMC5449299",
        year=2017,
        disease="cataract",
        priority=1
    ),
    PMCArticle(
        title="Recent developments in cataract surgery",
        pmcid="PMC7729366",
        year=2020,
        disease="cataract",
        priority=1
    ),

    # 干眼症 (Dry Eye)
    PMCArticle(
        title="Dry Eye Disease: An Update on Changing Perspectives",
        pmcid="PMC11162257",
        year=2024,
        disease="dry_eye",
        priority=1
    ),
    PMCArticle(
        title="A review on recent advances in dry eye: Pathogenesis and management",
        pmcid="PMC3160069",
        year=2011,
        disease="dry_eye",
        priority=1
    ),
    PMCArticle(
        title="Dry Eye Syndrome",
        pmcid="PMC3306104",
        year=2012,
        disease="dry_eye",
        priority=1
    ),
    PMCArticle(
        title="The Pathophysiology, Diagnosis, and Treatment of Dry Eye Disease",
        pmcid="PMC4335585",
        year=2015,
        disease="dry_eye",
        priority=1
    ),

    # ========== 优先级二：重要疾病 ==========
    # 视网膜脱离 (Retinal Detachment)
    PMCArticle(
        title="Rhegmatogenous retinal detachment surgery: A review",
        pmcid="PMC12489960",
        year=2025,
        disease="retinal_detachment",
        priority=2
    ),
    PMCArticle(
        title="Retinal detachment",
        pmcid="PMC3940167",
        year=2014,
        disease="retinal_detachment",
        priority=2
    ),
    PMCArticle(
        title="Retinal detachment",
        pmcid="PMC3275330",
        year=2012,
        disease="retinal_detachment",
        priority=2
    ),

    # 角膜疾病 (Keratoconus)
    PMCArticle(
        title="Keratoconus: exploring fundamentals and future perspectives",
        pmcid="PMC10956165",
        year=2024,
        disease="keratoconus",
        priority=2
    ),
    PMCArticle(
        title="Keratoconus Diagnosis and Treatment: Recent Advances",
        pmcid="PMC10511017",
        year=2024,
        disease="keratoconus",
        priority=2
    ),
    PMCArticle(
        title="Keratoconus: A historical and prospective review",
        pmcid="PMC10697266",
        year=2024,
        disease="keratoconus",
        priority=2
    ),
    PMCArticle(
        title="Advances in the diagnosis and treatment of keratoconus",
        pmcid="PMC8246497",
        year=2021,
        disease="keratoconus",
        priority=2
    ),

    # 葡萄膜炎 (Uveitis) - 替换为新的可用文章
    PMCArticle(
        title="Non-biologic, steroid-sparing therapies for non-infectious uveitis",
        pmcid="PMC9621106",
        year=2022,
        disease="uveitis",
        priority=2
    ),
    PMCArticle(
        title="Corticosteroid implants for chronic non-infectious uveitis",
        pmcid="PMC5038923",
        year=2022,
        disease="uveitis",
        priority=2
    ),
    PMCArticle(
        title="The Use of Sustained Release Intravitreal Steroid Implants in Non-Infectious Uveitis",
        pmcid="PMC8800436",
        year=2022,
        disease="uveitis",
        priority=2
    ),

    # 视神经炎 (Optic Neuritis) - 替换为新的可用文章
    PMCArticle(
        title="Optic neuritis: an update on diagnosis and management",
        pmcid="PMC6013201",
        year=2018,
        disease="optic_neuritis",
        priority=2
    ),
    PMCArticle(
        title="Approach to optic neuritis: An update",
        pmcid="PMC8544067",
        year=2021,
        disease="optic_neuritis",
        priority=2
    ),

    # 近视 (Myopia) - 替换为新的可用文章
    PMCArticle(
        title="Myopia: a review of current evidence and treatment strategies",
        pmcid="PMC9971458",
        year=2023,
        disease="myopia",
        priority=2
    ),
    PMCArticle(
        title="Myopia Control: Are We Ready for an Evidence Based Approach?",
        pmcid="PMC11109072",
        year=2024,
        disease="myopia",
        priority=2
    ),
    PMCArticle(
        title="Effectiveness of myopia control interventions: A systematic review",
        pmcid="PMC10076805",
        year=2023,
        disease="myopia",
        priority=2
    ),

    # ========== 优先级三：补充病种 ==========
    # 视网膜静脉阻塞 (CRVO)
    PMCArticle(
        title="Central Retinal Vein Occlusion: A Review of Current Evidence-based Treatment",
        pmcid="PMC4759903",
        year=2016,
        disease="crvo",
        priority=3
    ),
    PMCArticle(
        title="Retinal vein occlusion: pathophysiology and treatment options",
        pmcid="PMC2915868",
        year=2010,
        disease="crvo",
        priority=3
    ),
    PMCArticle(
        title="Recent advances in understanding and managing retinal vein occlusions",
        pmcid="PMC5904724",
        year=2018,
        disease="crvo",
        priority=3
    ),

    # 斜视/弱视 (Strabismus/Amblyopia) - 替换为新的可用文章
    PMCArticle(
        title="Amblyopia: a review of current treatment approaches",
        pmcid="PMC9939563",
        year=2023,
        disease="amblyopia",
        priority=3
    ),
    PMCArticle(
        title="Current concepts in the management of amblyopia",
        pmcid="PMC2704537",
        year=2009,
        disease="amblyopia",
        priority=3
    ),

    # 睑缘炎 (Blepharitis) - 替换为新的可用文章
    PMCArticle(
        title="Blepharitis: a comprehensive review of diagnosis and treatment",
        pmcid="PMC9435396",
        year=2022,
        disease="blepharitis",
        priority=3
    ),
    PMCArticle(
        title="Diagnosis and management of blepharitis",
        pmcid="PMC6095371",
        year=2018,
        disease="blepharitis",
        priority=3
    ),
    PMCArticle(
        title="Uncommon Blepharitis",
        pmcid="PMC10856592",
        year=2024,
        disease="blepharitis",
        priority=3
    ),

    # 青光眼手术 (Glaucoma Surgery)
    PMCArticle(
        title="Minimally Invasive Glaucoma Surgery: A Review of the Literature",
        pmcid="PMC10443347",
        year=2023,
        disease="glaucoma_surgery",
        priority=3
    ),
    PMCArticle(
        title="Revisiting Results of Conventional Surgery: Trabeculectomy, MIGS",
        pmcid="PMC6743311",
        year=2019,
        disease="glaucoma_surgery",
        priority=3
    ),

    # 抗 VEGF 治疗
    PMCArticle(
        title="Current and Future Anti-VEGF Agents for Neovascular AMD",
        pmcid="PMC8488047",
        year=2021,
        disease="anti_vegf",
        priority=3
    ),
    PMCArticle(
        title="The role of anti-VEGF in the management of proliferative DR",
        pmcid="PMC6113746",
        year=2018,
        disease="anti_vegf",
        priority=3
    ),

    # 抗青光眼药物
    PMCArticle(
        title="Currently available Prostanoids for the Treatment of Glaucoma",
        pmcid="PMC10922870",
        year=2024,
        disease="glaucoma_medication",
        priority=3
    ),
    PMCArticle(
        title="Managing adverse effects of glaucoma medications",
        pmcid="PMC4025938",
        year=2014,
        disease="glaucoma_medication",
        priority=3
    ),

    # 眼外伤
    PMCArticle(
        title="Open Globe Injuries: Review of Evaluation, Management, and Surgical Pearls",
        pmcid="PMC9379121",
        year=2022,
        disease="ocular_trauma",
        priority=3
    ),
    PMCArticle(
        title="Management of open globe injury: a narrative review",
        pmcid="PMC11543839",
        year=2024,
        disease="ocular_trauma",
        priority=3
    ),

    # OCT
    PMCArticle(
        title="The Perspective of Using OCT in Ophthalmology: Present and Future",
        pmcid="PMC11854452",
        year=2025,
        disease="oct",
        priority=3
    ),
    PMCArticle(
        title="A review of optical coherence tomography angiography (OCTA)",
        pmcid="PMC5066513",
        year=2016,
        disease="oct",
        priority=3
    ),

    # ========== 优先级二：新增重要疾病 ==========
    # 结膜炎 (Conjunctivitis)
    PMCArticle(
        title="Conjunctivitis: A Systematic Review of Diagnosis and Treatment",
        pmcid="PMC4049531",
        year=2014,
        disease="conjunctivitis",
        priority=2
    ),
    PMCArticle(
        title="Bacterial conjunctivitis: a review of the evidence",
        pmcid="PMC3635545",
        year=2013,
        disease="conjunctivitis",
        priority=2
    ),
    PMCArticle(
        title="Topical ketotifen treatment for allergic conjunctivitis: a systematic review",
        pmcid="PMC9922628",
        year=2023,
        disease="conjunctivitis",
        priority=2
    ),

    # 翼状胬肉 (Pterygium)
    PMCArticle(
        title="Pterygium: pathophysiology and management",
        pmcid="PMC1860212",
        year=2006,
        disease="pterygium",
        priority=2
    ),
    PMCArticle(
        title="The use of antimetabolites as adjunctive therapy in the surgical treatment of pterygium",
        pmcid="PMC3497463",
        year=2013,
        disease="pterygium",
        priority=2
    ),

    # 角膜炎 (Keratitis)
    PMCArticle(
        title="Infectious keratitis: A review",
        pmcid="PMC9542356",
        year=2022,
        disease="keratitis",
        priority=2
    ),
    PMCArticle(
        title="Update on peripheral ulcerative keratitis",
        pmcid="PMC3363308",
        year=2012,
        disease="keratitis",
        priority=2
    ),
    PMCArticle(
        title="Recurrent corneal erosion: a comprehensive review",
        pmcid="PMC6376883",
        year=2019,
        disease="keratitis",
        priority=2
    ),

    # 角膜移植 (Corneal Transplant)
    PMCArticle(
        title="An Overview of Corneal Transplantation in the Past Decade",
        pmcid="PMC9955122",
        year=2023,
        disease="corneal_transplant",
        priority=2
    ),
    PMCArticle(
        title="Current Perspectives on Corneal Transplantation",
        pmcid="PMC8904759",
        year=2022,
        disease="corneal_transplant",
        priority=2
    ),
    PMCArticle(
        title="Evolving Techniques in Corneal Transplantation",
        pmcid="PMC4474142",
        year=2015,
        disease="corneal_transplant",
        priority=2
    ),

    # 早产儿视网膜病变 (ROP)
    PMCArticle(
        title="Retinopathy of Prematurity: A Review of Risk Factors and their Clinical Significance",
        pmcid="PMC6089661",
        year=2018,
        disease="rop",
        priority=2
    ),
    PMCArticle(
        title="Modifiable Risk Factors and Preventative Strategies for Severe Retinopathy of Prematurity",
        pmcid="PMC10224242",
        year=2023,
        disease="rop",
        priority=2
    ),

    # 斜视 (Strabismus)
    PMCArticle(
        title="Comitant strabismus: Perspectives, present and future",
        pmcid="PMC3729504",
        year=2013,
        disease="strabismus",
        priority=2
    ),
    PMCArticle(
        title="Recent Advances Clarifying the Etiologies of Strabismus",
        pmcid="PMC4437883",
        year=2015,
        disease="strabismus",
        priority=2
    ),
    PMCArticle(
        title="Minimally invasive strabismus surgery",
        pmcid="PMC4330290",
        year=2015,
        disease="strabismus",
        priority=2
    ),

    # 甲状腺相关眼病 (Thyroid Eye Disease)
    PMCArticle(
        title="An overview of thyroid eye disease",
        pmcid="PMC4655452",
        year=2014,
        disease="thyroid_eye_disease",
        priority=2
    ),
    PMCArticle(
        title="Thyroid-associated Ophthalmopathy",
        pmcid="PMC5384127",
        year=2017,
        disease="thyroid_eye_disease",
        priority=2
    ),
    PMCArticle(
        title="Recent developments in thyroid eye disease",
        pmcid="PMC509348",
        year=2004,
        disease="thyroid_eye_disease",
        priority=2
    ),

    # 视网膜动脉阻塞 (Retinal Artery Occlusion)
    PMCArticle(
        title="A review of the management of central retinal artery occlusion",
        pmcid="PMC9558462",
        year=2022,
        disease="rao",
        priority=2
    ),
    PMCArticle(
        title="A review of central retinal artery occlusion: clinical presentation and management",
        pmcid="PMC3682348",
        year=2013,
        disease="rao",
        priority=2
    ),

    # 泪器疾病 (Lacrimal Disease)
    PMCArticle(
        title="The Lacrimal Gland and Its Role in Dry Eye",
        pmcid="PMC4793137",
        year=2016,
        disease="lacrimal_disease",
        priority=2
    ),
    PMCArticle(
        title="Endoscopic and external dacryocystorhinostomy for lacrimal obstructions",
        pmcid="PMC10152216",
        year=2023,
        disease="lacrimal_disease",
        priority=2
    ),

    # 黄斑疾病 (Macular Disease)
    PMCArticle(
        title="Idiopathic Macular Hole: A Comprehensive Review of Its Pathogenesis",
        pmcid="PMC6556255",
        year=2019,
        disease="macular_hole",
        priority=2
    ),
    PMCArticle(
        title="Long-Term Outcomes After Idiopathic Epiretinal Membrane Surgery",
        pmcid="PMC7127775",
        year=2020,
        disease="epiretinal_membrane",
        priority=2
    ),

    # ========== 优先级三：已有病种补充 ==========
    # 替换原来失败的青光眼文章
    PMCArticle(
        title="The pathophysiology and treatment of glaucoma: a review",
        pmcid="PMC4020443",
        year=2014,
        disease="glaucoma",
        priority=1
    ),

    # 替换原来失败的糖尿病视网膜病变文章
    PMCArticle(
        title="Diabetic retinopathy: linear equation modeling of risk factors",
        pmcid="PMC10394655",
        year=2024,
        disease="diabetic_retinopathy",
        priority=1
    ),

    # 替换原来失败的葡萄膜炎文章
    PMCArticle(
        title="Non-biologic, steroid-sparing therapies for non-infectious uveitis",
        pmcid="PMC9621106",
        year=2022,
        disease="uveitis",
        priority=2
    ),
    PMCArticle(
        title="Corticosteroid implants for chronic non-infectious uveitis",
        pmcid="PMC5038923",
        year=2022,
        disease="uveitis",
        priority=2
    ),

    # 替换原来失败的视神经炎文章
    PMCArticle(
        title="Optic neuritis: an update on diagnosis and management",
        pmcid="PMC6013201",
        year=2018,
        disease="optic_neuritis",
        priority=2
    ),

    # 替换原来失败的近视文章
    PMCArticle(
        title="Myopia: a review of current evidence and treatment strategies",
        pmcid="PMC9971458",
        year=2023,
        disease="myopia",
        priority=2
    ),

    # 替换原来失败的斜视/弱视文章
    PMCArticle(
        title="Amblyopia: a review of current treatment approaches",
        pmcid="PMC9939563",
        year=2023,
        disease="amblyopia",
        priority=3
    ),

    # 替换原来失败的睑缘炎文章
    PMCArticle(
        title="Blepharitis: a comprehensive review of diagnosis and treatment",
        pmcid="PMC9435396",
        year=2022,
        disease="blepharitis",
        priority=3
    ),

    # 眼表疾病综合 (Ocular Surface Disease)
    PMCArticle(
        title="Inflammation and dry eye disease—where are we?",
        pmcid="PMC9091897",
        year=2022,
        disease="ocular_surface",
        priority=3
    ),

    # 眼睑疾病 (Eyelid Disease)
    PMCArticle(
        title="Cosmetic blepharoplasty and dry eye disease: a review",
        pmcid="PMC7154208",
        year=2020,
        disease="eyelid_disease",
        priority=3
    ),

    # 白内障手术并发症 (Cataract Surgery Complications)
    PMCArticle(
        title="Posterior capsule opacification: a review of prevention and treatment",
        pmcid="PMC8968330",
        year=2022,
        disease="cataract_complications",
        priority=3
    ),

    # 糖尿病性黄斑水肿 (DME)
    PMCArticle(
        title="Diabetic macular edema: current and emerging therapies",
        pmcid="PMC9039941",
        year=2022,
        disease="dme",
        priority=3
    ),

    # ========== 优先级三：检查诊断与药物（新增） ==========
    # 视网膜静脉阻塞 (RVO)
    PMCArticle(
        title="The Diagnosis and Treatment of Branch Retinal Vein Occlusions: An Update",
        pmcid="PMC11763247",
        year=2025,
        disease="retinal_vein_occlusion",
        priority=3
    ),
    PMCArticle(
        title="Central Retinal Vein Occlusion: A Review of Current Evidence-based Treatment Options",
        pmcid="PMC4759903",
        year=2016,
        disease="retinal_vein_occlusion",
        priority=3
    ),
    PMCArticle(
        title="Recent advances in understanding and managing retinal vein occlusions",
        pmcid="PMC5904724",
        year=2018,
        disease="retinal_vein_occlusion",
        priority=3
    ),

    # 光学相干断层扫描 (OCT)
    PMCArticle(
        title="The Perspective of Using Optical Coherence Tomography in Ophthalmology: Present and Future Applications",
        pmcid="PMC11854452",
        year=2024,
        disease="oct",
        priority=2
    ),
    PMCArticle(
        title="Advances in OCT Angiography",
        pmcid="PMC11905608",
        year=2025,
        disease="oct",
        priority=3
    ),
    PMCArticle(
        title="A review of optical coherence tomography angiography (OCTA)",
        pmcid="PMC5066513",
        year=2017,
        disease="oct",
        priority=3
    ),

    # 视野检查
    PMCArticle(
        title="Central visual field in glaucoma: An updated review",
        pmcid="PMC11488810",
        year=2025,
        disease="visual_field",
        priority=3
    ),
    PMCArticle(
        title="Visual field patterns in glaucoma: A systematic review",
        pmcid="PMC11811403",
        year=2025,
        disease="visual_field",
        priority=3
    ),
    PMCArticle(
        title="Visual fields interpretation in glaucoma: a focus on static automated perimetry",
        pmcid="PMC3678209",
        year=2013,
        disease="visual_field",
        priority=3
    ),

    # 屈光手术 (LASIK, SMILE, PRK)
    PMCArticle(
        title="Small Incision Lenticule Extraction (SMILE) versus Femtosecond Laser-Assisted In Situ Keratomileusis (FS-LASIK) for Myopia: A Systematic Review and Meta-Analysis",
        pmcid="PMC4930219",
        year=2016,
        disease="refractive_surgery",
        priority=3
    ),
    PMCArticle(
        title="Three-year outcomes of small incision lenticule extraction (SMILE) and femtosecond laser-assisted laser in situ keratomileusis (FS-LASIK) for myopia and myopic astigmatism",
        pmcid="PMC6691872",
        year=2019,
        disease="refractive_surgery",
        priority=3
    ),
    PMCArticle(
        title="Comparison of visual quality and optical zones after TransPRK, SMILE, and FS-LASIK myopia correction procedures",
        pmcid="PMC12487276",
        year=2025,
        disease="refractive_surgery",
        priority=3
    ),
    PMCArticle(
        title="Review of Corneal Biomechanical Properties Following LASIK and SMILE for Myopia and Myopic Astigmatism",
        pmcid="PMC6062908",
        year=2018,
        disease="refractive_surgery",
        priority=3
    ),

    # 抗VEGF药物
    PMCArticle(
        title="Anti-VEGF treatment for macular conditions",
        pmcid="PMC11938191",
        year=2025,
        disease="anti_vegf",
        priority=2
    ),
    PMCArticle(
        title="Current and Future Anti-VEGF Agents for Neovascular Age-Related Macular Degeneration",
        pmcid="PMC8488047",
        year=2022,
        disease="anti_vegf",
        priority=2
    ),
    PMCArticle(
        title="Aflibercept, Bevacizumab, or Ranibizumab for Diabetic Macular Edema",
        pmcid="PMC4422053",
        year=2016,
        disease="anti_vegf",
        priority=3
    ),

    # 青光眼药物治疗
    PMCArticle(
        title="Currently available Prostanoids for the Treatment of Glaucoma and Ocular Hypertension: A review",
        pmcid="PMC10922870",
        year=2024,
        disease="glaucoma_medication",
        priority=2
    ),
    PMCArticle(
        title="Current Medical Therapy and Future Trends in the Management of Glaucoma Treatment",
        pmcid="PMC7391108",
        year=2020,
        disease="glaucoma_medication",
        priority=2
    ),
    PMCArticle(
        title="Managing adverse effects of glaucoma medications",
        pmcid="PMC4025938",
        year=2015,
        disease="glaucoma_medication",
        priority=3
    ),

    # 弱视治疗
    PMCArticle(
        title="Current Management of Childhood Amblyopia",
        pmcid="PMC6911788",
        year=2020,
        disease="amblyopia",
        priority=2
    ),
    PMCArticle(
        title="Efficacy of Amblyopia Treatments in Children Up to Seven Years Old: A Systematic Review",
        pmcid="PMC11034898",
        year=2024,
        disease="amblyopia",
        priority=3
    ),
    PMCArticle(
        title="Management of amblyopia in pediatric patients: Current insights",
        pmcid="PMC8727565",
        year=2022,
        disease="amblyopia",
        priority=3
    ),

    # 甲状腺相关眼病 (Thyroid Eye Disease)
    PMCArticle(
        title="2022 Update on Clinical Management of Graves' Disease and Thyroid Eye Disease",
        pmcid="PMC9174594",
        year=2022,
        disease="thyroid_eye_disease",
        priority=2
    ),
    PMCArticle(
        title="Management of thyroid eye disease: a Consensus Statement by the American Thyroid Association and the European Thyroid Association",
        pmcid="PMC9727317",
        year=2022,
        disease="thyroid_eye_disease",
        priority=2
    ),

    # 角膜炎 (Keratitis)
    PMCArticle(
        title="Infectious Keratitis Management: 10-Year Update",
        pmcid="PMC12429233",
        year=2025,
        disease="keratitis",
        priority=2
    ),
    PMCArticle(
        title="Infectious keratitis: A review",
        pmcid="PMC9542356",
        year=2023,
        disease="keratitis",
        priority=2
    ),
    PMCArticle(
        title="Infectious keratitis: an update on epidemiology, causative microorganisms, risk factors, and antimicrobial resistance",
        pmcid="PMC8102486",
        year=2021,
        disease="keratitis",
        priority=3
    ),

    # 眼底血管造影与 OCT-A
    PMCArticle(
        title="Role of optical coherence tomography-angiography in diabetes mellitus: Utility in diabetic retinopathy",
        pmcid="PMC8725072",
        year=2022,
        disease="imaging",
        priority=3
    ),
    PMCArticle(
        title="Imaging Modalities for Assessing the Vascular Component of Diabetic Retinal Disease",
        pmcid="PMC10837643",
        year=2024,
        disease="imaging",
        priority=3
    ),
    PMCArticle(
        title="Pearls and Pitfalls of Optical Coherence Tomography Angiography Imaging: A Review",
        pmcid="PMC6513942",
        year=2019,
        disease="imaging",
        priority=3
    ),

    # 斜视手术
    PMCArticle(
        title="Adjustable Sutures in the Treatment of Strabismus",
        pmcid="PMC10187043",
        year=2023,
        disease="strabismus",
        priority=3
    ),
    PMCArticle(
        title="Analysis of Strabismus Surgical Outcomes: A Retrospective Study of 2269 Cases",
        pmcid="PMC12291608",
        year=2025,
        disease="strabismus",
        priority=3
    ),

    # 眼外伤
    PMCArticle(
        title="Management of open globe injury: a narrative review",
        pmcid="PMC11543839",
        year=2024,
        disease="ocular_trauma",
        priority=2
    ),
    PMCArticle(
        title="Open Globe Injuries: Review of Evaluation, Management, and Surgical Pearls",
        pmcid="PMC9379121",
        year=2022,
        disease="ocular_trauma",
        priority=3
    ),

    # 视网膜色素变性 (RP)
    PMCArticle(
        title="Genetic Therapies for Retinitis Pigmentosa: Current Breakthroughs and Future Directions",
        pmcid="PMC12387042",
        year=2025,
        disease="retinitis_pigmentosa",
        priority=2
    ),
    PMCArticle(
        title="Voretigene Neparvovec in Retinal Diseases: A Review of the Current Clinical Evidence",
        pmcid="PMC7671481",
        year=2021,
        disease="retinitis_pigmentosa",
        priority=3
    ),

    # 近视控制 (Myopia Control)
    PMCArticle(
        title="Efficacy and safety of orthokeratology sequentially combined with escalating atropine concentrations for myopia control in children",
        pmcid="PMC12592541",
        year=2025,
        disease="myopia_control",
        priority=3
    ),
    PMCArticle(
        title="The Combined Effect of Low-dose Atropine with Orthokeratology in Pediatric Myopia Control",
        pmcid="PMC7465046",
        year=2020,
        disease="myopia_control",
        priority=3
    ),

    # 前房角镜检查 (Gonioscopy)
    PMCArticle(
        title="Gonioscopy skills and techniques",
        pmcid="PMC8862628",
        year=2022,
        disease="gonioscopy",
        priority=3
    ),

    # 中心性浆液性脉络膜视网膜病变 (CSC)
    PMCArticle(
        title="Current Pharmacological Treatment Options for Central Serous Chorioretinopathy: A Review",
        pmcid="PMC7597965",
        year=2020,
        disease="csc",
        priority=3
    ),
    PMCArticle(
        title="Management of chronic central serous chorioretinopathy",
        pmcid="PMC6256894",
        year=2018,
        disease="csc",
        priority=3
    ),

    # 青光眼手术 (Glaucoma Surgery)
    PMCArticle(
        title="Minimally Invasive Glaucoma Surgery",
        pmcid="PMC10539010",
        year=2024,
        disease="glaucoma_surgery",
        priority=2
    ),
    PMCArticle(
        title="Minimally Invasive Glaucoma Surgery: A Review of the Literature",
        pmcid="PMC10443347",
        year=2023,
        disease="glaucoma_surgery",
        priority=3
    ),
    PMCArticle(
        title="Comparison of tube shunt implantation and trabeculectomy for glaucoma: a systematic review and meta-analysis",
        pmcid="PMC10273552",
        year=2023,
        disease="glaucoma_surgery",
        priority=3
    ),
]


def download_article(article: PMCArticle, timeout: int = 60) -> bool:
    """
    下载单篇文章的全文
    优先使用 PMC OA套件 API (api.literome.org)，失败则用 HTML 解析
    """
    out_file = DATA_DIR / article.filename

    # 跳过已下载且文件大小 > 1KB 的
    if out_file.exists() and out_file.stat().st_size > 1024:
        return True

    # 尝试方案一：PMC OA套件 API（最干净，返回纯文本）
    if download_via_pmcapi(article, timeout):
        return True

    # 尝试方案二：HTML 页面解析
    if download_html_fallback(article, timeout):
        return True

    print(f"  ❌ 全部方案失败: {article.pmcid}")
    return False


def download_via_pmcapi(article: PMCArticle, timeout: int = 60) -> bool:
    """方案一：使用 PMC BioC API 获取纯文本（修正版）"""
    out_file = DATA_DIR / article.filename
    headers = {
        "User-Agent": "OphthalmologyRAG/1.0 (graduate thesis project)"
    }

    # BioC API 正确格式（去掉多余的斜杠）
    bioc_url = (
        f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi"
        f"/BioC_text/{article.pmcid}/unicode"
    )

    try:
        resp = requests.get(bioc_url, timeout=timeout, headers=headers)

        if resp.status_code == 200 and len(resp.text) > 500:
            # 检查是否返回的是错误页面（包含 "[Error]" 字符串）
            if "[Error]" in resp.text or "<html" in resp.text[:200].lower():
                return False

            with open(out_file, "w", encoding="utf-8") as f:
                f.write(f"Source: PubMed Central (PMC)\n")
                f.write(f"PMCID: {article.pmcid}\n")
                f.write(f"Title: {article.title}\n")
                f.write(f"URL: {article.url}\n")
                f.write(f"Year: {article.year}\n")
                f.write(f"Disease: {article.disease}\n")
                f.write(f"Priority: {article.priority}\n")
                f.write("=" * 60 + "\n\n")
                f.write(resp.text)

            size_kb = out_file.stat().st_size / 1024
            print(f"  ✅ [BioC] {article.pmcid} {article.title[:45]}... ({size_kb:.1f} KB)")
            return True

        return False

    except requests.exceptions.Timeout:
        print(f"  ⏰ 超时: {article.pmcid}")
        return False
    except Exception as e:
        print(f"  ⚠  API 失败: {article.pmcid} - {e}")
        return False


def download_html_fallback(article: PMCArticle, timeout: int = 60) -> bool:
    """方案二：直接请求 PMC 页面，精准提取正文"""
    out_file = DATA_DIR / article.filename

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

        resp = requests.get(article.url, timeout=timeout, headers=headers)
        if resp.status_code != 200:
            return False

        import re

        html = resp.text

        # 尝试提取 <article> 或 <div id="article"> 标签内的内容
        article_match = re.search(
            r'<article[^>]*>(.*?)</article>',
            html,
            re.DOTALL | re.IGNORECASE
        )

        if not article_match:
            # 备选：找 .t-content 或 .body-content 或 #content 的 div
            for selector in ['class="t-content"', 'class="body-content"',
                             'id="article-content"', 'class="content-body"']:
                m = re.search(
                    rf'<div[^>]*{re.escape(selector)}[^>]*>(.*?)</div>',
                    html, re.DOTALL | re.IGNORECASE
                )
                if m:
                    article_match = m
                    break

        if not article_match:
            return False

        content = article_match.group(1)

        # 移除不需要的标签块
        for pattern in [
            r'<script[^>]*>.*?</script>',
            r'<style[^>]*>.*?</style>',
            r'<nav[^>]*>.*?</nav>',
            r'<footer[^>]*>.*?</footer>',
            r'<aside[^>]*>.*?</aside>',
            r'<!--.*?-->',
            r'<form[^>]*>.*?</form>',
        ]:
            content = re.sub(pattern, '', content, flags=re.DOTALL | re.IGNORECASE)

        # 去除所有 HTML 标签，保留纯文本
        text = re.sub(r'<[^>]+>', ' ', content)

        # 清理特殊实体
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        text = text.replace('&rsquo;', "'")
        text = text.replace('&lsquo;', "'")
        text = text.replace('&rdquo;', '"')
        text = text.replace('&ldquo;', '"')

        # 清理多余空白
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        if len(text) < 500:
            print(f"  ⚠  内容过短: {article.pmcid} ({len(text)} chars)")
            return False

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(f"Source: PubMed Central (PMC)\n")
            f.write(f"PMCID: {article.pmcid}\n")
            f.write(f"Title: {article.title}\n")
            f.write(f"URL: {article.url}\n")
            f.write(f"Year: {article.year}\n")
            f.write(f"Disease: {article.disease}\n")
            f.write(f"Priority: {article.priority}\n")
            f.write("=" * 60 + "\n\n")
            f.write(text)

        size_kb = out_file.stat().st_size / 1024
        print(f"  ✅ [HTML] {article.pmcid} {article.title[:45]}... ({size_kb:.1f} KB)")
        return True

    except Exception as e:
        print(f"  ❌ HTML 失败: {article.pmcid} - {e}")
        return False


def list_articles(priority_filter: Optional[int] = None):
    """列出所有文章"""
    print("\n" + "=" * 70)
    print("眼科 PMC 综述文章列表")
    print("=" * 70)

    # 按优先级分组
    priority_names = {1: "⭐⭐⭐ 核心", 2: "⭐⭐ 重要", 3: "⭐ 补充"}

    for p in [1, 2, 3]:
        if priority_filter and priority_filter != p:
            continue

        articles = [a for a in PMC_ARTICLES if a.priority == p]
        if not articles:
            continue

        print(f"\n{priority_names[p]} ({len(articles)} 篇)")
        print("-" * 70)

        for i, art in enumerate(articles, 1):
            year_str = str(art.year) if art.year > 0 else "N/A"
            print(f"  {i:2d}. [{art.pmcid}] {art.title[:55]}...")
            print(f"      病种: {art.disease} | 年份: {year_str}")
            print(f"      链接: {art.url}")
            print()

    print("=" * 70)


def download_all(priority: Optional[int] = None, delay: float = 0.5):
    """下载所有或指定优先级的文章"""


    articles = PMC_ARTICLES
    if priority:
        articles = [a for a in articles if a.priority <= priority]

    print(f"\n开始下载 {len(articles)} 篇文章...")
    print(f"保存目录: {DATA_DIR}")
    print(f"请求间隔: {delay}s")
    print("-" * 60)

    success = 0
    skipped = 0
    failed = 0

    for i, article in enumerate(articles, 1):
        out_file = DATA_DIR / article.filename

        # 检查是否已下载且内容有效（不是错误文件）
        if out_file.exists() and out_file.stat().st_size > 1024:
            # 检查文件内容是否是错误信息
            try:
                with open(out_file, "r", encoding="utf-8", errors="ignore") as f:
                    first_chars = f.read(200)
                if "[Error]" not in first_chars and "Format of the path" not in first_chars:
                    print(f"  ➡️  跳过（已存在）: {article.title[:50]}...")
                    skipped += 1
                    continue
                else:
                    print(f"  🗑️  重新下载（错误文件）: {article.title[:50]}...")
            except Exception:
                pass

        print(f"  [{i:2d}/{len(articles)}] ", end="", flush=True)

        if download_article(article):
            success += 1
        else:
            failed += 1

        time.sleep(delay)  # 礼貌请求间隔

    # 统计
    print("\n" + "=" * 60)
    print("下载完成!")
    print(f"  ✅ 成功: {success}")
    print(f"  ➡️  跳过: {skipped}")
    print(f"  ❌ 失败: {failed}")
    print(f"\n保存目录: {DATA_DIR}")

    # 显示各病种统计
    print("\n各病种文章数:")
    from collections import Counter
    disease_counts = Counter(a.disease for a in articles)
    for disease, count in sorted(disease_counts.items()):
        print(f"  {disease:20s}: {count} 篇")

    return success, skipped, failed


def main():
    parser = argparse.ArgumentParser(
        description="眼科知识库 PMC 综述文章下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/download_pmc_reviews.py --list        # 列出所有文章
  python scripts/download_pmc_reviews.py               # 下载全部文章
  python scripts/download_pmc_reviews.py --priority 1   # 只下载核心病种
  python scripts/download_pmc_reviews.py --priority 2   # 下载核心+重要
  python scripts/download_pmc_reviews.py --delay 1.0   # 延长请求间隔
        """
    )
    parser.add_argument("--list", action="store_true", help="仅列出文章，不下载")
    parser.add_argument("--priority", type=int, choices=[1, 2, 3],
                        help="下载优先级 (1=核心, 2=重要, 3=补充)")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="请求间隔秒数 (默认 0.5)")
    args = parser.parse_args()

    if args.list:
        list_articles(args.priority)
    else:
        download_all(priority=args.priority, delay=args.delay)
        print("\n下一步: python scripts/ingest.py --dir data/documents")


if __name__ == "__main__":
    main()

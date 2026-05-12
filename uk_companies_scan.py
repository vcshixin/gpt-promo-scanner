#!/usr/bin/env python3
"""UK Companies House 全量公司 → ChatGPT Team 促销码扫描

流程:
  1. 读取 BasicCompanyData CSV (5M+ 公司)
  2. 过滤: Active + 相关 SIC (Tech/IT/AI/Consulting)
  3. 归一化公司名 → base name
  4. 生成候选码 (base × 40 国家 + bare)
  5. 分批 eligibility check
  6. 增量保存结果

用法:
  python3 uk_companies_scan.py
  python3 uk_companies_scan.py --resume
"""
import csv
import io
import json
import os
import random
import re
import sys
import time
import zipfile
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import discover_codes as dc

ZIP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BasicCompanyData.zip")
OUTPUT_DIR = config.get_output_dir()
PROGRESS_FILE = os.path.join(OUTPUT_DIR, ".uk_progress.json")
RESULTS_FILE = os.path.join(OUTPUT_DIR, "uk_results.json")
BASES_FILE = os.path.join(OUTPUT_DIR, "uk_bases.txt")

# ============================================================
# SIC codes 相关 (Tech / IT / AI / Software / Consulting)
# ============================================================

TECH_SIC_PREFIXES = [
    "58",   # Publishing
    "61",   # Telecommunications
    "62",   # Computer programming, consultancy
    "63",   # Information service activities
    "72",   # Scientific R&D
]

TECH_SIC_CODES = {
    "58210", "58290",  # Software publishing
    "62010", "62011", "62012", "62020", "62030", "62090",  # IT services
    "63110", "63120",  # Data processing, web portals
    "63910", "63990",  # Other information services
    "70210", "70220", "70229",  # Management consultancy
    "72110", "72190", "72200",  # R&D
    "73110", "73120",  # Advertising
    "74100",            # Specialised design
    "74201", "74202", "74209",  # Photography
    "74901", "74909",  # Other professional activities
    "77320",            # Renting of construction machinery
    "77400",            # Leasing of IP
    "85590",            # Other education
    "85600",            # Educational support
    "95110",            # Repair of computers
}

# 公司名中包含这些词的也算 tech 公司
TECH_KEYWORDS = [
    "ai", "artificial", "intelligence", "machine learning",
    "software", "tech", "digital", "cloud", "data",
    "cyber", "security", "analytics", "automation",
    "blockchain", "saas", "platform", "app",
    "dev", "code", "programming", "compute",
    "algorithm", "neural", "deep", "learning",
    "robot", "autonomous", "computer", "virtual",
    "informatic", "telecom", "network", "internet",
    "consulting", "solutions", "services",
    "labs", "lab", "studio", "labs",
    "innovate", "innovative", "innovation",
    "digital", "electronic", "online",
    "mobile", "web", "api", "micro",
    "system", "systems", "logic", "algorithm",
    "analytics", "insight", "intelligence",
    "predict", "forecast", "optimize",
    "automation", "automat",
]


# ============================================================
# 公司名归一化
# ============================================================

# 常见公司后缀 (去掉后得到核心名字)
COMPANY_SUFFIXES = [
    "limited", "ltd", "plc", "llp", "lp",
    "incorporated", "inc", "corp", "corporation",
    "company", "co", "group", "holdings", "holding",
    "international", "global", "uk", "europe",
    "services", "service", "solutions", "solution",
    "consulting", "consultancy", "consultants", "consultant",
    "technologies", "technology", "tech",
    "systems", "software", "digital", "media",
    "partners", "partner", "associates", "associate",
    "management", "advisory", "advisors", "advisor",
    "capital", "ventures", "investment",
    "enterprises", "enterprise", "industries", "industry",
    "networks", "network", "online",
    "creative", "design", "studio", "studios",
    "productions", "production",
    "and", "the", "of", "for",
]

# 尾部数字/分隔符清理
RE_SUFFIX_CLEAN = re.compile(
    r'\s+(limited|ltd|plc|llp|inc|corp|co|uk|gb|eu)\.?$', re.I
)
RE_TRAILING_CHARS = re.compile(r'[&\',\\.\\-\\_\\#]+$')


def normalize_company_name(name):
    """公司全名 → 促销码 base name"""
    if not name:
        return ""
    name = name.strip().strip('"').strip()
    if not name:
        return ""

    # 原始名称小写
    orig_lower = name.lower()

    # 逐步去除后缀
    cleaned = orig_lower
    for suffix in COMPANY_SUFFIXES:
        # 匹配 " XXX" 或 " XXX." 结尾
        pattern = r'\s+' + re.escape(suffix) + r'\.?$'
        cleaned = re.sub(pattern, '', cleaned)

    # 去掉所有非字母数字字符（保留字母数字）
    cleaned = re.sub(r'[^a-z0-9]', '', cleaned)

    # 去掉 "the" 前缀
    if cleaned.startswith('the'):
        cleaned = cleaned[3:]

    # 长度过滤
    if len(cleaned) < 4 or len(cleaned) > 30:
        return ""

    return cleaned


def has_tech_indicators(name, sic_codes):
    """判断公司是否与技术相关"""
    name_lower = name.lower()

    # SIC 码匹配
    for sic in sic_codes:
        if sic:
            sic_clean = sic.split(" - ")[0].strip()
            if sic_clean in TECH_SIC_CODES:
                return True
            for prefix in TECH_SIC_PREFIXES:
                if sic_clean.startswith(prefix):
                    return True

    # 公司名关键词匹配
    for kw in TECH_KEYWORDS:
        if kw in name_lower:
            return True

    return False


# ============================================================
# 数据处理管道
# ============================================================

def extract_bases(max_companies=200000):
    """从 CSV 提取公司名 → base name"""
    print(f"📂 读取 {ZIP_PATH}...")

    bases = set()
    total_rows = 0
    tech_rows = 0

    with zipfile.ZipFile(ZIP_PATH) as zf:
        # 找到 CSV 文件名
        csv_name = [n for n in zf.namelist() if n.endswith('.csv')][0]
        print(f"  CSV: {csv_name}")

        with zf.open(csv_name) as f:
            # CSV 可能带 BOM
            text = io.TextIOWrapper(f, encoding='utf-8-sig')
            reader = csv.reader(text)

            # 找列索引
            header = next(reader)
            header_clean = [h.strip() for h in header]

            try:
                name_idx = header_clean.index("CompanyName")
                status_idx = header_clean.index("CompanyStatus")
            except ValueError:
                # 尝试不同格式
                name_idx = 0
                status_idx = 11  # guessed

            # 找 SIC 列索引
            sic_indices = []
            for i, h in enumerate(header_clean):
                if h.startswith("SICCode"):
                    sic_indices.append(i)

            print(f"  列: CompanyName={name_idx}, CompanyStatus={status_idx}, SIC={sic_indices}")

            for row in reader:
                total_rows += 1
                if not row or len(row) <= max(name_idx, status_idx):
                    continue

                name = row[name_idx].strip().strip('"').strip()
                status = row[status_idx].strip().strip('"').strip()

                # 只处理 Active 公司
                if status != "Active":
                    continue

                # 提取 SIC codes
                sic_codes = []
                for si in sic_indices:
                    if si < len(row):
                        sic_codes.append(row[si].strip().strip('"').strip())

                # 非 tech 公司跳过
                if not has_tech_indicators(name, sic_codes):
                    continue

                tech_rows += 1

                # 归一化
                base = normalize_company_name(name)
                if base:
                    bases.add(base)

                # 进度提示
                if total_rows % 500000 == 0:
                    print(f"  ... 已读 {total_rows:,} 行, tech {tech_rows:,}, bases {len(bases):,}")

                # 限制处理量
                if tech_rows >= max_companies:
                    break

    print(f"\n  ✅ 总行: {total_rows:,}")
    print(f"  ✅ Tech 公司: {tech_rows:,}")
    print(f"  ✅ Base names: {len(bases):,}")
    return sorted(bases)


# ============================================================
# 候选生成 & 去重
# ============================================================

COUNTRIES = [
    "us", "gb", "uk", "ca", "au", "de", "fr", "es", "it", "nl", "ie",
    "br", "nz", "za", "ke", "ng", "th", "sg", "ph", "in", "jp",
    "kr", "se", "no", "dk", "fi", "ch", "at", "be", "mx",
    "ae", "sa", "il", "tr", "pl", "cz", "ro", "pt", "gr", "hu",
]


def generate_candidates(bases, dedup=None, max_candidates=50000):
    """生成候选码: base × country + bare"""
    candidates = set()
    for base in bases:
        for cc in COUNTRIES:
            candidates.add(f"{base}{cc}")
        candidates.add(base)

    if dedup:
        old_count = len(candidates)
        candidates -= dedup
        print(f"  🔄 去重: {old_count - len(candidates)} 已测, 剩余 {len(candidates)}")

    result = sorted(c for c in candidates if len(c) >= 4)
    random.seed(456)  # 不同的种子 vs mega_scan
    random.shuffle(result)
    return result[:max_candidates]


def load_tested():
    """加载所有已测码"""
    tested = set()
    for fname in os.listdir(OUTPUT_DIR):
        if fname.startswith("discovery_") and fname.endswith(".json"):
            try:
                with open(os.path.join(OUTPUT_DIR, fname)) as f:
                    data = json.load(f)
                for key in ("eligible", "exists"):
                    for code in data.get(key, []):
                        tested.add(code)
            except: pass
    for rf in [RESULTS_FILE, os.path.join(OUTPUT_DIR, "mega_results.json")]:
        if os.path.exists(rf):
            try:
                with open(rf) as f:
                    data = json.load(f)
                for key in ("eligible", "exists"):
                    for code in data.get(key, []):
                        tested.add(code)
            except: pass
    return tested


# ============================================================
# 保存 & 进度
# ============================================================

def save_progress(state):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except: pass
    return None


def save_results(results):
    merged = {"eligible": [], "exists": [], "errors": {}}
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE) as f:
                existing = json.load(f)
            merged["eligible"] = existing.get("eligible", [])
            merged["exists"] = existing.get("exists", [])
            merged["errors"] = existing.get("errors", {})
        except: pass

    for code, status in results.items():
        if status == "ELIGIBLE":
            if code not in merged["eligible"]:
                merged["eligible"].append(code)
        elif status == "EXISTS":
            if code not in merged["exists"]:
                merged["exists"].append(code)
        else:
            merged["errors"][code] = status

    for k in ("eligible", "exists"):
        merged[k] = sorted(set(merged[k]))
    merged["last_updated"] = datetime.now().isoformat()
    merged["total_eligible"] = len(merged["eligible"])
    merged["total_exists"] = len(merged["exists"])

    with open(RESULTS_FILE, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    return merged


# ============================================================
# 主流程
# ============================================================

def run(resume=False):
    print(f"\n{'='*60}")
    print(f"🇬🇧 UK Companies House 全量公司 → ChatGPT Team 促销码扫描")
    print(f"{'='*60}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    state = load_progress() if resume else None

    # 1. 提取 base names
    if state and state.get("bases"):
        bases = state["bases"]
        print(f"🔁 恢复: {len(bases)} base name\n")
    else:
        print("📦 阶段 1: 从 5M+ 公司中提取 Tech 公司...")
        bases = extract_bases(max_companies=200000)
        print(f"  ✅ {len(bases)} base names\n")

    # 2. 去重
    if state:
        tested = set(state.get("tested_codes", []))
    else:
        tested = load_tested()
    print(f"  🔄 已有已测码: {len(tested)}")

    # 3. 生成候选 (最多 50000)
    if state:
        candidates = state["candidates"]
    else:
        candidates = generate_candidates(bases, dedup=tested, max_candidates=50000)
    print(f"  ✅ 候选码数: {len(candidates)}\n")

    # 保存 base names
    with open(BASES_FILE, "w") as f:
        for b in bases:
            f.write(b + "\n")
    print(f"  💾 Base names 已保存: {BASES_FILE}")

    if not candidates:
        print("❌ 没有新候选码")
        return

    # 4. 分批验证
    BATCH = 100
    total = len(candidates)
    start = state.get("completed", 0) if state else 0

    print(f"🔍 开始分批验证 (每批 {BATCH} 个, 总共 {total} 个)...")
    print(f"{'='*60}")

    all_results = {}
    completed = start
    found_eligible = 0
    found_exists = 0

    if state:
        all_results = state.get("results", {})
        found_eligible = len([s for s in all_results.values() if s == "ELIGIBLE"])
        found_exists = len([s for s in all_results.values() if s == "EXISTS"])

    for bs in range(start, total, BATCH):
        batch = candidates[bs:bs + BATCH]
        be = min(bs + BATCH, total)
        batch_num = bs // BATCH + 1
        total_batches = (total - 1) // BATCH + 1

        print(f"\n📊 批次 {batch_num}/{total_batches} ({bs}-{be}/{total}) "
              f"[✅{found_eligible} 🔶{found_exists}]")

        try:
            results = dc.batch_check(batch, delay=0.12)
        except Exception as e:
            print(f"\n❌ 批次失败: {e}")
            save_progress({
                "completed": bs, "total": total,
                "results": all_results,
                "tested_codes": list(tested | set(candidates[:bs])),
                "bases": bases, "candidates": candidates,
                "timestamp": datetime.now().isoformat(),
            })
            print(f"💾 进度已保存 ({bs}/{total}), --resume 继续")
            return

        for code, status in results.items():
            all_results[code] = status
            if status == "ELIGIBLE":
                found_eligible += 1
                print(f"  🎉 新合格码: {code}")
            elif status == "EXISTS":
                found_exists += 1

        completed = be

        merged = save_results(all_results)
        save_progress({
            "completed": completed, "total": total,
            "results": all_results,
            "tested_codes": list(tested | set(candidates[:completed])),
            "bases": bases, "candidates": candidates,
            "timestamp": datetime.now().isoformat(),
        })

        elapsed = found_eligible + found_exists
        pct = f"{elapsed / max(completed, 1) * 100:.4f}%"
        print(f"  📈 进度: {completed}/{total} | "
              f"✅{found_eligible} | 🔶{found_exists} | 命中率: {pct}")

    # 5. 汇总
    elapsed = found_eligible + found_exists
    print(f"\n{'='*60}")
    print(f"📊 扫描完成!")
    print(f"{'='*60}")
    print(f"  总测试: {completed}")
    print(f"  ✅ ELIGIBLE: {found_eligible}")
    print(f"  🔶 EXISTS:   {found_exists}")
    pct = f"{elapsed / max(completed, 1) * 100:.4f}%"
    print(f"  命中率: {pct}")

    if elapsed > 0:
        print(f"\n📋 所有有效码:")
        for code, status in sorted(all_results.items()):
            if status in ("ELIGIBLE", "EXISTS"):
                print(f"    {'✅' if status == 'ELIGIBLE' else '🔶'} {code}")

    print(f"\n📝 结果保存: {RESULTS_FILE}")

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


if __name__ == "__main__":
    resume = "--resume" in sys.argv
    run(resume=resume)

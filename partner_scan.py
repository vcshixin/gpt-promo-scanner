#!/usr/bin/env python3
"""OpenAI 合作商 → 促销码定向扫描

OpenAI 官方合作伙伴（Reseller / SI / 渠道）是最可能的促销码来源。
直接找合作商 base name 是最有效的策略。
"""
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import discover_codes as dc

OUTPUT_DIR = config.get_output_dir()
RESULTS_FILE = os.path.join(OUTPUT_DIR, "partner_results.json")

# OpenAI 官方合作伙伴 — 已知的所有 Reseller/SI/Consulting Partners
PARTNER_NAMES = [
    # === Reseller (direct sales channel) ===
    "pwc",           # PwC — first-ever reseller
    "bain",          # Bain & Company — 13,000 ChatGPT Enterprise licenses
    "accenture",     # Accenture — 40,000 licenses, "primary intelligence partner"
    "mckinsey",      # McKinsey — Frontier Alliance
    "bcg",           # Boston Consulting Group — Frontier Alliance
    "capgemini",     # Capgemini — Frontier Alliance
    "samsungsds",    # Samsung SDS — first Korean reseller
    "lgcns",         # LG CNS — Korean reseller
    "cognizant",     # Cognizant — Codex SI partner
    "cgi",           # CGI — Codex SI partner
    "cloudwerx",     # Cloudwerx — ANZ OpenAI partner
    "shopify",       # Shopify — e-commerce integration partner
    "megazonecloud", # Megazone Cloud — Korean cloud MSP
    "bespinglobal",  # Bespin Global — Korean cloud MSP
    # === Ad Tech Partners ===
    "criteo",        # Criteo — first ad tech partner
    "adobe",         # Adobe — ad tech partner
    "kargo",         # Kargo — ad tech partner
    "pacvue",        # Pacvue — commerce media OS
    "stackadapt",    # StackAdapt — ad tech partner
    # === Agency Partners ===
    "omnicom",       # Omnicom Media Group
    "wpp",           # WPP
    "dentsu",        # Dentsu
    "kepler",        # Kepler — independent agency
    # === Notable Enterprise Customers ===
    "notion",        # Notion — enterprise customer
    "ramp",          # Ramp — enterprise customer
    "braintrust",    # Braintrust — enterprise customer
    "github",        # GitHub — enterprise customer
    "nextdoor",      # Nextdoor — enterprise customer
    "cisco",         # Cisco — enterprise customer
    "nvidia",        # Nvidia — enterprise customer
    "samsung",       # Samsung
    "lg",            # LG
    # === OpenAI Frontier Alliance ===
    "accenture",
    "mckinsey",
    "bcg",
    "capgemini",
    # === First Focus / SearchKings (OpenAI SMB channel) ===
    "firstfocus",
    "talentgenius",
    "wildmango",
    "codestone",
    "thealloynetwork",
    "alongside",
    "monicai",
    "thinkingmachines",
]

COUNTRIES = [
    "us", "gb", "uk", "ca", "au", "de", "fr", "es", "it", "nl", "ie",
    "br", "nz", "za", "ke", "ng", "th", "sg", "ph", "in", "jp",
    "kr", "se", "no", "dk", "fi", "ch", "at", "be", "mx",
    "ae", "sa", "il", "tr", "pl", "cz", "ro", "pt", "gr", "hu",
]


def build_candidates():
    """Partner name × 40 countries + bare name"""
    candidates = set()
    for name in PARTNER_NAMES:
        name = name.strip().lower()
        if not name:
            continue
        for cc in COUNTRIES:
            code = f"{name}{cc}"
            if len(code) >= 4:
                candidates.add(code)
        candidates.add(name)

    # Dedup
    tested = set()
    for fname in os.listdir(OUTPUT_DIR):
        if fname.startswith("discovery_") and fname.endswith(".json"):
            try:
                with open(os.path.join(OUTPUT_DIR, fname)) as f:
                    data = json.load(f)
                for key in ("eligible", "exists"):
                    for code in data.get(key, []):
                        tested.add(code)
            except:
                pass
    for rf in ["mega_results.json", "uk_results.json", "us_results.json", "partner_results.json"]:
        p = os.path.join(OUTPUT_DIR, rf)
        if os.path.exists(p):
            try:
                with open(p) as f:
                    data = json.load(f)
                for key in ("eligible", "exists"):
                    for code in data.get(key, []):
                        tested.add(code)
            except:
                pass

    before = len(candidates)
    candidates -= tested
    removed = before - len(candidates)
    if removed:
        print(f"  🔄 去重: {removed} 已测")
    return sorted(candidates)


def save_results(results):
    merged = {"eligible": [], "exists": [], "errors": {}}
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE) as f:
                existing = json.load(f)
            merged["eligible"] = existing.get("eligible", [])
            merged["exists"] = existing.get("exists", [])
            merged["errors"] = existing.get("errors", {})
        except:
            pass

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


def run():
    print(f"\n{'='*60}")
    print(f"🤝 OpenAI 合作伙伴定向扫描")
    print(f"{'='*60}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    candidates = build_candidates()
    print(f"  📋 候选码数: {len(candidates)}")

    BATCH = 100
    total = len(candidates)
    all_results = {}
    found_eligible = 0
    found_exists = 0

    print(f"\n🔍 开始分批验证 (每批 {BATCH} 个)...")
    for bs in range(0, total, BATCH):
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
            save_results(all_results)
            return

        for code, status in results.items():
            all_results[code] = status
            if status == "ELIGIBLE":
                found_eligible += 1
                print(f"  🎉 新合格码: {code}")
            elif status == "EXISTS":
                found_exists += 1
                print(f"  🔶 存在: {code}")

        merged = save_results(all_results)
        elapsed = found_eligible + found_exists
        pct = f"{elapsed / max(be, 1) * 100:.4f}%"
        print(f"  📈 进度: {be}/{total} | ✅{found_eligible} | 🔶{found_exists} | 命中率: {pct}")

    print(f"\n{'='*60}")
    print(f"📊 合作伙伴扫描完成!")
    print(f"{'='*60}")
    print(f"  总测试: {total}")
    print(f"  ✅ ELIGIBLE: {found_eligible}")
    print(f"  🔶 EXISTS:   {found_exists}")
    if found_eligible + found_exists > 0:
        print(f"\n📋 所有有效码:")
        for code, status in sorted(all_results.items()):
            if status in ("ELIGIBLE", "EXISTS"):
                print(f"    {'✅' if status == 'ELIGIBLE' else '🔶'} {code}")
    print(f"\n📝 结果保存: {RESULTS_FILE}")


if __name__ == "__main__":
    run()

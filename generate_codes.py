"""
ChatGPT Team 促销码批量生成器
基于已验证模式：公司名全小写去空格 + ISO国家代码

用法:
  python generate_codes.py                    # 打印所有候选码
  python generate_codes.py --verify           # 输出可直接复制到 verify.py CODES 的格式
  python generate_codes.py --verified-only    # 只输出已验证存在的码
  python generate_codes.py --cross-product    # 输出已验证公司的全地区交叉测试
"""

import re
import argparse

# ============================================================
# 已验证存在的公司 Base Name（用于交叉测试）
# ============================================================
VERIFIED_BASES = [
    "aibuildgroup",       # GB EXISTS
    "wildmango",          # KE/US/FR/ZA/NG — 已验证
    "firstfocus",         # AU/US/NZ — 已验证（AU无后缀）
    "codestone",          # DE/FR/ES — 已验证
    "talentgenius",       # US/CA/AU/BR — 已验证
    "thealloynetwork",    # US — 已验证（有无us后缀均可）
    "alongside",          # US — 已验证
    "monicai",            # US/CA — 已验证
]

# 已验证存在的完整码
VERIFIED_CODES = {
    "ELIGIBLE": {
        "US": [
            "talentgeniusus",      # $25/月
            "thealloynetwork",     # $30/月
            "alongsideus",         # $30/月
            "monicaius",           # $30/月
            "firstfocusus",        # $25/月
            "wildmangous",         # $25/月
            "thealloynetworkus",   # $30/月（重复）
        ],
    },
    "EXISTS": {
        "base_only": ["firstfocus"],
        "GB": ["aibuildgroupgb"],
        "KE": ["wildmangoke"],
        "FR": ["wildmangofr", "codestonefr"],
        "DE": ["codestonede"],
        "ES": ["codestonees"],
        "NZ": ["firstfocusnz"],
        "CA": ["talentgeniusca", "monicaica"],
        "AU": ["talentgeniusau"],
        "BR": ["talentgeniusbr"],
        "ZA": ["wildmangoza"],
        "NG": ["wildmangong"],
    },
}

# ============================================================
# 候选公司列表（潜在合作伙伴）
# ============================================================
# AI 生产力工具公司（类似 TalentGenius / Monica AI 模式）
AI_PRODUCTIVITY = [
    ("Notion", ["US"]),
    ("Mem", ["US"]),
    ("Taskade", ["US"]),
    ("Motion", ["US"]),
    ("Reclaim AI", ["US"]),
    ("Akiflow", ["US"]),
    ("Fathom", ["US", "CA"]),
    ("Otter AI", ["US"]),
    ("Fireflies", ["US"]),
    ("Tactiq", ["US"]),
    ("Elephas", ["US"]),
    ("Pulze AI", ["US"]),
    ("Typetonic", ["US"]),
    ("Writer", ["US"]),
    ("Jasper AI", ["US"]),
    ("Copy AI", ["US"]),
    ("Rytr", ["US"]),
    ("Writesonic", ["US"]),
    ("Article", ["US"]),
    ("Scalenut", ["US"]),
    ("Frase", ["US"]),
    ("Surfer", ["US"]),
    ("ContentBot", ["US"]),
    ("Ink", ["US"]),
    ("NeuronWriter", ["US"]),
    ("Outranking", ["US"]),
    ("Synthesia", ["US", "GB"]),
    ("HeyGen", ["US"]),
    ("D-ID", ["US"]),
    ("ElevenLabs", ["US"]),
    ("Resemble", ["US"]),
    ("Murf", ["US"]),
    ("PlayHT", ["US"]),
    ("Descript", ["US"]),
    ("Wellsaid", ["US"]),
    ("OpenTop", ["US"]),
    ("Lexica", ["US"]),
    ("Genie", ["US"]),
    ("Pictor", ["US"]),
    ("Canva", ["US", "AU"]),
    ("Midjourney", ["US"]),
    ("Leonardo AI", ["US"]),
    ("Krea AI", ["US"]),
    ("Recraft", ["US"]),
    ("Ideogram", ["US"]),
    ("ClipDrop", ["US"]),
    ("Stability AI", ["US", "GB"]),
    ("GetImg", ["US"]),
    ("Runway ML", ["US"]),
    ("Pika Labs", ["US"]),
    ("Immersity", ["US"]),
]

# IT/MSP 公司（类似 Codestone / First Focus 模式）
MSP_COMPANIES = [
    ("Sherweb", ["US", "CA"]),
    ("Pax8", ["US"]),
    ("AppDirect", ["US"]),
    ("Ingram Micro", ["US", "CA"]),
    ("Tech Data", ["US"]),
    ("Synnex", ["US"]),
    ("D&H", ["US"]),
    ("Connection", ["US"]),
    ("Zones", ["US"]),
    ("CSP", ["US"]),
    ("Thrive", ["US"]),
    ("Sophos", ["US", "GB"]),
    ("Presidio", ["US"]),
    ("ePlus", ["US"]),
    ("CDW", ["US", "CA"]),
    ("SHI", ["US"]),
    ("Insight", ["US"]),
    ("Rackspace", ["US", "GB"]),
    ("Lumen", ["US"]),
    ("Optiv", ["US"]),
    ("GuidePoint", ["US"]),
    ("Slalom", ["US", "CA"]),
    ("Thoughtworks", ["US", "GB"]),
    ("Globant", ["US"]),
    ("SoftServe", ["US"]),
    ("EPAM", ["US"]),
    ("Endava", ["US", "GB"]),
    ("Bounteous", ["US"]),
    ("Improving", ["US"]),
    ("Avanade", ["US", "GB"]),
    ("Influx Data", ["US"]),
    ("Confluent", ["US"]),
    ("MongoDB", ["US"]),
    ("Elastic", ["US", "GB"]),
    ("Databricks", ["US"]),
    ("Snowflake", ["US"]),
    ("Palantir", ["US", "GB"]),
]

# 全球/地区性 IT 咨询公司
CONSULTING_FIRMS = [
    ("Accenture", ["US", "GB"]),
    ("Deloitte", ["US", "GB"]),
    ("PwC", ["US", "GB"]),
    ("KPMG", ["US", "GB"]),
    ("EY", ["US", "GB"]),
    ("McKinsey", ["US", "GB"]),
    ("BCG", ["US", "GB"]),
    ("Bain", ["US"]),
    ("Capgemini", ["US", "GB", "FR"]),
    ("Infosys", ["US", "IN"]),
    ("TCS", ["US", "IN"]),
    ("Wipro", ["US", "IN"]),
    ("HCL", ["US", "IN"]),
    ("Cognizant", ["US", "IN"]),
    ("IBM", ["US", "GB"]),
]


COUNTRIES = ["us", "gb", "ca", "au", "ke", "de", "fr", "jp", "in", "sg", "ie", "kr",
             "nl", "se", "no", "dk", "fi", "ch", "at", "be", "es", "it", "nz", "sg",
             "mx", "br", "za", "ng", "ae", "sa", "il", "tr", "pl", "cz", "ro"]


def normalize_name(name):
    """生成公司名的各种标准化变体"""
    name = name.strip()
    variants = []
    base = re.sub(r'[\s\-_./,&+]', '', name).lower()
    variants.append(base)
    if base.startswith('the'):
        variants.append(base[3:])
    words = re.split(r'[\s\-_./,&+]+', name.lower())
    if len(words) > 1:
        acronym = ''.join(w[0] for w in words if w)
        variants.append(acronym)
    if len(words) > 1:
        variants.append(words[0])
    if len(words) > 1:
        two_word = ''.join(words[:2])
        variants.append(two_word)
    for suffix in ['technologies', 'services', 'solutions', 'group', 'international', 'consulting', 'systems', 'software', 'security', 'labs']:
        if base.endswith(suffix):
            variants.append(base[:-len(suffix)])
    seen = set()
    unique = []
    for v in variants:
        if v not in seen and v:
            seen.add(v)
            unique.append(v)
    return unique


def generate_codes(company_list):
    """从公司列表生成 {country: [codes]} 字典"""
    codes = {}
    for name, countries in company_list:
        name_variants = normalize_name(name)
        for cc in countries:
            if cc not in codes:
                codes[cc] = []
            for variant in name_variants:
                full_code = variant + cc.lower()
                if full_code not in codes[cc]:
                    codes[cc].append(full_code)
    return codes


def main():
    parser = argparse.ArgumentParser(description="ChatGPT Team 促销码批量生成器")
    parser.add_argument("--verify", action="store_true", help="输出 verify.py 兼容格式")
    parser.add_argument("--verified-only", action="store_true", help="只输出已验证存在的码")
    parser.add_argument("--cross-product", action="store_true", help="输出已验证公司的全地区交叉测试格式")
    args = parser.parse_args()

    if args.verified_only:
        print("# Verified codes (known to exist)")
        for tag, regions in VERIFIED_CODES.items():
            print(f"# {tag}")
            for region, codes in regions.items():
                for c in codes:
                    print(f"  {c}")
        return

    if args.cross_product:
        print("# Cross-product test: verified bases × all countries")
        print("CODES = {")
        print('    "CROSS_PRODUCT": [')
        for base in VERIFIED_BASES:
            for cc in COUNTRIES:
                print(f'        "{base}{cc}",')
        print("    ],")
        print("}")
        return

    if args.verify:
        all_codes = {}
        for company_list in [AI_PRODUCTIVITY, MSP_COMPANIES, CONSULTING_FIRMS]:
            codes = generate_codes(company_list)
            for region, code_list in codes.items():
                if region not in all_codes:
                    all_codes[region] = []
                for c in code_list:
                    if c not in all_codes[region]:
                        all_codes[region].append(c)

        print("# auto-generated by generate_codes.py")
        print("CODES = {")
        for region in sorted(all_codes.keys()):
            codes = all_codes[region]
            print(f'    "{region}": [')
            for i, code in enumerate(codes):
                comma = "," if i < len(codes) - 1 else ","
                print(f'        "{code}"{comma}')
            print("    ],")
        print("}")
        print(f"\n# Total: {sum(len(v) for v in all_codes.values())} codes across {len(all_codes)} regions")
        return

    # Default: print summary
    print("=" * 70)
    print("ChatGPT Team 促销码工具")
    print("=" * 70)

    print("\n=== 已验证存在的码 ===")
    for tag, regions in VERIFIED_CODES.items():
        print(f"\n[{tag}]")
        for region, codes in regions.items():
            print(f"  {region}: {', '.join(codes)}")

    print(f"\n=== 已验证公司 Base Name ===")
    for b in VERIFIED_BASES:
        print(f"  {b}")

    total_candidate = sum(len(generate_codes(AI_PRODUCTIVITY).get(c, [])) +
                          len(generate_codes(MSP_COMPANIES).get(c, [])) +
                          len(generate_codes(CONSULTING_FIRMS).get(c, []))
                          for c in COUNTRIES)

    print(f"\n=== 候选公司 ===")
    print(f"  AI生产力公司: {len(AI_PRODUCTIVITY)}")
    print(f"  MSP公司: {len(MSP_COMPANIES)}")
    print(f"  咨询公司: {len(CONSULTING_FIRMS)}")
    print(f"  可用国家码: {len(COUNTRIES)}")
    print(f"\n使用 --verify 生成 verify.py 兼容格式")
    print(f"使用 --cross-product 生成已验证公司的交叉测试")
    print(f"使用 --verified-only 列出已验证存在的码")


if __name__ == "__main__":
    main()

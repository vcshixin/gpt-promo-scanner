"""
OpenAI ChatGPT Team 促销码批量验证脚本
使用 /backend-api/promotions/eligibility/{code} 端点验证促销码是否存在。

用法:
  1. 修改下方 TOKEN 为你的 accessToken（从 chatgpt.com F12 Console 获取）
  2. 修改 PROXY 为你的代理地址（如不需要代理则设为 None）
  3. 修改 CODES 字典添加要测试的促销码
  4. python verify.py

输出:
  EXISTS  = 促销码真实存在（但当前账户地区不匹配）
  ELIGIBLE = 促销码有效且可用
  not found = 促销码不存在
"""

import json
import time
from curl_cffi import requests as cffi_requests

# ============================================================
# 配置区域 - 修改这里
# ============================================================

# accessToken - 从 chatgpt.com F12 Console 执行以下命令获取:
#   const s = await (await fetch("/api/auth/session")).json(); console.log(s.accessToken);
TOKEN = "在此填入你的 accessToken"

# 代理地址，不需要代理则设为 None
PROXY = "http://127.0.0.1:7890"

# 请求间隔（秒），避免触发限流
DELAY = 1

# 要验证的促销码，格式: { "地区标签": ["code1", "code2", ...] }
CODES = {
    # ============================================================
    # 已验证 ELIGIBLE（当前账户可用）
    # ============================================================
    "✅ US ELIGIBLE": [
        "talentgeniusus",      # $25/月 off, 48mo — TalentGenius
        "thealloynetwork",     # $30/月 off, 48mo — The Alloy Network
        "alongsideus",         # $30/月 off, 48mo — Alongside
        "monicaius",           # $30/月 off, 48mo — Monica AI
        "firstfocusus",        # $25/月 off, 48mo — First Focus (AU MSP)
        "wildmangous",         # $25/月 off, 48mo — WildMango (KE AI partner)
        "thealloynetworkus",   # $30/月 off, 48mo — 别名
    ],
    # ============================================================
    # 已验证 EXISTS（存在但地区不匹配）
    # ============================================================
    "✅ EXISTS (misc)": [
        "firstfocus",          # AU — 无国家后缀！
        "aibuildgroupgb",      # GB
        "wildmangoke",         # KE
        "wildmangofr",         # FR
        "wildmangoza",         # ZA
        "wildmangong",         # NG
        "firstfocusnz",        # NZ
        "codestonede",         # DE
        "codestonefr",         # FR
        "codestonees",         # ES
        "talentgeniusca",      # CA
        "talentgeniusau",      # AU
        "talentgeniusbr",      # BR
        "monicaica",           # CA
    ],
}

# 结果输出文件
OUTPUT_FILE = "results.json"

# ============================================================
# 核心逻辑 - 一般不需要修改
# ============================================================

def create_session():
    """创建带 TLS 指纹伪装的 HTTP 会话"""
    session = cffi_requests.Session(impersonate="chrome136")
    if PROXY:
        session.proxies = {"https": PROXY, "http": PROXY}
    return session

def get_headers(token):
    """构建请求头"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

def check_code(session, headers, code):
    """
    验证单个促销码
    返回: dict with keys: code, is_eligible, reason_code, reason_msg, status, metadata
    """
    url = f"https://chatgpt.com/backend-api/promotions/eligibility/{code}?type=promo"
    resp = session.get(url, headers=headers, timeout=15)
    data = resp.json()

    is_eligible = data.get("is_eligible", False)
    reason = data.get("ineligible_reason")
    reason_code = reason.get("code", "unknown") if reason else "none"
    reason_msg = reason.get("message", "") if reason else ""

    result = {
        "code": code,
        "status": resp.status_code,
        "is_eligible": is_eligible,
        "reason_code": reason_code,
        "reason_msg": reason_msg,
    }

    # 对存在的促销码获取元数据
    if is_eligible or reason_code == "user_not_eligible":
        time.sleep(0.5)
        meta_url = f"https://chatgpt.com/backend-api/promotions/metadata/{code}?type=promo"
        try:
            meta_resp = session.get(meta_url, headers=headers, timeout=15)
            meta_data = meta_resp.json()
            result["metadata"] = meta_data
        except Exception:
            pass

    return result

def classify(result):
    """分类验证结果"""
    if result.get("is_eligible"):
        return "ELIGIBLE"
    elif result.get("reason_code") == "user_not_eligible":
        return "EXISTS"
    elif result.get("reason_code") == "invalid_code":
        return "not found"
    else:
        return f"unknown({result.get('reason_code', '?')})"

def main():
    if TOKEN == "在这里粘贴你的accessToken":
        print("错误: 请先设置 TOKEN（从 chatgpt.com 获取 accessToken）")
        print("获取方法: 在 chatgpt.com F12 Console 执行:")
        print('  const s = await (await fetch("/api/auth/session")).json(); console.log(s.accessToken);')
        return

    session = create_session()
    headers = get_headers(TOKEN)

    all_results = []
    found_codes = []

    for region, codes in CODES.items():
        if not codes:
            continue

        print(f"\n{'='*60}")
        print(f"Region: {region} ({len(codes)} codes)")
        print(f"{'='*60}")

        for i, code in enumerate(codes, 1):
            try:
                result = check_code(session, headers, code)
                result["region"] = region
                all_results.append(result)

                tag = classify(result)
                print(f"  [{i:2d}/{len(codes)}] {code:<35s} {tag}")

                if tag in ("ELIGIBLE", "EXISTS"):
                    found_codes.append(result)
                    if result.get("metadata", {}).get("metadata"):
                        print(f"         metadata: {json.dumps(result['metadata']['metadata'])[:200]}")

            except Exception as e:
                print(f"  [{i:2d}/{len(codes)}] {code:<35s} ERROR: {e}")
                all_results.append({"region": region, "code": code, "error": str(e)})

            time.sleep(DELAY)

    # 汇总
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total tested: {len(all_results)}")
    print(f"Valid (exist): {len(found_codes)}")

    if found_codes:
        print(f"\n*** FOUND {len(found_codes)} EXISTING CODES ***")
        for r in found_codes:
            tag = classify(r)
            meta = r.get("metadata", {}).get("metadata", {})
            meta_str = f" | {json.dumps(meta)[:200]}" if meta else ""
            print(f"  {r['code']:<35s} [{tag}] ({r['region']}) - {r['reason_msg']}{meta_str}")

    # 保存
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

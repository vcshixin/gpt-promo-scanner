"""Clash 代理智能节点选择器 + ChatGPT Team 促销码结账测试

用法:
  python smart_proxy.py list                   # 列出可用地区与节点
  python smart_proxy.py test GB                # 切英国节点 + 生成链接
  python smart_proxy.py test GB --open         # 切节点 + 浏览器打开
  python smart_proxy.py scan                   # 列出所有地区所有码的链接
  python smart_proxy.py scan-auto              # 自动切节点 + checkout API 验证所有码
"""
import json
import time
import subprocess
import webbrowser
import re
from urllib.parse import quote

CLASH_SOCKET = "/tmp/verge/verge-mihomo.sock"
AI_GROUP = "🤖 AI"  # ChatGPT 流量走这个组（规则模式）
GLOBAL_GROUP = "GLOBAL"  # 全局模式走这个组
PROXY_URL = "http://127.0.0.1:7890"

REGIONS = {
    "GB": {
        "keywords": ["英国", "🇬🇧"],
        "codes": ["aibuildgroupgb", "geccogb"],
        "billing": {"country": "GB", "currency": "GBP"},
        "label": "🇬🇧 英国",
        "desc": "~£11/月 ≈ $7/人",
    },
    "AU": {
        "keywords": ["澳洲", "澳大利亚", "🇦🇺"],
        "codes": ["firstfocus"],
        "billing": {"country": "AU", "currency": "AUD"},
        "label": "🇦🇺 澳大利亚",
        "desc": "~AU$25/月 ≈ $8/人",
    },
    "DE": {
        "keywords": ["德国", "🇩🇪"],
        "codes": ["codestonede"],
        "billing": {"country": "DE", "currency": "EUR"},
        "label": "🇩🇪 德国",
        "desc": "Codestone DE",
    },
    "FR": {
        "keywords": ["法国", "🇫🇷"],
        "codes": ["codestonefr", "wildmangofr"],
        "billing": {"country": "FR", "currency": "EUR"},
        "label": "🇫🇷 法国",
        "desc": "Codestone/WildMango FR",
    },
    "ES": {
        "keywords": ["西班牙", "🇪🇸"],
        "codes": ["codestonees"],
        "billing": {"country": "ES", "currency": "EUR"},
        "label": "🇪🇸 西班牙",
        "desc": "Codestone ES",
    },
    "CA": {
        "keywords": ["加拿大", "🇨🇦"],
        "codes": ["talentgeniusca", "monicaica"],
        "billing": {"country": "CA", "currency": "CAD"},
        "label": "🇨🇦 加拿大",
        "desc": "TalentGenius/Monica CA",
    },
    "BR": {
        "keywords": ["巴西", "🇧🇷"],
        "codes": ["talentgeniusbr"],
        "billing": {"country": "BR", "currency": "BRL"},
        "label": "🇧🇷 巴西",
        "desc": "TalentGenius BR",
    },
    "NZ": {
        "keywords": ["新西兰", "🇳🇿"],
        "codes": ["firstfocusnz"],
        "billing": {"country": "NZ", "currency": "NZD"},
        "label": "🇳🇿 新西兰",
        "desc": "First Focus NZ",
    },
    "KE": {
        "keywords": ["肯尼亚", "🇰🇪"],
        "codes": ["wildmangoke"],
        "billing": {"country": "KE", "currency": "USD"},
        "label": "🇰🇪 肯尼亚",
        "desc": "WildMango KE",
    },
    "ZA": {
        "keywords": ["南非", "🇿🇦"],
        "codes": ["wildmangoza"],
        "billing": {"country": "ZA", "currency": "ZAR"},
        "label": "🇿🇦 南非",
        "desc": "WildMango ZA",
    },
    "NG": {
        "keywords": ["尼日利亚", "🇳🇬"],
        "codes": ["wildmangong"],
        "billing": {"country": "NG", "currency": "NGN"},
        "label": "🇳🇬 尼日利亚",
        "desc": "WildMango NG",
    },
}

US_CODES = [
    ("thealloynetwork", "US", "USD"),
    ("alongsideus", "US", "USD"),
    ("monicaius", "US", "USD"),
    ("talentgeniusus", "US", "USD"),
    ("firstfocusus", "US", "USD"),
    ("wildmangous", "US", "USD"),
]


# ─── Clash API ──────────────────────────────────────────────

def clash_api(path, method="GET", data=None):
    url = f"http://localhost{path}"
    cmd = ["curl", "-s", "--unix-socket", CLASH_SOCKET]
    if method != "GET":
        cmd += ["-X", method]
    if data:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        raise Exception(f"curl error: {result.stderr}")
    return result.stdout

def _proxy_group():
    """检测当前模式，返回对应 proxy group 名"""
    raw = clash_api("/configs")
    mode = json.loads(raw).get("mode", "rule")
    return GLOBAL_GROUP if mode == "global" else AI_GROUP

def get_all_nodes():
    raw = clash_api("/proxies")
    data = json.loads(raw)
    proxies = data.get("proxies", {})
    group_name = _proxy_group()
    group = proxies.get(group_name, {})
    current = group.get("now", "?")
    nodes = []
    for name in group.get("all", []):
        info = proxies.get(name)
        if info and info.get("type") not in ("Selector", "URLTest", "Fallback", "Direct", "Reject", "Compatible", "Pass"):
            nodes.append(name)
    return nodes, current

def match_region_nodes(nodes, keywords):
    return [n for n in nodes for kw in keywords if kw in n]

def test_node_latency(node_name):
    encoded = quote(node_name, safe='')
    url = f"http://localhost/proxies/{encoded}/delay?timeout=5000&url=https://www.google.com"
    cmd = ["curl", "-s", "--unix-socket", CLASH_SOCKET, "-X", "GET", url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    try:
        return json.loads(result.stdout).get("delay", -1)
    except:
        return -1

def switch_node(node_name):
    group_name = _proxy_group()
    encoded = quote(group_name, safe='')
    clash_api(f"/proxies/{encoded}", method="PUT", data={"name": node_name})

def get_current_node():
    raw = clash_api("/proxies")
    group_name = _proxy_group()
    return json.loads(raw).get("proxies", {}).get(group_name, {}).get("now", "?")


# ─── Checkout API ───────────────────────────────────────────

def _get_token():
    with open('/Volumes/SSD/oaipromo/verify.py', 'r') as f:
        content = f.read()
    match = re.search(r'TOKEN = "([^"]+)"', content)
    return match.group(1)

def try_checkout(promo_code, country, currency):
    """调用 checkout API，返回 (url_or_None, status, error_msg)"""
    from curl_cffi import requests as cffi_requests

    session = cffi_requests.Session(impersonate="chrome136")
    session.proxies = {"https": PROXY_URL, "http": PROXY_URL}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Authorization": f"Bearer {_get_token()}",
        "Content-Type": "application/json",
    }
    payload = {
        "plan_name": "chatgptteamplan",
        "team_plan_data": {
            "workspace_name": f"Team{int(time.time())}",
            "price_interval": "month",
            "seat_quantity": 2,
        },
        "billing_details": {"country": country, "currency": currency},
        "promo_code": promo_code,
        "cancel_url": "https://chatgpt.com/",
        "checkout_ui_mode": "hosted",
    }
    try:
        resp = session.post(
            "https://chatgpt.com/backend-api/payments/checkout",
            json=payload, headers=headers, timeout=20
        )
        data = resp.json()
        url = data.get("url") or ""
        if url.startswith("https://"):
            return url, resp.status_code, None
        return None, resp.status_code, data.get("detail", str(data)[:200])
    except Exception as e:
        return None, 0, str(e)


# ─── 命令实现 ───────────────────────────────────────────────

def cmd_list():
    nodes, current = get_all_nodes()
    print(f"\n📡 Clash 可用地区与节点数（当前: {current}）:")
    print(f"{'地区':<15s} {'节点数':<8s} {'待测码':<25s} {'说明'}")
    print("-" * 70)
    for code, region in sorted(REGIONS.items()):
        matched = match_region_nodes(nodes, region["keywords"])
        codes_str = ", ".join(region["codes"])
        print(f"{region['label']:<15s} {len(matched):<8d} {codes_str:<25s} {region['desc']}")


def cmd_test(region_code, auto_open=False):
    region = REGIONS[region_code]
    nodes, _ = get_all_nodes()
    matched = match_region_nodes(nodes, region["keywords"])

    if not matched:
        print(f"❌ 没有找到 {region['label']} 的节点")
        return

    print(f"\n🔍 {region['label']} — {len(matched)} 个节点，正在测速...")
    best = None
    best_delay = 99999
    for name in matched:
        delay = test_node_latency(name)
        status = f"{delay}ms" if delay > 0 else "超时"
        if 0 < delay < best_delay:
            best_delay = delay
            best = name
        print(f"  {name:<30s} {status}")

    if not best:
        print("❌ 所有节点超时")
        return

    print(f"\n🔄 切换到: {best} ({best_delay}ms)")
    switch_node(best)
    time.sleep(0.5)
    print(f"  ✓ 当前节点: {get_current_node()}")
    print()

    print(f"{'='*60}")
    print(f"🌍 {region['label']} — {region['desc']}")
    print(f"{'='*60}")

    bc = region["billing"]
    for code in region["codes"]:
        url, status, err = try_checkout(code, bc["country"], bc["currency"])
        if url:
            print(f"  {code:<25s} ✅ {url[:80]}...")
        elif err:
            print(f"  {code:<25s} ❌ {err[:80]}")
        else:
            print(f"  {code:<25s} ❌ status={status}")

    if auto_open:
        print(f"\n🌐 正在浏览器打开...")
        for code in region["codes"]:
            url, _, _ = try_checkout(code, bc["country"], bc["currency"])
            if url:
                webbrowser.open(url)
                time.sleep(0.5)


def cmd_scan():
    """列出所有链接（不调 API，自己手动切节点测）"""
    print(f"\n{'='*60}")
    print("🔍 全区域 promo 链接")
    print(f"{'='*60}")

    print(f"\n--- US 码（切到美国节点后打开）---")
    for code, *_ in US_CODES:
        print(f"  https://chatgpt.com/?promoCode={code}")

    for rc, region in sorted(REGIONS.items()):
        print(f"\n--- {region['label']} — {region['desc']} ---")
        for code in region["codes"]:
            print(f"  https://chatgpt.com/?promoCode={code}")

    print(f"\n📌 用法：手动切 Clash 节点到对应地区，然后浏览器打开链接")


def cmd_scan_auto():
    """自动切每个节点 → checkout API 出 Stripe URL"""
    print(f"\n{'='*60}")
    print("🔍 自动扫描：切节点 → checkout API")
    print(f"{'='*60}")

    all_working = []
    nodes, _ = get_all_nodes()

    # 先测 US
    us_nodes = match_region_nodes(nodes, ["美国", "🇺🇸"])
    if us_nodes:
        print(f"\n🔄 切换到 US: {us_nodes[0]}")
        switch_node(us_nodes[0])
        time.sleep(0.5)

    print(f"\n{'─'*60}")
    print("🇺🇸 US 码")
    print(f"{'─'*60}")
    for code, country, currency in US_CODES:
        url, status, err = try_checkout(code, country, currency)
        if url:
            print(f"  {code:<25s} ✅ {url[:80]}...")
            all_working.append((code, "US", url))
        elif err:
            print(f"  {code:<25s} ❌ {err[:80]}")
        else:
            print(f"  {code:<25s} ❌ status={status}")

    # 再测其他地区
    for rc, region in sorted(REGIONS.items()):
        matched = match_region_nodes(nodes, region["keywords"])
        if not matched:
            continue

        # 找最佳节点
        best = None
        best_delay = 99999
        for name in matched:
            delay = test_node_latency(name)
            if 0 < delay < best_delay:
                best_delay = delay
                best = name

        if not best:
            continue

        print(f"\n{'─'*60}")
        print(f"{region['label']} — 切换到: {best} ({best_delay}ms)")
        print(f"{'─'*60}")
        switch_node(best)
        time.sleep(0.5)

        bc = region["billing"]
        for code in region["codes"]:
            url, status, err = try_checkout(code, bc["country"], bc["currency"])
            if url:
                print(f"  {code:<25s} ✅ {url[:80]}...")
                all_working.append((code, rc, url))
            elif "not eligible" in (err or ""):
                print(f"  {code:<25s} ❌ 不可用")
            else:
                print(f"  {code:<25s} ❌ {str(err or status)[:60]}")

    # 汇总
    print(f"\n{'='*60}")
    print("📊 扫描完成")
    print(f"{'='*60}")
    if all_working:
        print(f"\n✅ 可用的码:")
        for code, rc, url in all_working:
            print(f"  {code:<25s} [{rc}] {url[:100]}...")
    else:
        print("\n❌ 没有找到可用的码")

    # 切回 US
    if us_nodes:
        switch_node(us_nodes[0])
        print(f"\n✅ 已切回: {us_nodes[0]}")


# ─── 入口 ───────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python smart_proxy.py list              # 列出可用地区与节点")
        print("  python smart_proxy.py test GB            # 切英国节点 + checkout API 验证")
        print("  python smart_proxy.py test GB --open     # 切节点 + 浏览器打开")
        print("  python smart_proxy.py scan               # 列出所有链接")
        print("  python smart_proxy.py scan-auto          # 自动切节点 + checkout API 验证所有码")
        print("\n地区码:", ", ".join(REGIONS.keys()))
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "list":
        cmd_list()
    elif cmd == "test":
        if len(sys.argv) < 3:
            print("请指定地区码")
            sys.exit(1)
        rc = sys.argv[2].upper()
        if rc not in REGIONS:
            print(f"未知地区: {rc}")
            sys.exit(1)
        auto_open = "--open" in sys.argv
        cmd_test(rc, auto_open)
    elif cmd == "scan":
        cmd_scan()
    elif cmd == "scan-auto":
        cmd_scan_auto()
    else:
        print(f"未知命令: {cmd}")

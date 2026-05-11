"""一键生成 ChatGPT Business 促销码 Stripe 付款链接

用法:
  python3 open_stripe.py <促销码> <国家码> <accessToken>

示例:
  python3 open_stripe.py thinkingmachinesth TH eyJhbGciOi...
  python3 open_stripe.py thealloynetwork US eyJhbGciOi...
"""

import sys, time

def get_stripe_url(code, token, country="US", currency="USD"):
    from curl_cffi import requests as cffi_requests

    session = cffi_requests.Session(impersonate="chrome136")
    session.proxies = {"https": "http://127.0.0.1:7890", "http": "http://127.0.0.1:7890"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {token}",
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
        "promo_code": code,
        "cancel_url": "https://chatgpt.com/",
        "checkout_ui_mode": "hosted",
    }
    try:
        resp = session.post(
            "https://chatgpt.com/backend-api/payments/checkout",
            json=payload, headers=headers, timeout=20,
        )
        data = resp.json()
        url = data.get("url", "")
        return url if url.startswith("https://") else None
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 4 or "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(1)

    code = sys.argv[1]
    country = sys.argv[2].upper()
    token = sys.argv[3]

    if not token.startswith("eyJ"):
        print("❌ accessToken 格式不对，应该是 eyJ... 开头")
        sys.exit(1)

    print(f"\n🔗 {code}  [{country}]")
    url = get_stripe_url(code, token, country, "USD")

    if url:
        print(f"\n✅ 链接已生成，复制到浏览器打开：\n{url}\n")
    else:
        print(f"❌ 生成失败，检查代理或 token")

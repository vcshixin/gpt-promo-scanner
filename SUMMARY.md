# ChatGPT Team (Business) 促销码批量发现与验证 — 完整总结

> 所有有效码、方法论、踩坑记录

---

## 一、最终有效码清单（22 个）

### US — 当前账户可直接用（7 个）

| 促销码 | 折扣/月 | 48月省 | 来源公司 |
|--------|---------|--------|---------|
| `thealloynetwork` | -$30 | $1,440 | The Alloy Network (MSP) |
| `thealloynetworkus` | -$30 | $1,440 | 同上（别名） |
| `alongsideus` | -$30 | $1,440 | Alongside (AI 投资) |
| `monicaius` | -$30 | $1,440 | Monica AI (浏览器助手) |
| `talentgeniusus` | -$25 | $1,200 | TalentGenius (AI 招聘) |
| `firstfocusus` | -$25 | $1,200 | First Focus (MSP) |
| `wildmangous` | -$25 | $1,200 | WildMango (AI 分销) |

### 非 US — 需对应节点付款（15 个）

| 促销码 | 地区 | 本地折扣/月 | ≈ USD/月 | 公司 |
|--------|------|------------|----------|------|
| `codestonede` | 🇩🇪 DE | -€29 | $34 | Codestone |
| `codestonees` | 🇪🇸 ES | -€28 | $33 | Codestone |
| `codestonefr` | 🇫🇷 FR | -€28 | $33 | Codestone |
| `firstfocus` | 🇦🇺 AU | -A$45 | $33 | First Focus |
| `monicaica` | 🇨🇦 CA | -C$42 | $31 | Monica AI |
| `wildmangoke` | 🇰🇪 KE | -$30 | $30 | WildMango |
| `talentgeniusbr` | 🇧🇷 BR | -R$130 | $26 | TalentGenius |
| `wildmangofr` | 🇫🇷 FR | -€22 | $26 | WildMango |
| `talentgeniusau` | 🇦🇺 AU | -A$35 | $25 | TalentGenius |
| `talentgeniusca` | 🇨🇦 CA | -C$34 | $25 | TalentGenius |
| `talentgeniusuk` | 🇬🇧 GB | -£18 | $25 | TalentGenius |
| `aibuildgroupgb` | 🇬🇧 GB | -£18 | $25 | AI Build Group |
| `wildmangong` | 🇳🇬 NG | -₦33,600 | $25 | WildMango |
| `firstfocusnz` | 🇳🇿 NZ | -NZ$41 | $24 | First Focus |
| `wildmangoza` | 🇿🇦 ZA | -R400 | $24 | WildMango |

**全部 48 个月时长，ChatGPT Business (原 Team) 计划。**

---

## 二、方法论

### 命名规则

```
[公司名全小写去空格][ISO 国家码小写]
```

变体:
- **标准**: `talentgeniusus`, `wildmangoke`
- **无后缀**: `firstfocus`（裸公司名）
- **别名**: `thealloynetwork` = `thealloynetworkus`
- **uk 非 gb**: `talentgeniusuk`（UK 码用 `uk` 后缀）

### 验证 API

```python
GET /backend-api/promotions/eligibility/{code}?type=promo
Authorization: Bearer <token>
```

返回值:
- `is_eligible: true` → **ELIGIBLE**（当前账户可用）
- `ineligible_reason.code: "user_not_eligible"` → **EXISTS**（码存在但地区不匹配）
- `ineligible_reason.code: "invalid_code"` → **not_found**（不存在）

### 价格收集 API

```python
# 1. 生成 Stripe 支付 URL
POST /backend-api/payments/checkout
Body: { promo_code, billing_details, plan_name, team_plan_data, ... }

# 2. 获取折扣详情
GET /backend-api/promotions/metadata/{code}?type=promo
```

⚠️ 两个 API 都**必须在对应地区的代理节点下调用**，否则返回错误。

### 自动扫描流程

```
切节点 → checkout API → metadata API → 实时汇率换算 → 汇总
```

---

## 三、踩坑记录

### 坑 1：CRN 报道的合作伙伴全是错的

初始策略是找 OpenAI 公开宣布的 SMB 合作伙伴，然后枚举他们的码。SearchKings (CA)、Samsung SDS (KR)、ITPartners、Entech 等全部 not found。花了一天时间验证了 ~100 个码，0 个命中。

**教训**：公开宣布的合作伙伴 ≠ 有促销码的合作伙伴。大部分合作伙伴走的是返点/回扣模式，不是码模式。

### 坑 2：跑大量请求前没先测一个

发现 UK 的 AI 公司列表后，直接生成 1286 个候选码开跑。结果全部返回 `Expecting value: line 1 column 1 (char 0)` — Cloudflare 把我们的代理节点 IP 拉黑了。浪费 1286 次请求。

**教训**：任何批处理之前，先测一个单请求确认 API 可用。

### 坑 3：代码逻辑错误导致 `--cross` 永远不触发

写全矩阵交叉扫描功能时，`--cross` 的判断放在了 `if not target: sys.exit(1)` 之后。结果用户每次运行 `--cross` 都直接退出了。折腾了半天才找到。

**教训**：flag 解析必须在 target 解析之前，顺序很重要。

### 坑 4：Clash 全局模式 vs 规则模式

早期版本硬编码切换 `🤖 AI` 代理组。但用户的 Clash 在 **global 模式** 下，ChatGPT 流量走的是 `GLOBAL` 组。所有节点切换都不生效，checkout API 一直失败。

**教训**：必须检测 Clash 当前模式：

```python
mode = get("/configs").mode
group = "GLOBAL" if mode == "global" else "🤖 AI"
```

### 坑 5：UK 的国家后缀不统一

`talentgeniusuk` 有效，但 `talentgeniusgb` 不存在。反过来 `aibuildgroupgb` 有效，但 `aibuildgroupuk` 不存在。没有任何规律。

**教训**：对 UK，两种后缀（`gb` 和 `uk`）都要试。

### 坑 6：Cloudflare 限速

连续请求 ~50 个后，Cloudflare 开始返回验证码页面（非 JSON），导致 JSON 解析异常。需要：
- 控制频率（150-200ms 间隔）
- 被限速时切换代理节点
- 每次请求用新的 Session（避免 cookie 累积）

### 坑 7：Metadata 折扣是 per-seat 的

Metadata API 返回的 `discount.value` 是**每席位的折扣**，不是总折扣。2 席位时实际省 = value × 2。但 Stripe 页面的最终价格有时还会有些微差异（税费等）。

### 坑 8：码有有效期

`geccogb` 和 `codestonegb` 在 OzBargain 和论坛上被验证有效（~£11/月），但现在已经返回 `invalid_code`。码是有生命周期的。

### 坑 9：部分码可能有别名

`thealloynetwork`（裸名）和 `thealloynetworkus`（带后缀）都有效且都是 ELIGIBLE。同样的码可能有多个入口。

---

## 四、公司跨国矩阵

```
TalentGenius    → US($25)  AU($25)  BR($26)  CA($25)  GB($25)
WildMango       → US($25)  FR($26)  KE($30)  NG($25)  ZA($24)
First Focus     → US($25)  AU($33)  NZ($24)
Codestone       → DE($34)  ES($33)  FR($33)
Monica AI       → US($30)  CA($31)
The Alloy Network→ US($30)
Alongside       → US($30)
AI Build Group  → GB($25)
```

**特征**：有码的公司都是中小型 MSP/IT 服务和 AI 工具公司，不是大型咨询公司。

---

## 五、已验证不存在的候选

| 类别 | 例子 |
|------|------|
| CRN 报道 MSP | ITPartners, Entech, iCorps, Shield, NexusTek (全 US) |
| 大型咨询 | Accenture, Deloitte, PwC, KPMG, EY, McKinsey, BCG, Bain |
| AI 工具公司 | Synthesia, HeyGen, Midjourney, Canva, Notion, Perplexity, 40+ |
| 电商合作 | eBay, PayPal, Booking, VistaPrint, Criteo |
| 已知合作伙伴 | SearchKings (CA), Samsung SDS (KR) |
| UK AI 公司 | Beamery, Metaview + 200 家（仅 talentgeniusuk 命中） |
| 全矩阵扩展 | 280 组合 (8 bases × 34 国家)，新增 9 个 |

---

## 六、文件清单

| 文件 | 用途 |
|------|------|
| `auto_scan.py` | 自动切节点 + checkout + 价格收集 + 汇率换算 |
| `discover_codes.py` | 批量候选码生成 + eligibility 验证 |
| `verify.py` | Token 配置 + 单码验证 |
| `scan_results.json` | 结构化扫描结果 |
| `stripe_urls.txt` | 所有 Stripe URL 汇总 |
| `DISCOVERY_LOG.md` | 完整发现过程日志 |
| `discovery_cross.json` | 全矩阵交叉扫描结果 |
| `discovery_GB.json` | UK 批量扫描结果 |

---

## 七、生效中的码 （用于快速参考）

当前 US 账户可直接用的最优惠码：
- **$30/月 off**: `thealloynetwork` / `alongsideus` / `monicaius`
- **$25/月 off**: `talentgeniusus` / `firstfocusus` / `wildmangous`

选择策略：码在 checkout 时生成 Stripe URL，URL 有效期内付款即可。没有账号限制，只要有对应地区的支付方式。

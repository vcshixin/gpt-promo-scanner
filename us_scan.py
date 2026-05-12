#!/usr/bin/env python3
"""美国 AI + MSP 全量公司 → ChatGPT Team 促销码扫描

数据源:
  1. Forbes AI 50 (2025-2026) — 美国 AI 明星公司
  2. TechCrunch AI 百大融资公司
  3. Wing VC Enterprise Tech 30
  4. Madrona IA40
  5. Y Combinator AI 公司 (2024-2026)
  6. CRN MSP 500 (Elite 150 + Pioneer 250 + Security 100)
  7. Channel Futures MSP 501
  8. 美国 IT 咨询/系统集成商 (Top 200)
  9. US AI SaaS 各垂直领域 (Legal/Health/HR/Fintech/Marketing/Security)
  10. SEC EDGAR 美股上市公司 (Public Companies)
  11. US Cloud / 基础设施公司
  12. 全球 30+ 热点国家的 AI 科技公司

策略: base name × 40 国家码 + bare name → 随机打乱 → 分批 eligibility check

用法:
  python3 us_scan.py
  python3 us_scan.py --resume
"""
import json
import os
import sys
import time
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import discover_codes as dc

OUTPUT_DIR = config.get_output_dir()
PROGRESS_FILE = os.path.join(OUTPUT_DIR, ".us_progress.json")
RESULTS_FILE = os.path.join(OUTPUT_DIR, "us_results.json")

# 只有美国公司才带 US 标记 — 这是最可能的有效码来源
# 策略: 收集尽可能多的美国公司, x 40 国家码 + 裸码

COMPANY_LISTS = """
# ═══════════════════════════════════════════════════════════════
# 1. Forbes AI 50 / TechCrunch AI Top Funded (US)
# ═══════════════════════════════════════════════════════════════
OpenAI Anthropic ScaleAI Databricks Perplexity Glean
Runway Harvey CognitionAI Abridge Hebbia Sierra
FireworksAI TogetherAI Lambda Baseten Modular Modal
Replicate UnslothAI ReflectionAI Suno Gamma Luma
Pika Captions HeyGen ElevenLabs Descript Krisp
Writer Typeface Cohere AdeptAI InflectionAI
Anysphere Cursor Windsurf Factory Lovable
PhysicalIntelligence FigureAI ShieldAI Anduril
SandboxAQ Groq Cerebras CelestialAI Crusoe
VASTData FlockSafety Island Wiz AbnormalSecurity
Snyk Chainguard Cribl ArcticWolf
Ramp Brex Mercury Deel Rippling Gusto Justworks
Notion Canva Figma Linear Airtable Miro
ClickHouse MotherDuck Starburst dbt Fivetran Airbyte
MonteCarlo Sifflet ArizeAI WhyLabs Gantry
OpenEvidence Ambience ChaiDiscovery LilaSciences HippocraticAI
EvenUp Eudia DistylAI Clio CopilotKit
Braintrust LangChain LlamaIndex CrewAI Browserbase
Unify OrbyAI Rogo Decagon Clay
Granola OtterAI Fireflies Fathom Mem Krisp
Superhuman Tailscale Stackblitz Replit
BoltNew CodeRabbit Graphite Greptile Augment
MutableAI SweepAI OpenCommit CosineFactory
Poolside Axiom ResolveAI
UnconventionalAI NexthopAI RICSOpenSource
PeriodicLabs HumansAnd AxiomWisperFlow Certuma
LatentHealth NectarSocial WorktraceAI
AdvancedMachineIntelligence

# ═══════════════════════════════════════════════════════════════
# 2. Y Combinator AI 公司 (HF0 / S24-W25)
# ═══════════════════════════════════════════════════════════════
Emergent UnslothAI Mem0 ConfidentAI Wildcard A0dev Promptless
IncidentFox Mendral Draftbit DepGuard Runbook Schematic
PenAgent PolicyPilot ShadowScan HexSecurity Zalos EndClose
FullSeam Pace Proximitty OrigamiRobotics Asimov HumanArchive
CortexAI Lightberry Hyperspell Metorial Lemma Dari Multifactor
AgentTrace NeuronRouter GuardRail Everest Jarmin Relaw Lexi
LunaBill NoteScribe ClauseHound AuditAI Canary Terrapin
Hyperspell Calltree AlphaSonic OctaiPipeline Sema4 AI21Vec
AcuityMD Agentio Apex AssortHealth
Collate DavidAI Decart Forterra
Krea LiveKit Rox Reducto
Basis Malga Layer Anysphere
Tempo Astronomer CommonPaper Vapi
Inferact ComfyUI ParallelAI

# ═══════════════════════════════════════════════════════════════
# 3. CRN MSP 500 — Elite 150 (US + North America)
# ═══════════════════════════════════════════════════════════════
# 大型企业级 MSP
Presidio CDW InsightEn WWT WorldWideTech SHIInternational
Connection EnPointe ZoneTechnologies MainstreamTech eMazzanti
StanfieldIT AllCovered Bowne BDO Digital ProServe
GreenPages StrataCom EaseTech eGroupTech Vology Pomeroy
RedRiver C3Integrated GDT Dataprise AccessGlobal AABACUS
BitbyBit KMicro TechPrecision CalTech ICS Cygnul
OneNeckIT TierPoint Flexential DataBank QTS Cyxtera
Equinix DigitalRealty Rackspace Sunguard Navisite Concur
Hostway Peer1 Internap CoreSite CenturyLink
NexusTek ParkPlace Netgain NetAtWork AlcottEnterprises
Verinext MGMConsulting NetGainTech ManagedSolution LogicalisUS
TPxCommunications AndromedaTech BetterWorldTech EMPIST
AlithyaGroup BCMOne BespokeTechnologyGroup CBTS
CCS CDSOffice Technologies CentreTechnologies Chetu
ConvergeTechnologySolutions ePlus IronBowTechnologies
JudgeGroup JudgeConsulting RedRiver RSMUS Sikich
Stratix Sycomp USCloud Effectual DoiT
Summit7 CriticalStart Xantrion
Cbeyond Ntiva AnchorManagedSolutions
ForthrightTechnology Partners MREConsulting OmegaComputerServices
Stasmayer TechRageIT VintageITServices Xperteks
Cloudticity MRE Consulting AnchorMS

# ═══════════════════════════════════════════════════════════════
# 4. US Top MSP / MSSP (CRN + Channel Futures)
# ═══════════════════════════════════════════════════════════════
# 这是 CRN MSP 500 + CF 501 大名单
EdwardsManagedService Adkore SecuritySavvy
PCS Technologies Impact Networking INOC Services
LIS Networks Secuvant FishNet Security
Optiv Security GuidePoint Security Armor Defense
CrowdStrike FalconForce eSentire Expel
Rapid7 Tenable Qualys AlertLogic Trustwave
SecureWorks Mandiant FireEye Trellix McAfee
PaloAltoNetworks Fortinet CheckPoint TrendMicro
BlueVoyant Deepwatch RedCanary Huntress
Fortra Sophos Cybereason SentinelOne
Tanium CarbonBlack DigitalGuardian Proofpoint
Mimecast Barracuda Netskope Zscaler
Okta DuoSecurity Cloudflare Auth0 BeyondTrust
CyberArk Thycotic Centrify OneLogin
DellEMC HPE IBM ServiceNow ConnectWise
Kaseya Datto SolarWinds N able Acronis
Veeam Commvault Rubrik Cohesity Veritas
Axcient StorageCraft Infrascale Arcserve
Datto Continuum ConnectWise Autotask
Pax8 Sherweb IngramMicro TechData Synnex
ArrowElectronics WestconComstor Avnet
ClimbChannel Rhipe DickerData ResellerTech

# ═══════════════════════════════════════════════════════════════
# 5. US IT 咨询 / 系统集成商 (Top Tier)
# ═══════════════════════════════════════════════════════════════
Accenture Deloitte IBM PwC EY KPMG
TCS Infosys HCLTech Wipro TechMahindra Cognizant
Capgemini Atos DXC Globant EPAMSystems Perficient
NTTData Fujitsu HitachiVantara NEC Unisys
GDIT Leidos SAIC BoozAllen CACI ScienceApps
KeyW Perspectia Engility MITRE Noblis
BoozAllenHamilton Slalom Kainos CognizantSoftvision
SopraSteria Indra CGI Logica
Gartner Forrester IDC FrostSullivan
Smartronix ThunderCat PrescientSolutions InfoReliance
AcentureDigital BCG Platinion McKinseyDigital BainLeghart
DelloiteDigital MissionCloud ApexSystems CompassUOL
Infocepts FactualMinds Cloudreach Appsbroker
Ancoris MadeTech ANDDigital ScottLogic
Version1 Noranalytos Rackspace Endava
Avanade Thoughtworks Elastic Palantir Sophos
Sage InterSystems OpenText MicroFocus

# ═══════════════════════════════════════════════════════════════
# 6. US AI SaaS — 各垂直领域
# ═══════════════════════════════════════════════════════════════
# Legal AI
Harvey RobinAI EvenUp Eudia Clio LexisNexis
Ironclad LinkSquares Evisort Lexion Spellbook Alexi
PaxtonAI Relaw Juro Luminance ThoughtRiver
Definely GenieAI Legl Lawhive Jaxon Della
KiraSystems Keneox Disco Everlaw Onit
BusyLamp LawGeex LegalRobot

# Healthcare AI
Abridge OpenEvidence Ambience ChaiDiscovery LilaSciences
HippocraticAI PathAI PaigeAI VizAI Aidoc
ZebraMedical ButterflyNetwork CaptionHealth Tempus
FlatironHealth FoundationMedicine GuardantHealth RecursionInnPharma
Insitro BenevolentAI Exscientia DeepMind Isomorphic
Pager Medly RoRo BuoyHealth YourMD
PushHealth AdaHealth Babylon CeraCare
KheironMedical Medopad SkinAnalytics Optellum PatchAi
Healx Relation MindFoundry Kortical RapidBird Owkin
Ibex Pimloc Infogrid Zegami

# HR / Recruiting AI
Beamery Metaview Huddle Applied Tribepad
Clevry ThriveMap ArcticShores Sova Fasthr
Detech Jobbio Cognisium SnapHire Lever
Greenhouse Workable Breezy Hibob Personio
Lattice 15Five CultureAmp OfficeVibe Peakon
Pymetrics HireVue ModernHire Ideal EightfoldAI
SeekOut PhenomPeople iCIMS SmartRecruiters TalentGenius

# Fintech AI
Stripe Plaid Brex Ramp Mercury Deel
Payoneer Wise Square Block Robinhood
Coinbase Kraken Gemini Affirm Afterpay
Klarna Marqeta Unit Synctera Lithic
Cleo Chip Plum Moneybox Wealthify Freetrade
Trading212 Revolut Monzo Starling OakNorth
Kroo Pento MennaAI Marloo Swoop Fluidly
Pulse Countingup Coconut FreeAgent Crunch TaxScouts
Previse 9fin DueCourse iwoca MarketFinance Tide
Monese TransferGo Azimo Currencycloud TrueLayer
Razorpay Cred Chargebee

# Marketing / AdTech AI
HubSpot Salesforce Lavender StoryChief Contentscale
Simplified Jasper Anyword Rytr Writesonic CopyAI
Peppertype GrowthBar Mutiny Brandwatch BuzzSumo
SproutSocial Hootsuite Buffer SendGrid Mailchimp
Klaviyo Iterable Braze CustomerIO Segment
mParticle Amplitude Mixpanel Heap FullStory
Hotjar LuckyOrange CrazyEgg VWO Optimizely
Searchable FlickAI Decima Joggle Adzooma
BrightBid Peerius Qubit Yieldify Ozone
Echobox Pulsar Chattermill Ometria SmartFocus
Conversocial Spektrix Meltwater Determ NewsWhip
Talkwalker Brand24 Kamma Hubb SignalMedia

# Customer Service / Sales AI
Intercom Zendesk Freshworks Gorgias Crisp Olark
HelpShift Ada KoreAI PolyAI Netomi DigitalGenius
Astound Elevio Freshchat Trengo Chaport
Drift Salesloft Outreach Apollo ZoomInfo Gong
Clari Chorus Wingman Jiminny
Kustomer Gladly Tymeshift MessageBird
Talkdesk Five9 Genesys NICEinContact

# 企业 AI / 数据分析
Snowflake Databricks Dbt Coalesce Sifflet Seldon
Monolith Diffblue SignalBox Streetbees Preamble
ThoughtMachine TheAX Mapify LocAI Quantexa
Featurespace Onfido Tessian Tableau PowerBI
Looker Mode Hex Thoughtspot Sigma Domo
Sisense Metabase Superset Dataiku DataRobot
H2OAI DataStax Neo4j Starburst Trino Presto
Clickhouse Seldon ArizeAI WhyLabs Gantry EvidentlyAI
StreamSets Talend Informatica Matillion Alteryx

# Cybersecurity AI
Wiz Lacework SentinelOne CrowdStrike PaloAlto
Darktrace Snyk Aqua Illumio Cybereason Orca
NormanShield HackerOne Bugcrowd Fortinet CheckPoint
TrendMicro McAfee CarbonBlack Tanium Cylance
Crowdstrike Okta Auth0 DuoSecurity Zscaler
Netskope Prisma Sysdig Falco Rapid7
Tenable Qualys Nexpose AlienVault Splunk
SumoLogic Datadog NewRelic Grafana Dynatrace
Elastic SolarWinds Nagios LogicMonitor PRTG
GeordieAI Panaseer Egress Garrison ZoneFox
Glasswall RedSocks Senseon Traceable Darklantern
BluePrism ProtectWise SignalSciences

# AI 开发者工具
GitHubCopilot Cursor Codeium Tabnine Replit Bolt
Lovable Windsurf Continue Pieces Sourcegraph
BuildJet Depot TestSprite QA Wolf BugBug
Codacy Docker CopilotKit SweepAI Greptile
OpenCommit CodeGenie MutableAI Debuild
KiloCode CosineFactory xIsland Factory
LangChain LlamaIndex CrewAI AutoGen SemanticKernel
Pinecone Weaviate Qdrant Milvus Chroma
WeightsBiases CometML NeptuneAI Valohai AllegroAI
GridAI Spell Deepgram AssemblyAI Speechmatics
Vercel Netlify Render FlyIO Railway Modal
HuggingFace Gradio Streamlit FastAPI

# AI 视频 / 创意 / 内容
Luma Suno Gamma Fal Runway Synthesia
Descript ElevenLabs Murf Respeecher Sonantic Papercup
SpeechKit Sonix Krisp Boomy Haiper InVideo
Pictory OpusClip TypeStudio HeyGen Colossyan HourOne
DID Tavus PikaLabs Midjourney StableDiffusion
Ideogram LeonardoAI Clipdrop Magnific Krea Recraft
Artbreeder Flawless DeepDub Respeecher Voicemod
Altered Aiva Endlesss Soundraw Beatoven Tuney
Kapwing FlexClip Clipchamp Magisto Wondershare
Canva DesignEvo Visme Piktochart Genially

# AI 搜索 / 知识管理
Perplexity Youcom Glean AlphaSense Hebbia Consensus
Elicit SciSpace Sourcely Scite Jenni Paperpal
Typeset IrisAI Mem NotionAI OtterAI Fireflies
Fathom Granola Readwise Reader Reflect Snipd
Podwise Briefmatic Tactiq Bluedot Hugo Dirac
MemBeam Knowledgator Stacks AIAnywhere Exa

# 教育 AI
Quizlet Duolingo Coursera Udacity Udemy KhanAcademy
Brilliant DataCamp Codecademy Pluralsight Skillshare
Masterclass FutureLearn GoStudent Brainly Photomath
Socratic Cognii CarnegieLearning Dreambox Knewton
ALEKS CENTURYTech Sparx Seneca Tassomai
PiTop Microbit BibliU Perlego Kortext
MyTutor Tutorful AtomLearning EdPlace KanoComputing
SAMLabs Natterhub ThirdSpaceLearning Studiosity

# 房地产 / 物业 AI
Zillow Redfin CoStar Compass Opendoor Offerpad
EliseAI Mashroom Nested Boomin Goodlord Ozo
Plentific Fixflo Kestrix Hubble Essensys Density
Locale Reonomy Revaluate HouseCanary

# 制造业 / 物流 / 能源 AI
Samsara Uptake C3AI SparkCognition Falkonry
ElementAnalytics FeroLabs SightMachine Augury
Tractable Snapsheet ClaimGenius
Routific Route4Me OptimoRoute DispatchTrack
Project44 FourKites Flexport Convoy UberFreight
Tesla Nuro Aurora Cruise Waymo Zoox
PonyAI WeRide Motional
GEDigital SiemensDigital ABBAbility HoneywellForge
AspenTech AVEVA OSIsoft Uptake

# ═══════════════════════════════════════════════════════════════
# 7. US Public Companies (SEC EDGAR) — 科技/IT 行业
# ═══════════════════════════════════════════════════════════════
# 美国知名上市公司中与科技 AI 相关
Microsoft Apple Amazon Google Meta NVIDIA AMD
Intel Qualcomm Broadcom TexasInstruments Micron
AppliedMaterials ASML LamResearch KLA Synopsys
Cadence ANSYS Autodesk Adobe Salesforce Oracle
SAP Workday ServiceNow Intuit PayPal Block
Shopify Etsy eBay Pinterest Snap Twitter
Uber Lyft Doordash Instacart Zoom Dropbox
Box DocuSign Okta Twilio Fastly Cloudflare
MongoDB Elastic Datadog NewRelic Dynatrace Splunk
Confluent HashiCorp GitLab GitHub Atlassian Jira
Fortinet PaloAlto Cisco Juniper AristaNetworks
F5Networks NetApp PureStorage Nutanix VMWare
CrowdStrike Zscaler Okta Cloudflare Fastly
RingCentral 8x8 Vonage Twilio Five9
Guidewire Veeva Athenahealth Cerner Epic
Teladoc Livongo Castlight Health

# ═══════════════════════════════════════════════════════════════
# 8. 全球 AI 科技公司 (非 US 补充 — 各热点地区)
# ═══════════════════════════════════════════════════════════════
# 英国
DeepMind Synthesia Graphcore Wayve Huma BenevolentAI
Exscientia InstaDeep Faculty Centauric SignalAI
Cleo TrueLayer Revolut Monzo Starling OakNorth
PolyAI Speechmatics AudioTelligence Seldon Featurespace
Onfido Tessian ThoughtMachine SignalBox
# 加拿大
Cohere Waabi KeplerRd Syntiant Avidbots
Kinduct BlueDot MindBridge ElementAI Layer6
D-WaveSystem Kindred DeepGenomics Cyclica
# 以色列
Wix Monday AI21Labs RunAI DeciAI WalkMe
Fiverr Lemonade Hibob AppsFlyer IronSource
Mobileye CheckPoint Waze HopOn Moovit
Gett Trax RetailRedefined Tanium Cybereason
# 德国
MistralAI AlephAlpha DeepL Lexica Nyris
Merantix Lafleet Celonis UiPath
# 法国
MistralAI H Company Photoroom HuggingFace Replika
Dataiku ShiftTechnology Ledger Doctolib
AlanContentsquare Mirakl BackMarket Qonto
Sorare Lydia YounitedCredit
# 印度
Freshworks Gupshup Sarvam SonataSoftware Zoho
Chargebee Postman BrowserStack Hasura Razorpay
Cred MakeMyTrip Ola Flipkart Paytm
Nykaa PharmEasy Swiggy Zomato UrbanCompany Oyo
Infosys TCS Wipro HCLTech TechMahindra
# 日本
PreferredNetworks SakanaAI LeanValue LTSE DataRobot
ThinkingMachines DatroAI SoftBank NEC Fujitsu
Toshiba Sony Panasonic Hitachi Rakuten Mercari
LINE YahooJapan RapidAPI
# 韩国
Naver Kakao Coupang Baedal Minyong SamsungLG
NCSoft Netmarble Krafton Nexon
# 新加坡
Grab SeaGroup Shopee Razer PatSnap
Trax TradeGecko Carousell PropertyGuru
# 中国
DeepSeek Baidu Alibaba Tencent ByteDance ZhipuAI
BaichuanAI Minimax InfinigenceAI Stepfun LingyiAI MoonshotAI
SenseTime Megvii CloudWalk Yitu PonyAI WeRide
Momenta HorizonRobotics Datagain PulseAI ShukunTechnology
Infervision YituTech Airdoc ModelBest GigaAI EngineAI
Unitree PuduRobotics DeepGlint 4Paradigm Bonree
DJI Huawei Xiaomi Oppo Vivo
Meituan Didi JDcom NetEase Kuaishou Bilibili
Xiaohongshu Zhihu Douyin WeChat

# ═══════════════════════════════════════════════════════════════
# 9. 云计算 / 基础设施公司
# ═══════════════════════════════════════════════════════════════
AWS Azure GoogleCloud OracleCloud DigitalOcean
Linode Vultr Hetzner OVH Scaleway UpCloud
Packet BareMetal CloudSigma ProfitBricks IONOS
CloudFlare Fastly Akamai StackPath Imperva
MongoDBAtlas Supabase PlanetScale NeonRail
Railway Render NorthFlank Koyeb Pulumi
Terraform HashiCorp Docker CloudBees CircleCI
GitHubActions GitLabCI Jenkins TravisCI TeamCity
JFrog Sonatype Nexus WhiteSource Snyk

# ═══════════════════════════════════════════════════════════════
# 10. AI 代理 / 自动化平台
# ═══════════════════════════════════════════════════════════════
Zapier Make Integromat TrayIO Workato
AutomationAnywhere UiPath BluePrism Kryon
NICE ActionBot Ada KoreAI PolyAI
RelevanceAI Fixie AIAgent Swirl AgentHub
AgentLayer Superagent AutoGPT BabyAGI
CrewAI LangGraph AutoGen Semantic Kernel
Fixie Voiceflow Botpress Rasa Dialogflow
LobeChat Dify BotPenguin Coze

# ═══════════════════════════════════════════════════════════════
# 11. AI 垂直/新兴行业应用
# ═══════════════════════════════════════════════════════════════
# 国防 / 军事 AI
Anduril ShieldAI Palantir RebellionDefense
AeroVironment Kratos GeneralAtomics BlueOrigin
SpaceX RelativitySpace RocketLab Astra
# 法律 AI (补充)
Harvey RobinAI EvenUp Eudia Clio LexisNexis
Ironclad LinkSquares Evisort Lexion
# 保险 AI
Lemonade Hippo RootInsurance Metromile Clearcover
Tractable Snapsheet ClaimGenius ShiftTechnology
# 农业 AI
IndigoAg Bowery Plenty AeroFarms AppHarvest
IronOx FarmBot BlueRiverTechnology HarvestAutomation
# 气候 / 能源 AI
C3AI SparkCognition Falkonry StandardCarbon
Climeco Terrapact Pachama NCX

# ═══════════════════════════════════════════════════════════════
# 12. 已知有效码 — 确保它们的各种国家变体都被测试
# ═══════════════════════════════════════════════════════════════
AIBuildGroup AlloyNetwork Alongside Codestone
DatroAI MonicaAI TinyStars Noranalytos
TalentGenius ThinkingMachines Trintel VouchAPI
FirstFocus InfoSeekAI WildMango

# ═══════════════════════════════════════════════════════════════
# 13. 更多美国科技公司 — 初创/B2B SaaS
# ═══════════════════════════════════════════════════════════════
Asana Monday ClickUp Coda Notion Height Plane
Linear Brew Activepieces Loom Tango Scribe
Dubble Loom Frame io Miro Mural FigJam
Whimsical Excalidraw Diagrams Drawio OmniGraffle
Calendly AcuitySchedule ChiliPiper RevenueCat
Chargebee Recurly Stax Stripe Square
Toast Clover Lightspeed SpotOn TouchBistro
ServiceTitan HousecallPro Jobber WorkWave
Buildertrend Procore Autodesk Bluebeam PlanGrid
PagerDuty VictorOps OpsGenie FireHydrant Transposit
LaunchDarkly Splitio ConfigCat Unleash Hypertune
Honeycomb Lightstep Grafana Chronosphere Observe
Tigera Isovalent Cilium Calico Soloio
Buoyant Linkerd Istio Consul HashiCorp
CircleCI Buildkite Semaphore Railway Render
PlanetScale Neon Supabase PocketBase Appwrite
Supabase Convex Firebase Amplify AppSync
Auth0 Clerk WorkOS MagicLink Descope
Frontegg Stytch Userfront PropelAuth Permit
Vercel Netlify Render CloudflarePages AWSAmplify
ArcadeIronWebflow Framer WebStudio Readymag
BuilderIO Plasmic YcodeApp WeWeb WixStudio
Webflow Framer Squarespace Wix Shopify BigCommerce
Magento WooCommerce Saleor Medusa CommerceLayer
Grid Dynamics Endava Slalom EPAM Globant
""".split()

# 非公司词过滤器
NON_COMPANY_WORDS = {
    "ai", "aiai", "all", "and", "are", "best", "can", "data",
    "digital", "for", "from", "global", "group", "has", "have",
    "into", "its", "list", "managed", "management", "more", "new",
    "news", "not", "our", "privacy", "search", "security",
    "services", "service", "solutions", "solution", "software",
    "systems", "team", "tech", "technology", "technologies",
    "that", "the", "their", "them", "they", "this", "top",
    "was", "were", "will", "with", "your",
    "2024", "2025", "2026", "companies", "company",
    "ecosystem", "electric", "energy", "enterprise", "finance",
    "financial", "health", "healthcare", "human", "industry",
    "intelligence", "international", "learning", "life",
    "machine", "manufacturing", "marketing", "marketplace",
    "media", "medical", "msp", "network", "networks",
    "online", "physical", "platform", "platforms", "product",
    "provider", "providers", "publishing", "research",
    "resources", "review", "robotics", "scientific",
    "service", "social", "special", "startup", "startups",
    "supply", "support", "tools", "training",
    "university", "virtual", "work",
    "accelerators", "aisaas", "cyber", "fintech",
    "biotech", "cleantech", "proptech", "legaltech",
    "adtech", "insurtech", "edtech", "hrtech",
    "martech", "salestech", "medtech", "agritech",
    "foodtech", "climatetech", "greentech",
    "enterprise", "edwardsmanaged", "centurytech",
    "stasmayer", "computerspecialists", "xperteks",
}


def normalize(name):
    """公司名 → base name"""
    name = name.strip().lower()
    if name.startswith("#"):
        name = name[1:]
    name = name.replace("-", "").replace("_", "").replace(".", "")
    name = name.replace("'", "").replace("&", "").replace(",", "")
    name = name.replace(" ", "").replace("(", "").replace(")", "")
    name = name.replace(":", "").replace("!", "").replace("?", "")
    name = name.replace("@", "").replace("#", "").replace("+", "")
    if name.startswith("the"):
        name = name[3:]
    return name


def is_valid_company_name(name):
    """判断是否为有效的公司 base name"""
    n = normalize(name)
    if len(n) < 5 or len(n) > 30:
        return False
    if n.isdigit():
        return False
    if not any(c.isalpha() for c in n):
        return False
    if n in NON_COMPANY_WORDS:
        return False
    if len(n) >= 8 and n[-4:].isdigit() and n[:4].isdigit():
        return False
    # 去掉 "computerspecialists" 这种极长无意义的单词
    if len(n) >= 25:
        return False
    # 去掉多余重复的字符（比如 3+ 个相同元音）
    vowel_run = 0
    for c in n:
        if c in "aeiou":
            vowel_run += 1
            if vowel_run >= 5:
                return False
        else:
            vowel_run = 0
    return True


def build_pool():
    """构建去重后的公司 base name 池"""
    pool = set()
    for b in dc.KNOWN_BASES:
        pool.add(normalize(b))
    for name in COMPANY_LISTS:
        if not name or name.startswith("#"):
            continue
        if not is_valid_company_name(name):
            continue
        n = normalize(name)
        if n not in NON_COMPANY_WORDS:
            pool.add(n)
    return sorted(pool)


# 国家码列表
COUNTRIES = [
    "us", "gb", "uk", "ca", "au", "de", "fr", "es", "it", "nl", "ie",
    "br", "nz", "za", "ke", "ng", "th", "sg", "ph", "in", "jp",
    "kr", "se", "no", "dk", "fi", "ch", "at", "be", "mx",
    "ae", "sa", "il", "tr", "pl", "cz", "ro", "pt", "gr", "hu",
]


def generate(bases, dedup=None):
    """生成所有候选码: base × country + base 裸码"""
    candidates = set()
    for base in bases:
        for cc in COUNTRIES:
            candidates.add(f"{base}{cc}")
        candidates.add(base)
    if dedup:
        old_count = len(candidates)
        candidates -= dedup
        print(f"  🔄 去重: {old_count - len(candidates)} 已测, 剩余 {len(candidates)}")
    MAX_CANDIDATES = 50000
    result = sorted(c for c in candidates if len(c) >= 4)
    random.seed(789)
    random.shuffle(result)
    return result[:MAX_CANDIDATES]


def load_tested():
    """加载所有已测过的码 (去重用)"""
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
    for rf in [RESULTS_FILE, os.path.join(OUTPUT_DIR, "mega_results.json"),
               os.path.join(OUTPUT_DIR, "uk_results.json")]:
        if os.path.exists(rf):
            try:
                with open(rf) as f:
                    data = json.load(f)
                for key in ("eligible", "exists"):
                    for code in data.get(key, []):
                        tested.add(code)
            except:
                pass
    return tested


def save_progress(state):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except:
            pass
    return None


def save_results(results):
    """增量保存"""
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


def run(resume=False):
    print(f"\n{'='*60}")
    print(f"🇺🇸 US AI + MSP 全量公司 → ChatGPT Team 促销码扫描")
    print(f"{'='*60}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    state = load_progress() if resume else None

    # 1. 构建公司名池
    print("📦 构建 US AI + MSP 公司名池...")
    if state and state.get("bases"):
        bases = state["bases"]
        print(f"🔁 恢复: {len(bases)} base name\n")
    else:
        bases = build_pool()
    print(f"  ✅ {len(bases)} 个 base name (去重后)")

    # 2. 去重
    if state:
        tested = set(state.get("tested_codes", []))
    else:
        tested = load_tested()
    print(f"  🔄 已有已测码: {len(tested)}")

    # 3. 生成候选
    if state:
        candidates = state["candidates"]
    else:
        candidates = generate(bases, dedup=tested)
    print(f"  ✅ 生成了 {len(candidates)} 个候选码\n")

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

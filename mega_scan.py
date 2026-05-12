#!/usr/bin/env python3
"""超大规模促销码发现 v3 — AI + MSP 全枚举

数据源:
  1. Y Combinator AI 公司 (2024-2026)
  2. 全球 AI 独角兽 + AI 基础架构
  3. Product Hunt 热门 AI 工具
  4. UK AI SaaS / Startup 公司 (~200)
  5. UK MSP / IT 服务公司 (~200)
  6. CRN MSP 500 / Channel Futures MSP 501 公司
  7. 全球 IT 咨询/系统集成商
  8. 中国 AI 生态 (DeepSeek/智谱/月之暗面...)
  9. 各行业 AI 应用 (Fintech/Health/Legal/HR/Security...)
  10. 全球云计算/基础设施公司

策略: base name × 40 国家码 = 80,000+ 候选 → 随机选 20,000 → 分批 eligibility check

用法:
  python3 mega_scan.py                     # 全自动
  python3 mega_scan.py --resume            # 断点续跑
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
PROGRESS_FILE = os.path.join(OUTPUT_DIR, ".mega_progress.json")
RESULTS_FILE = os.path.join(OUTPUT_DIR, "mega_results.json")

# ============================================================
# AI + MSP 全公司枚举 — 按类别组织
# ============================================================

COMPANY_LISTS = """

# ═══════════════════════════════════════════════════════════
# 1. Y Combinator AI 公司 (2024-2026)
# ═══════════════════════════════════════════════════════════
Anysphere Cursor Perplexity ScaleAI Runway Glean Harvey
Emergent UnslothAI Mem0 ConfidentAI Wildcard A0dev Promptless
IncidentFox Mendral Draftbit DepGuard Runbook Schematic
PenAgent PolicyPilot ShadowScan HexSecurity Zalos EndClose
FullSeam Pace Proximitty OrigamiRobotics Asimov HumanArchive
CortexAI Lightberry Hyperspell Metorial Lemma Dari Multifactor
AgentTrace NeuronRouter GuardRail Everest Jarmin Relaw Lexi
LunaBill NoteScribe ClauseHound AuditAI Canary Terrapin
Hyperspell Calltree AlphaSonic
OctaiPipeline Sema4 AI21Vec

# ═══════════════════════════════════════════════════════════
# 2. AI 基础架构与开发者工具
# ═══════════════════════════════════════════════════════════
Databricks Modal Baseten FireworksAI Modular LangChain Factory
Youcom Lovable TogetherAI Replicate Anyscale OctoML BentoML
Nscale SambaNova Cerebras Groq dMatrix Mythic Graphcore
Synthetaic DefinedCortex V7Labs Labelbox Supervisely
Roboflow Encord Lightly DarwinAI Sama
WeightsBiases CometML NeptuneAI Valohai AllegroAI
GridAI Spell Deepgram AssemblyAI Speechmatics
Pinecone Weaviate Qdrant Milvus Chroma
Vercel Netlify Render FlyIO Railway

# ═══════════════════════════════════════════════════════════
# 3. AI 视频/音频/创意/内容
# ═══════════════════════════════════════════════════════════
Luma Suno Gamma Fal Runway Synthesia Descript ElevenLabs
Murf Respeecher Sonantic Papercup SpeechKit Sonix Krisp
Boomy Haiper InVideo Pictory OpusClip TypeStudio HeyGen
Colossyan HourOne D-ID Tavus
PikaLabs Midjourney StableDiffusion Ideogram LeonardoAI
Clipdrop Magnific Krea Recraft Artbreeder
Flawless DeepDub Respeecher Voicemod Altered
Aiva Endlesss Soundraw Beatoven Tuney
Kapwing FlexClip Clipchamp Magisto

# ═══════════════════════════════════════════════════════════
# 4. AI 搜索/知识管理
# ═══════════════════════════════════════════════════════════
Perplexity Youcom Glean AlphaSense Hebbia Consensus Elicit
SciSpace Sourcely Scite Jenni Paperpal Typeset IrisAI
Mem NotionAI OtterAI Fireflies Fathom Granola
Readwise Reader Reflect Snipd Podwise
Briefmatic Tactiq Bluedot Hugo Dirac
MemBeam Knowledgator Stacks AIAnywhere

# ═══════════════════════════════════════════════════════════
# 5. AI 代码/开发者工具
# ═══════════════════════════════════════════════════════════
GitHubCopilot Cursor Codeium Tabnine Replit Bolt Lovable
Windsurf Continue Pieces Sourcegraph BuildJet Depot
TestSprite QA Wolf BugBug Codacy Snyk Docker
KiloCode CosineFactory xIsland
CopilotKit SweepAI Greptile OpenCommit CodeGenie
MutableAI Debuild PythonAnychart

# ═══════════════════════════════════════════════════════════
# 6. AI Customer Service / Sales / CRM
# ═══════════════════════════════════════════════════════════
Intercom Zendesk Freshworks Gorgias Crisp Olark HelpShift
Ada KoreAI PolyAI Netomi DigitalGenius Astound Elevio
Freshchat Trengo Chaport CustomerIO
Kustomer Gladly Tymeshift MessageBird
Drift Salesloft Outreach Apollo ZoomInfo Gong Clari
Chorus Gong Wingman Jiminny

# ═══════════════════════════════════════════════════════════
# 7. AI HR / Recruiting / People
# ═══════════════════════════════════════════════════════════
TalentGenius Beamery Metaview Huddle Applied Tribepad
Clevry ThriveMap ArcticShores Sova Fasthr Detech Jobbio
Cognisium SnapHire
Lever Greenhouse Workable Breezy Hibob
Personio Rippling Gusto Justworks BambooHR
Lattice 15Five CultureAmp OfficeVibe Peakon
Pymetrics HireVue ModernHire Ideal EightfoldAI
SeekOut PhenomPeople iCIMS SmartRecruiters

# ═══════════════════════════════════════════════════════════
# 8. AI Fintech / Banking / Payments
# ═══════════════════════════════════════════════════════════
Stripe Plaid Brex Ramp Mercury Deel Payoneer Wise
Revolut Monzo Starling OakNorth Kroo Cleo Chip Plum
Moneybox Wealthify Freetrade Trading212 TrueLayer Currencycloud
Marqeta Unit Synctera Lithic
Square Block Robinhood Coinbase Kraken Gemini
Affirm Afterpay Klarna Zip Zilch
TransferWise WorldRemit Remitly Azimo MoneyGram
Pento MennaAI Marloo Swoop Fluidly
Countingup Coconut FreeAgent Crunch TaxScouts
Previse 9fin DueCourse iwoca MarketFinance Tide
Monese TransferGo

# ═══════════════════════════════════════════════════════════
# 9. AI Legal / Compliance
# ═══════════════════════════════════════════════════════════
Harvey RobinAI Luminance ThoughtRiver Definely Juro
GenieAI Legl WavelengthLaw Netlaw Avoka ClauseBase Lawhive
Jaxon Della Spellbook Alexi PaxtonAI Relaw
Ironclad LinkSquares Evisort Lexion
KiraSystems Keneox Disco Everlaw
Onit BusyLamp LawGeex LegalRobot

# ═══════════════════════════════════════════════════════════
# 10. AI Healthcare / Bio / Life Sciences
# ═══════════════════════════════════════════════════════════
Abridge OpenEvidence ChaiDiscovery PomeloCare Ambience
Xaira CeraCare KheironMedical Medopad SkinAnalytics Optellum
PatchAi Healx Relation MindFoundry Kortical RapidBird
Owkin Ibex Pimloc Infogrid Zegami
AdaHealth Babylon BuoyHealth YourMD PushHealth
Tempus FlatironHealth FoundationMedicine GuardantHealth
RecursionInnPharma Insitro BenevolentAI Exscientia
DeepMind Isomorphic PathAI PaigeAI VizAI
ButterflyNetwork CaptionHealth Aidoc ZebraMedical
Pager Medly Ro Ro

# ═══════════════════════════════════════════════════════════
# 11. AI EdTech
# ═══════════════════════════════════════════════════════════
CENTURYTech Sparx Seneca Tassomai PiTop Microbit BibliU
Perlego Kortext MyTutor Tutorful AtomLearning EdPlace
Kano SAMLabs Natterhub Quizlet Duolingo
Coursera Udacity Udemy KhanAcademy Brilliant DataCamp
Codecademy Pluralsight Skillshare Masterclass FutureLearn
GoStudent Brainly Photomath Socratic Cognii
CarnegieLearning Dreambox Knewton ALEKS

# ═══════════════════════════════════════════════════════════
# 12. AI Marketing / AdTech / Content
# ═══════════════════════════════════════════════════════════
HubSpot Salesforce Outreach Apollo ZoomInfo Gong Clari
Lavender StoryChief Contentscale Simplified Jasper Anyword
Rytr Writesonic CopyAI Peppertype GrowthBar Mutiny
Brandwatch BuzzSumo SproutSocial Hootsuite Buffer
Searchable FlickAI Decima Joggle Adzooma BrightBid
Peerius Qubit Yieldify Ozone Pure360 RedEye
Echobox Pulsar Chattermill Ometria SmartFocus
Conversocial Spektrix PiwikPRO Brand24 BuzzRadar
Meltwater Determ NewsWhip Talkwalker TrendHERO
Kamma Hubb SignalMedia Digimind Taggify
Percolate TrendKite

# ═══════════════════════════════════════════════════════════
# 13. AI Security / Cybersecurity
# ═══════════════════════════════════════════════════════════
Wiz Lacework SentinelOne CrowdStrike PaloAlto Darktrace
Snyk Aqua Systems Illumio Cybereason Orca Security
NormanShield HackerOne Bugcrowd
CortexXSOAR Fortinet CheckPoint TrendMicro McAfee
Sophos CarbonBlack Tanium Cylance Crowdstrike
Okta Auth0 DuoSecurity CloudFlare Zscaler
Netskope PaloAlto Prisma Sysdig Falco
Rapid7 Tenable Qualys Nexpose
GeordieAI Panaseer Egress Garrison ZoneFox
Glasswall RedSocks Senseon Traceable Darklantern
BluePrism

# ═══════════════════════════════════════════════════════════
# 14. AI Data / Analytics / BI
# ═══════════════════════════════════════════════════════════
Databricks Snowflake Dbt Fivetran Airbyte Monte Carlo
Sifflet Seldon Monolith Diffblue SignalBox Streetbees
Preamble ThoughtMachine TheAX Mapify LocAI Quantexa
Featurespace Onfido Tessian
Tableau PowerBI Looker Mode Hex Thoughtspot
Sigma Domo Sisense Metabase Superset
Dataiku DataRobot H2OAI DataStax Neo4j
Starburst Trino Presto Clickhouse
Seldon ArizeAI WhyLabs Gantry EvidentlyAI

# ═══════════════════════════════════════════════════════════
# 15. AWS Marketplace / Cloud / IT 咨询
# ═══════════════════════════════════════════════════════════
Accenture Deloitte IBM TCS Cognizant PwC Wipro Slalom
Infosys HCL Tech Mahindra Capgemini Atos DXC
BoozAllen Presidio Mission CDW ApexSystems CompassUOL
Infocepts FactualMinds Cloudreach Appsbroker Ancoris
MadeTech Kainos ANDDigital ScottLogic Version1
Noranalytos Rackspace Endava Avanade Thoughtworks
Elastic Palantir Sophos Sage InterSystems OpenText
RackspaceUK AWS Azure GCP OracleCloud
SalesforceCloud GoogleCloud MSCloud

# ═══════════════════════════════════════════════════════════
# 16. 中国 AI 生态
# ═══════════════════════════════════════════════════════════
DeepSeek Baidu Alibaba Tencent ByteDance ZhipuAI
BaichuanAI Minimax InfinigenceAI Stepfun LingyiAI MoonshotAI
SenseTime Megvii CloudWalk Yitu PonyAI WeRide
Momenta HorizonRobotics Datagain PulseAI ShukunTechnology
Infervision YituTech Airdoc ModelBest GigaAI EngineAI
Unitree PuduRobotics DeepGlint 4Paradigm Bonree

# ═══════════════════════════════════════════════════════════
# 17. 全球 AI 独角兽 / 明星公司
# ═══════════════════════════════════════════════════════════
OpenAI Anthropic Mistral SafeSuperintelligence ThinkingMachinesLab
ReflectionAI Nscale Baseten FireworksAI Modular LangChain
Factory Youcom Modal Lovable Luma Suno Gamma Fal
IneffableIntelligence Waabi SkildAI PhysicalIntelligence
FigureAI MindRobotics BedrockRobotics SuduTech TARS
GenkiRobotics GeckoRobotics
Cohere Writer Typeface Jasper StabilityAI
InflectionAI AdeptAI Glean Harvey Perplexity
ScaleAI Runway Replicate OctoML TogetherAI

# ═══════════════════════════════════════════════════════════
# 18. 全球知名 AI/SaaS 产品
# ═══════════════════════════════════════════════════════════
NotionAI Grammarly Canva Figma Miro Asana Monday
ClickUp Airtable Coda Notion Linear Height Plane
Brew Activepieces Zapier Make Integromat

# ═══════════════════════════════════════════════════════════
# 19. UK / EU 科技 & AI 公司 (详细)
# ═══════════════════════════════════════════════════════════
DeepMind Synthesia Graphcore Wayve Huma BenevolentAI
Exscientia InstaDeep Faculty Centauric SignalAI
Cleo TrueLayer Revolut Monzo Starling OakNorth
Kroo Chip Plum Moneybox Wealthify Freetrade Trading212
PolyAI Speechmatics AudioTelligence Soniox SpeechKey
Seldon Monolith Diffblue ThoughtMachine Featurespace
Onfido Tessian SignalBox
# UK HR/AI Recruiting
Beamery Metaview JackJillAI Huzzle Tribepad
Clevry ThriveMap Applied Rungway Perkbox PipDecks
RewardGateway ArcticShores Sova Fasthr Detech
Jobbio Spotted SnapHire Cognisium
# UK Marketing/AdTech
Brandwatch Peerius Qubit Yieldify Ozone Pure360
RedEye Echobox Pulsar Chattermill Ometria SmartFocus
Conversocial Spektrix PiwikPRO Brand24 BuzzRadar
Meltwater Determ NewsWhip Talkwalker TrendHERO
Kamma Hubb SignalMedia Digimind Taggify
Percolate TrendKite
# UK Content/Creative
ContentCal Lumen5 FilmBot Jukedeck Sonantic Papercup
SpeechKit Sonix Krisp Murf Respeecher Haiper
InVideo Pictory OpusClip TypeStudio Audlent Speechmatics
AudioTelligence AIMusic Boomy
# UK Fintech
Cleo Pento MennaAI Marloo Swoop Fluidly
Countingup Coconut FreeAgent Crunch TaxScouts
Previse 9fin DueCourse iwoca MarketFinance Tide
Monese TransferGo Azimo Currencycloud TrueLayer
Chip Plum Moneybox Wealthify Trading212 Freetrade
Revolut Monzo Starling OakNorth Kroo
# UK Legal
Luminance ThoughtRiver Definely Juro GenieAI Legl
WavelengthLaw Netlaw Avoka ClauseBase Lawhive RobinAI
Jaxon Della Spellbook Alexi PaxtonAI
# UK EdTech
CENTURYTech Sparx Seneca Tassomai PiTop Microbit
BibliU Perlego Kortext MyTutor Tutorful AtomLearning
EdPlace ThirdSpaceLearning Studiosity KanoComputing SAMLabs
Natterhub
# UK Healthcare
CeraCare KheironMedical Medopad SkinAnalytics Optellum
PatchAi Healx Relation MindFoundry Kortical RapidBird
AIBuild POKit Binfluencer Owkin Ibex Pimloc
Infogrid ChAI Zegami
# UK Data/Analytics
StoryStream Boomtrain Kaskada RavenPack SignalMedia
DataSift GeoPhy StatusToday ArtificialLabs Concirrus
nPlan
# UK Property/RealEstate
Mashroom Nested Boomin Goodlord Ozo Plentific
Fixflo Kestrix Hubble Essensys Density Locale
# UK Productivity/Collaboration
Granola SolveAI Attio ZeroOneCreative DatalineLabs
Capsule PipelineCRM OnePageCRM Teamgate NetHunt
Freshsales CloseCRM Copper Nimble Insightly
BluePrism Trayio Paddle

# ═══════════════════════════════════════════════════════════
# 20. UK MSP / IT 服务公司 (CRN / 渠道)
# ═══════════════════════════════════════════════════════════
# 大型 UK MSP
Computacenter Softcat CDWUK InsightUK XMA Trustmarque
Wavenet AlternativeNetworks DaisyGroup Claranet Maintel
Node4 M247 GCI Redwood SixDegrees Exponentiale
ANSGroup UKFast KCOM Jisc Kerv Boxxe
SCC MitelUK AzzureIT Whitegold Baltimore
Rackspace Endava Avanade Thoughtworks CapgeminiUK
Elastic Palantir Sophos Darktrace Sage InterSystems
MicroFocus OpenText Wayve Graphcore
# UK 云/技术咨询
Advania Apogee Bytes CHP CKS ClerksWell
ContentCloud CPS CreativeITC Dabber Datalink EACS
Eagle Epaton Eqalix Excel Express Extreme
Exsel FCS Focus Foursys Goss HCS Heath
Hyve Intelligent Intercity Involeo IPG Jola
Jumar Khipu Krystal Liverton Longira Lucidica
Magnet Mako Mansfield Marval MCSA Mint Morris
Nasstar Neos Network Nexus Nottingham OCS
Onecom Onetech Onyx Open Orange Osiris
OSW Oxygen Parity PCS Peak PeterConnects
Pinnacle Portland Prodec Pulsant Qcom Qolcom
RedMoor Reply Risual Rock Roke Rydal
Saepio Saints Sentinel Severn Sharptext Silverbug
Simply Six Softcat Solnet Sound Sparta
Splash Storm Sydney Syscap Systems Talus Tata
TCS TechData Telent Telsoc Thomas Tiscali
TP Ubertas Uniden Vayant Versutile Vorboss
Vox Westcoast Wifinity Zynstra

# ═══════════════════════════════════════════════════════════
# 21. 全球 IT 咨询 / 系统集成 (Top 500)
# ═══════════════════════════════════════════════════════════
Accenture Deloitte IBM Consulting PwC EY KPMG
TCS Infosys HCLTech Wipro TechMahindra Cognizant
Capgemini Atos DXC Delloite Digital BCG Platinion
McKinseyDigital Bain Leghart Slalom Kainos
Globant EPAM Systems Perficient Cognizant Softvision
NTTData Fujitsu HitachiVantara NEC Solutions
T Systems CGI Logica SopraSteria Indra AtosOrigin
Unisys GDIT Leidos SAIC BoozAllen CACI
ScienceApps KeyW Perspecta Engility

# ═══════════════════════════════════════════════════════════
# 22. 全球 MSP / MSSP (CRN / Channel Futures)
# ═══════════════════════════════════════════════════════════
NexusTek OmegaSystems ParkPlace Netgain NetAtWork
AlcottEnterprises Verinext MGTConsulting NetGainTech
ManagedSolution LogicalisUS TPxCommunications
AndromedaTech BetterWorldTech EMPIST
Presidio CDW InsightEn wwt WorldWideTech
SHI International Connection En Pointe
Zone Technologies MainstreamTech eMazzanti StanfieldIT
All Covered Bowne BDO Digital ProServe
GreenPages StrataCom EaseTech eGroupTech
Vology Pomeroy RedRiver C3Integrated
GDT Dataprise AccessGlobal AABACUS
Bit byBit KMicro TechPrecision CalTech
ICS Cygnul OneNeckIT TierPoint Flexential
DataBank QTS Cyxtera Equinix DigitalRealty
Rackspace Sunguard Navisite Concur Hostway
Peer1 Internap CoreSite CenturyLink

# ═══════════════════════════════════════════════════════════
# 23. 日本/韩国/东南亚 AI & 科技
# ═══════════════════════════════════════════════════════════
PreferredNetworks SakanaAI LeanValue LTSE DataRobot
ThinkingMachines DatroAI
RapidAPI SoftBank NEC Fujitsu Toshiba Sony
Panasonic Hitachi Rakuten Mercari LINE YahooJapan
Naver Kakao Coupang Baedal Minyong

# ═══════════════════════════════════════════════════════════
# 24. 印度 AI & 科技
# ═══════════════════════════════════════════════════════════
Freshworks Gupshup Sarvam SonataSoftware Zoho Chargebee
Postman BrowserStack Hasura Razorpay Cred
Infosys TCS Wipro HCLTech TechMahindra
MakeMyTrip Ola Flipkart Paytm Nykaa
PharmEasy Swiggy Zomato UrbanCompany Oyo

# ═══════════════════════════════════════════════════════════
# 25. 中东/以色列 AI & 科技
# ═══════════════════════════════════════════════════════════
Wix Monday AI21Labs JonLaser RunAI DeciAI
Wix Monday WalkMe Fiverr Lemonade
Hibob AppsFlyer IronSource Mobileye
CheckPoint Waze HopOn Moovit Gett
Trax RetailRedefined Tanium CyberReason

# ═══════════════════════════════════════════════════════════
# 26. 更多 AI 工具 (Product Hunt / G2 精选)
# ═══════════════════════════════════════════════════════════
MonicaAI Perplexity Copilot GrammarlyGO Writesonic
Jasper CopyAI Anyword Simplified Contentscale Rytr
Murf Synthesia Descript Runway ElevenLabs Krisp OtterAI
Fireflies Memotion Timely Pictory InVideo Fliki
DesignsAI Magician Uizard Visily GalileoAI Mintlify
BuildShip Encord Labelbox Tango Loom Dubble Scribe
Mem NotionAI
Warp Hyper Tide PoolGenie Wondercraft
Cassette Riffusion KerasChat FetchCode
Yess AiSflow Scrintal Typogram Detangle
Taskade Fibery Superflows Stepshot 10web
InboxPro MayaAI ListAssist Boltai

# ═══════════════════════════════════════════════════════════
# 27. 云计算 / 基础设施公司
# ═══════════════════════════════════════════════════════════
AWS Azure GoogleCloud OracleCloud DigitalOcean
Linode Vultr Hetzner OVH Scaleway UpCloud
Packet BareMetal CloudSigma ProfitBricks IONOS
CloudFlare Fastly Akamai StackPath Imperva
MongoDB Atlas Supabase PlanetScale NeonRail
Railway Render NorthFlank Koyeb Pulumi
Terraform HashiCorp Docker CloudBees CircleCI

# ═══════════════════════════════════════════════════════════
# 28. AI 代理 / 自动化平台
# ═══════════════════════════════════════════════════════════
Zapier Make Integromat TrayIO Workato
AutomationAnywhere UiPath BluePrism Kryon
NICE ActionBot Ada KoreAI PolyAI
RelevanceAI Fixie AIAgent Swirl AgentHub
AgentLayer Superagent AutoGPT BabyAGI
CrewAI LangGraph AutoGen Semantic Kernel

# ═══════════════════════════════════════════════════════════
# 29. VCs / Accelerators / 投资机构
# ═══════════════════════════════════════════════════════════
YCombinator Sequoia A16Z Accel Benchmark Lightspeed
Andreessen Index Ventures Greylock KleinerPerkins
TigerGlobal Softbank InsightPartners GeneralCatalyst
Felicis FirstRound NEA Bessemer Matrix

# ═══════════════════════════════════════════════════════════
# 30. 更多行业公司 (Manufacturing / Logistics / Energy AI)
# ═══════════════════════════════════════════════════════════
Samsara Uptake C3AI SparkCognition Falkonry
ElementAnalytics FeroLabs SightMachine Augury
ScaleAI Labelbox V7 Supervisely Dataloop
Tractable Snapsheet Claim Genius
Routific Route4Me OptimoRoute DispatchTrack
Project44 FourKites Flexport Convoy UberFreight
Tesla Nuro Aurora Cruise Waymo Zoox
""".split()

# ============================================================
# 工具函数
# ============================================================

# 明显不是公司名的词（类别标题、注释残留等）
NON_COMPANY_WORDS = {
    "ai", "aiai", "all", "and", "are", "best", "can", "data",
    "digital", "for", "from", "global", "group", "has", "have",
    "into", "its", "list", "managed", "management", "more", "new",
    "news", "not", "our", "privacy", "search", "security",
    "services", "service", "solutions", "solution", "software",
    "systems", "team", "tech", "technology", "technologies",
    "that", "the", "their", "them", "they", "this", "top",
    "was", "were", "will", "with", "your",
    # 类别标题残留
    "2024", "2025", "2026", "companies", "company",
    "ecosystem", "electric", "energy", "enterprise", "finance",
    "financial", "health", "healthcare", "human", "industry",
    "intelligence", "international", "learning", "life",
    "machine", "manufacturing", "marketing", "marketplace",
    "media", "medical", "msp", "network", "networks",
    "online", "physical", "platform", "platforms", "product",
    "provider", "providers", "publishing", "research",
    "resources", "review", "robotics", "scientific", "self",
    "service", "social", "special", "startup", "startups",
    "super", "supply", "support", "tools", "training",
    "university", "virtual", "work", "ycombinator",
    "accelerators", "aisaas", "cyber", "fintech",
    "biotech", "cleantech", "proptech", "legaltech",
    "adtech", "insurtech", "edtech", "hrtech",
    "martech", "salestech", "medtech", "agritech",
    "foodtech", "climatetech", "greentech", "all",
}


def normalize(name):
    """公司名 → 统一 base name"""
    name = name.strip().lower()
    # 跳过头盔注释符号
    if name.startswith("#"):
        name = name[1:]
    name = name.replace("-", "").replace("_", "").replace(".", "")
    name = name.replace("'", "").replace("&", "").replace(",", "")
    name = name.replace(" ", "").replace("(", "").replace(")", "")
    name = name.replace(":", "").replace("!", "").replace("?", "")
    name = name.replace("@", "").replace("#", "")
    name = name.replace("$", "").replace("%", "").replace("+", "")
    name = name.replace("═", "").replace("║", "").replace("─", "")
    name = name.replace("╔", "").replace("╗", "").replace("╚", "")
    name = name.replace("╝", "")
    # 数字尾缀变体
    if name.startswith("the"):
        name = name[3:]
    return name


def is_valid_company_name(name):
    """判断是否为有效的公司名"""
    n = normalize(name)
    # 长度过滤
    if len(n) < 4 or len(n) > 30:
        return False
    # 纯数字
    if n.isdigit():
        return False
    # 全是非字母字符
    if not any(c.isalpha() for c in n):
        return False
    # 非公司词
    if n in NON_COMPANY_WORDS:
        return False
    # 以 "yyyy" 年份结尾且长度 ≤ 8 (如 "20242026")
    if len(n) >= 8 and n[-4:].isdigit() and n[:4].isdigit():
        return False
    # 包含 unicode box-drawing chars 的纯装饰词
    if len(set(n) - set("abcdefghijklmnopqrstuvwxyz0123456789")) > 3:
        return False
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


# ============================================================
# 候选生成
# ============================================================

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
        candidates -= dedup
    MAX_CANDIDATES = 20000
    result = sorted(c for c in candidates if len(c) >= 4)
    random.seed(123)
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
            except: pass
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE) as f:
                data = json.load(f)
            for key in ("eligible", "exists"):
                for code in data.get(key, []):
                    tested.add(code)
        except: pass
    return tested


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
    """增量保存"""
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
    print(f"🚀 ChatGPT Team 促销码超大规模发现 v3 — AI+MSP 全枚举")
    print(f"{'='*60}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    state = load_progress() if resume else None
    if state:
        print(f"🔁 恢复进度: {state.get('completed', 0)}/{state.get('total', 0)}\n")

    # 1. 构建池
    print("📦 构建公司名池 (AI + MSP 全枚举)...")
    if state:
        bases = state["bases"]
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
    print(f"  ✅ 生成了 {len(candidates)} 个候选码 (上限 20000)\n")

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

        # 保存
        merged = save_results(all_results)
        save_progress({
            "completed": completed, "total": total,
            "results": all_results,
            "tested_codes": list(tested | set(candidates[:completed])),
            "bases": bases, "candidates": candidates,
            "timestamp": datetime.now().isoformat(),
        })

        elapsed_total = found_eligible + found_exists
        pct = f"{elapsed_total / max(completed, 1) * 100:.2f}%"
        print(f"  📈 进度: {completed}/{total} | "
              f"✅{found_eligible} | 🔶{found_exists} | 命中率: {pct}")

    # 5. 汇总
    elapsed_total = found_eligible + found_exists
    print(f"\n{'='*60}")
    print(f"📊 扫描完成!")
    print(f"{'='*60}")
    print(f"  总测试: {completed}")
    print(f"  ✅ ELIGIBLE: {found_eligible}")
    print(f"  🔶 EXISTS:   {found_exists}")
    pct = f"{elapsed_total / max(completed, 1) * 100:.2f}%"
    print(f"  命中率: {pct}")

    if elapsed_total > 0:
        print(f"\n📋 所有有效码:")
        for code, status in sorted(all_results.items()):
            if status in ("ELIGIBLE", "EXISTS"):
                print(f"    {'✅' if status == 'ELIGIBLE' else '🔶'} {code}")

    print(f"\n📝 结果保存: {RESULTS_FILE}")

    # 清理
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)


if __name__ == "__main__":
    resume = "--resume" in sys.argv
    run(resume=resume)

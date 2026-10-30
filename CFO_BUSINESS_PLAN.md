# Silica — Financial Model & Unit Economics (cfo.ai Plan)

**Platform:** Autonomous Semiconductor Engineering Platform  
**Target Market:** Fabless Semiconductor Startups, Hardware Design Teams, ASIC/FPGA Engineers  
**Product Initiative:** Enterprise Autonomous Semiconductor Architecture & EDA Platform

---

## 1. Executive Summary & Value Proposition

Traditional semiconductor design cycles take 6–18 months and require multi-million-dollar EDA tool licenses (Synopsys, Cadence, Siemens). Silica automates the front-end chip design lifecycle (Specification -> RTL -> Verification -> Synthesis -> Signoff) with specialized 7B Qwen2.5 LoRA agents and automated Verilator/Yosys execution, compressing block delivery from weeks to minutes.

---

## 2. Pricing Tiers

| Tier | Price | Target Customer | Features Included |
| :--- | :--- | :--- | :--- |
| **Starter / Individual** | **$49 / month** | Academic / Independent Hardware Hackers | Up to 100 RTL generations/mo, cloud Verilator simulation |
| **Pro Engineering Seat** | **$199 / seat / month** | Semiconductor Startups & SME Design Teams | Unlimited RTL generation, full Verilator + Yosys pipeline, automated failure diagnosis |
| **Enterprise / Custom** | **$1,499 / team / month** | Fabless ASIC / SoC Design Enterprises | Dedicated EC2 runner instance, custom PDK integration, private Hugging Face adapter hosting, SLA |
| **Usage-Based (On-Demand)** | **$0.50 / synthesized block** | Burst usage & batch design exploration | Pay-as-you-go synthesis runs with signoff reports |

---

## 3. Cost of Goods Sold (COGS) & Unit Economics

### Monthly Infrastructure Cost (per 10 Active Teams):
* **AWS EC2 Backend Runner (`t3.medium` / `c6i.large` with Docker, Verilator, Yosys):** $35.00 / month
* **Model Inference (4x Qwen 7B LoRA Adapters on Hugging Face / EC2 spot):** $0.01 per run (~$25.00 / month for 2,500 runs)
* **AWS DynamoDB (Metadata & User storage):** Free tier ($0.00 / month up to 25 GB)
* **AWS S3 / Artifact storage (Verilog netlists, logs, AST traces):** $2.50 / month
* **Total Direct COGS per Active Pro Customer:** **$23.50 / seat / month**

### Unit Economics per Pro Seat ($199 / month):
$$\text{Revenue} = \$199.00$$
$$\text{COGS} = \$23.50$$
$$\text{Gross Profit} = \$175.50$$
$$\text{Gross Margin} = \mathbf{88.2\%}$$

---

## 4. Financial Projections (3-Year Forecast)

| Metric | Year 1 | Year 2 | Year 3 |
| :--- | :--- | :--- | :--- |
| **Active Paid Seats** | 50 seats | 350 seats | 1,800 seats |
| **Annual Recurring Revenue (ARR)** | **$119,400** | **$835,800** | **$4,298,400** |
| **Hosting & Cloud COGS (12%)** | $14,100 | $98,700 | $507,600 |
| **Gross Profit (88%)** | **$105,300** | **$737,100** | **$3,790,800** |
| **Net Operating Margin** | 42% | 61% | 68% |

---

## 5. Market Size (TAM / SAM / SOM)

* **TAM (Total Addressable Market):** Global Semiconductor EDA Market = **$16.5 Billion** (CAGR 9.1%)
* **SAM (Serviceable Addressable Market):** Front-End ASIC / FPGA Design Tools = **$3.8 Billion**
* **SOM (Serviceable Obtainable Market):** Startups and agile hardware design teams adopting AI-EDA = **$190 Million**

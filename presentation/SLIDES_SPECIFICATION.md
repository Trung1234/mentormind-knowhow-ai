# MentorMind — Denso Hackathon AI Challenge
## Complete AI Slide Generator Specification & Master Prompts

> **Topic:** Accumulate Master Know-How for AI to Learn (MentorMind)  
> **Format Alignment:** **1:1 Chuẩn Đề Bài & Cấu Trúc PPT Gốc** (`Denso_Master_KnowHow_Slides.pptx` & PDF)  
> **Orientation:** **16:9 Horizontal Widescreen (Chiều Ngang)** — No vertical portrait squishing  
> **Target Audience:** Denso Hackathon Judging Committee, Factory Plant Managers, AI Researchers  
> **Language:** Professional English (with bilingual Vietnamese section mapping tags)  
> **Design Theme:** Industrial Precision Tech / Cyber-Dark Luxury (Denso Red, Obsidian Black, Electric Cyan, Emerald Green)  
> **GitHub Repository:** [https://github.com/Trung1234/mentormind-knowhow-ai](https://github.com/Trung1234/mentormind-knowhow-ai)  
> **Working Branch:** `vinh/feat-api-ui` ([PR #17](https://github.com/Trung1234/mentormind-knowhow-ai/pull/17))  
> **Generated PDF:** `presentation/MentorMind_Denso_Presentation.pdf` (8 Pages, 16:9 Landscape)

---

## Table of Contents
1. [Global Visual Identity & Styling Guide (16:9 Horizontal)](#global-visual-identity--styling-guide)
2. [Section A: Slide-by-Slide Detailed Blueprint (Format Đề Bài 1:1)](#section-a-slide-by-slide-detailed-blueprint)
   - [Slide 1: COVER · TIÊU ĐỀ (DENSO HACKATHON · AI CHALLENGE)](#slide-1-cover--project-identity)
   - [Slide 2: CONTEXT · BỐI CẢNH (Tri thức chuyên gia đang rời khỏi nhà máy)](#slide-2-context--critical-shopfloor-pain-points)
   - [Slide 3: THE CHALLENGE · ĐỀ BÀI (DELIVERABLES SAU 3 THÁNG)](#slide-3-the-challenge--4-measurable-deliverables)
   - [Slide 4: REFERENCE CASE · CASE THAM KHẢO ("Factory Workers Are Training AI...")](#slide-4-international-case-study--cautionary-lessons)
   - [Slide 5: LESSONS LEARNED · BÀI HỌC RÚT RA (Hai cách tiếp cận đối lập)](#slide-5-paradigm-shift--replacement-vs-empowerment)
   - [Slide 6: SOLUTION · GIẢI PHÁP (Thiết bị capture + cơ chế khuyến khích)](#slide-6-the-mentormind-4-step-solution-loop)
   - [Slide 7: ARCHITECTURE · KIẾN TRÚC (5 bước kỹ thuật hoàn chỉnh)](#slide-7-5-layer-system-architecture)
   - [Slide 8: ROADMAP · LỘ TRÌNH (Từ capture đến trợ lý AI trong 3 tháng)](#slide-8-3-month-execution-roadmap--vision)
3. [Section B: One-Click Master Prompt for AI Tools (Gamma / Tome / Beautiful.ai / ChatGPT)](#section-b-one-click-master-prompt-for-ai-tools)
4. [Section C: Marp Markdown Presentation Code (Native PPTX/PDF Export)](#section-c-marp-markdown-presentation-code)

---

## Global Visual Identity & Styling Guide

* **Color System:**
  * **Background Core:** Obsidian Night (`#07090E` / `#0D121F`) with subtle ambient micro-grid.
  * **Brand Primary:** Denso Crimson Red (`#E60012` / `#FF2A3B`).
  * **Technical Secondary:** Electric Cyber Cyan (`#00D2FF`).
  * **Success & Verification:** Emerald Green (`#10B981`).
  * **Warning / Caution:** Amber Gold (`#F59E0B`).
  * **Typography Color:** High-contrast Pure White (`#FFFFFF`) for titles, Slate Gray (`#94A3B8`) for body copy.
* **Typography Hierarchy:**
  * **Headings:** Modern Display Sans (e.g., *Outfit*, *Plus Jakarta Sans*, *Inter* - Bold/Black weights).
  * **Body & Metrics:** Clean Precision Sans (e.g., *Inter*, *Roboto*).
  * **Data & Technical Tags:** Monospace (e.g., *JetBrains Mono*, *Fira Code*).
* **Overall Mood:**
  * Precision manufacturing meets cutting-edge enterprise AI.
  * **Not a playful startup pitch** — this is an industrial-grade, secure, human-centric AI solution designed for high-precision automotive factories.

---

## Section A: Slide-by-Slide Detailed Blueprint

---

### Slide 1: Cover & Project Identity

* **Slide Category:** Title / Hero
* **Headline:** Accumulate Master Know-How for AI to Learn
* **Subheadline:** Digitizing expert craftsman know-how on the factory floor — capturing tacit knowledge directly from operational workflow and verbal reasoning without manual documentation.
* **Badges & Metadata:**
  * Event: `DENSO HACKATHON · AI CHALLENGE 2026`
  * Team: `MentorMind Team`
  * Focus Process: `Automotive Precision Kitting & Packing Assembly`
  * GitHub Branch: `vinh/feat-api-ui` ([PR #17](https://github.com/Trung1234/mentormind-knowhow-ai/pull/17))
* **Visual Direction / AI Image Prompt:**
  > *Cinematic close-up of skilled industrial technician hands assembling precision automotive components next to a high-tech glowing holographic data stream, dark moody factory background with Denso red laser accents, clean cyber-industrial lighting, 8k resolution, editorial photography style.*
* **Layout Structure:**
  * **Left 65%:** Hero title with gradient emphasis on "Know-How", subheadline, agenda pills (01. Context → 02. Problem → 03. Case Study → 04. Paradigm Shift → 05. Solution → 06. Architecture → 07. Roadmap).
  * **Right 35%:** High-tech product badge card showing the MentorMind core loop icon and Denso Hackathon logo.
* **Speaker Script (30 seconds):**
  > "Good morning esteemed judges! We are MentorMind. Today, we address the critical challenge of capturing tacit expert knowledge in manufacturing. Instead of forcing technicians to write endless paper SOPs that nobody reads, MentorMind captures master know-how directly from natural work cycles and verbal explanations. Let’s walk through how we empower artisans and preserve Denso’s craftsmanship."

---

### Slide 2: Context & Critical Shopfloor Pain Points

* **Slide Category:** Section 01 · Factory Reality
* **Headline:** Expert Knowledge Is Silently Leaving the Factory Floor
* **Subheadline:** The looming retirement wave and the deep divide between static documentation and real-world high-precision assembly.
* **Content Structure (2-Column Grid):**
  * **Left Column — 3 Acute Pain Points:**
    1. **Master Artisans Retiring:** Veteran technicians retire, taking with them decades of unwritten, instinctual know-how accumulated through hands-on craftsmanship.
    2. **SOPs Cannot Keep Up:** Bulky manual SOPs are slow to update and fail to capture micro-gestures, hand orientation angles, and live troubleshooting instincts.
    3. **Multimodal VLM + RAG Opportunity:** Vision-Language Models and GraphRAG present a historic opportunity to capture and replicate this knowledge — *if done ethically and at the right moment*.
  * **Right Column — Denso Automotive Specialization Focus Card:**
    * **Header:** High Precision & Craftsmanship Dependence
    * **Callout Quote:** *"Denso automotive components require ultra-tight tolerances. A slight deviation in placement angle or insertion pressure can trigger cascading defects across an entire lot."*
    * **Key Metrics:**
      * `80%`: Tacit unwritten knowledge in factory operations.
      * `≤ 5 Mins`: Target containment window to identify and arrest defect propagation.
* **Visual Direction / AI Image Prompt:**
  > *Industrial infographic illustration showing veteran craftsman hands retiring on one side, juxtaposed against a robotic assembly line and an empty workbench, subtle warning red data telemetry, dark technical style.*
* **Speaker Script (45 seconds):**
  > "Why is this urgent for Denso right now? Senior technicians are retiring at an unprecedented rate, taking unwritten tribal knowledge with them. Traditional manuals can't capture the subtle tactile feedback of kitting sensitive automotive sensors. In high-precision manufacturing, a 1-millimeter angular mistake triggers cascading lot defects. We need AI that learns from human masters before that knowledge is lost forever."

---

### Slide 3: The Challenge & 4 Measurable Deliverables

* **Slide Category:** Section 02 · Challenge & Deliverables
* **Headline:** Accumulate Master Know-How for AI to Learn
* **Subheadline:** Build an end-to-end system that captures expert workflows and reasoning into a knowledge base, powered by LLMs to reuse tacit knowledge for similar tasks — zero manual documentation required.
* **Content Structure (4-Card Bento Grid):**
  * **Card 1: Deliverable 01 — Standardized Capture Template**
    * *Description:* Machine-readable `WorkProfile` schema (JSON/JSONL) capturing granular steps, key points, underlying reasons ("why"), exceptions, and pass criteria.
    * *Tags:* `JSON Schema` · `WorkProfile` · `Step-by-Step`
  * **Card 2: Deliverable 02 — Hybrid Knowledge Base**
    * *Description:* Unified graph and vector storage combining Neo4j (equipment-symptom-rootcause-procedure graph) and PostgreSQL pgvector (dense HNSW + lexical RRF).
    * *Tags:* `Neo4j Graph` · `PostgreSQL pgvector` · `GraphRAG`
  * **Card 3: Deliverable 03 — Dual LLM Assistants**
    * *Description:* Station-side Work Assistant for apprentice guidance with strict source citations, and Root Cause Analysis (RCA) Agent for 5-Why investigation linked to Sigma MES.
    * *Tags:* `Work Assistant` · `RCA 5-Why Agent` · `Citation Engine`
  * **Card 4: Deliverable 04 — Usefulness Evaluation Report**
    * *Description:* Quantitative empirical benchmark report powered by Ragas (Faithfulness ≥ 0.85, Relevancy ≥ 0.80) and real-world A/B testing on novice technicians.
    * *Tags:* `Ragas Framework` · `Golden QA Set (30+)` · `A/B Testing`
* **Footer Tech Stack Banner:**
  * `Qwen3-VL 8B (Self-Hosted)` · `Neo4j GraphRAG` · `PostgreSQL + pgvector` · `MediaPipe Hands` · `Docling OCR` · `FastAPI & Python 3.11`
* **Speaker Script (45 seconds):**
  > "We committed to four tangible deliverables over our 3-month roadmap: First, a standardized WorkProfile schema capturing not just what is done, but *why*. Second, a Hybrid Knowledge Base unifying Neo4j GraphRAG with pgvector. Third, Dual AI Assistants serving both the apprentice and the quality manager. Fourth, rigorous empirical verification via Ragas metrics."

---

### Slide 4: International Case Study & Cautionary Lessons

* **Slide Category:** Section 03 · International Case Study
* **Headline:** When Knowledge Capture Takes an Exploitative Turn
* **Subheadline:** Cautionary lessons from investigative reporting: *"Factory Workers Are Training AI to Replace Them… Here's the Truth"* (Source: youtu.be/5BoTtw8s33g).
* **Content Structure (2-Column Comparative Hazard Analysis):**
  * **Left Column — Collection Method (Passive Exploitation):**
    * Garment and manufacturing workers in India equipped with head-mounted cameras throughout full shifts.
    * Capturing fine-motor gestures and tactile dexterity — real-world "egocentric" data impossible to synthesize in AI labs.
    * Targeting developing markets with low wages (~$240/month) and zero cross-border data protection barriers compared to the US or EU.
  * **Right Column — Consequences & Ethical Risks:**
    * Low-wage workers inadvertently train their own automated replacements without consent, transparency, or shared value.
    * Fosters workplace paranoia, active resistance, and knowledge hoarding across the workforce.
    * Macroeconomic dilemma: If extreme automation displaces human workers entirely, who will have the purchasing power to consume?
  * **Key Takeaway Box:**
    * *"AI must never be deployed as a covert surveillance tool that destroys worker trust."*
* **Visual Direction / AI Image Prompt:**
  > *A surveillance-style camera view showing factory workers from behind with red warning wireframe overlays, dystopian industrial aesthetic, highlighting the conflict between covert data collection and worker trust.*
* **Speaker Script (45 seconds):**
  > "To build an AI that works in real factories, we analyzed an international cautionary tale where Indian factory workers wore head-mounted cameras throughout their shifts. The company covertly used their fine-motor data to train robots to replace them. The result? Total loss of trust, sabotage, and knowledge hoarding. If artisans feel exploited, any AI deployment is doomed to fail."

---

### Slide 5: Paradigm Shift — Replacement vs. Empowerment

* **Slide Category:** Section 04 · Core Philosophy
* **Headline:** Two Opposing Approaches: Replacement vs. Empowerment
* **Subheadline:** The fundamental distinction between an AI project that triggers shopfloor resistance and one embraced by factory artisans.
* **Content Structure (Direct Side-by-Side Comparison Table):**

| Evaluation Criteria | Extract & Replace *(The Old Trap / Case Study)* | Capture & Empower *(MentorMind Approach)* |
| :--- | :--- | :--- |
| **Core Purpose** | Outright worker replacement through aggressive automation | Preserve, standardize, and amplify master know-how for future generations |
| **Expert Role** | Passive, covertly monitored, uninformed of data objectives | Active co-creator, final approver, attributed and cited in every AI answer |
| **Incentive System**| None — basic low wage, zero profit-sharing | Career rewards, reputation benefits, and bonuses for verbal explanations |
| **Organizational Outcome** | Broken trust, knowledge hoarding, ethical backlash, friction | Knowledge succession secured, collaborative culture, proud master artisans |

* **Visual Direction / AI Image Prompt:**
  > *Split screen visualization: Dark menacing robotic arm displacing a human worker on the left vs warm collaborative interface where human expert and AI assistant work side-by-side on the right, high contrast.*
* **Speaker Script (45 seconds):**
  > "This comparison is the core philosophy of MentorMind. We reject 'Extract & Replace'. We practice 'Capture & Empower'. Instead of treating artisans as data cattle, we treat them as honored mentors. Master technicians review and approve every profile, earn bonus points for verbal explanations, and their names are proudly cited every time the AI assists an apprentice."

---

### Slide 6: The MentorMind 4-Step Solution Loop

* **Slide Category:** Section 05 · Comprehensive Solution
* **Headline:** Non-Invasive Capture + Verbal Explanation Incentives
* **Subheadline:** A streamlined 4-step loop transforming real-world craftsmanship into structured digital intelligence.
* **Content Structure (Horizontal 4-Step Pipeline):**
  1. **Step 1: Non-Invasive Capture**  
     * Fixed station camera records 3–5 minute natural work cycles.  
     * Zero change to production flow, zero disruption to takt time.
  2. **Step 2: Explain & Incentivize**  
     * The master pauses for 30s to explain *"why rotate the part 90 degrees?"*  
     * Instantly earns professional recognition and bonus credits.
  3. **Step 3: Multimodal AI Processing**  
     * 3-pass VLM pipeline (self-hosted Qwen3-VL) + Docling OCR auto-generates WorkProfile drafts.  
     * The expert simply reviews and clicks "Approve".
  4. **Step 4: Store & Activate**  
     * Ingested into Knowledge Graph (Neo4j) + Vector (pgvector).  
     * Expert name is permanently linked and cited in all station Q&A.
* **Core Differentiator Banner:**
  * *"Experts are approvers, not document writers. Experts are rewarded for sharing know-how, never covertly exploited."*
* **Visual Direction / AI Image Prompt:**
  > *Sleek 4-stage circular industrial workflow diagram showing camera capture, microphone audio wave, neural network processing, and a knowledge graph network, illuminated with neon cyan and Denso red lights.*
* **Speaker Script (45 seconds):**
  > "Here is how MentorMind works in four elegant steps: Step 1: A camera records the assembly cycle naturally. Step 2: The artisan pauses for 30 seconds to explain the critical 'why', earning immediate reward credits. Step 3: Our 3-pass VLM auto-generates a structured WorkProfile draft. Step 4: The profile is stored into our GraphRAG database, permanently citing the master's name."

---

### Slide 7: 5-Layer System Architecture

* **Slide Category:** Section 06 · Technical Architecture
* **Headline:** MentorMind 5-Layer System Architecture
* **Subheadline:** Air-gapped self-hosted VLM, Hybrid Retrieval (GraphRAG + pgvector), and Dual AI Agents guaranteeing enterprise-grade data security.
* **Content Structure (Vertical 5-Layer Interactive Stack):**
  * **Layer 1: Multimodal Ingestion**  
    * Station video (4–8 fps gesture sampling), commentary microphone, Docling OCR for blueprints & SOP PDFs.
  * **Layer 2: Multimodal VLM Pipeline (3-Pass)**  
    * *Pass 1:* MediaPipe Hands temporal segmentation.  
    * *Pass 2:* Air-gapped self-hosted Qwen3-VL 8B (BF16 on 24GB GPU) step description.  
    * *Pass 3:* Task Graph synthesis & JSON Schema enforcement.
  * **Layer 3: Hybrid Knowledge Base**  
    * Neo4j Knowledge Graph (`Equipment -has-> Symptom -caused_by-> RootCause -fixed_by-> Procedure`).  
    * PostgreSQL pgvector (Dense HNSW + Lexical full-text with Reciprocal Rank Fusion RRF).  
    * Sigma MES Adapter (lot tracking and defect logs).
  * **Layer 4: Dual AI Agents**  
    * **Work Assistant:** Station-side Q&A for apprentices with strict citations and refusal guards.  
    * **RCA Agent:** 5-Why root cause analysis assistant for shift supervisors with A3/8D draft generation.
  * **Layer 5: Continuous Evaluation**  
    * Automated Ragas benchmark (Faithfulness ≥ 0.85, Relevancy ≥ 0.80) + Novice technician A/B benchmarks.
* **Blueprint Reference:**
  * High-Resolution System Architecture Blueprint available at `presentation/assets/architecture-diagram.png`.
* **Speaker Script (60 seconds):**
  > "Our technical architecture is built for strict factory data privacy. Layer 1 ingests video, audio, and schematics via Docling. Layer 2 runs an air-gapped, self-hosted Qwen3-VL model on a single 24GB GPU. Layer 3 couples Neo4j GraphRAG with PostgreSQL pgvector and Sigma MES logs. Layer 4 hosts Dual Agents: one for real-time station Q&A, one for 5-Why root-cause analysis. Layer 5 enforces automated Ragas quality gates."

---

### Slide 8: 3-Month Execution Roadmap & Vision

* **Slide Category:** Section 07 · 3-Month Plan & Vision
* **Headline:** From Factory Capture to AI Assistant in 3 Months
* **Subheadline:** A pragmatic, milestone-driven execution plan aligned with Denso Hackathon evaluation gates.
* **Content Structure (3-Month Milestone Roadmap):**
  * **Month 01: Capture & Standardization**  
    * Establish standardized `WorkProfile` template (JSON Schema).  
    * Deploy Docling OCR pipeline for technical schematics & SOPs.  
    * Ingest pilot video on Kitting & Packing station (Asian Alliance / Denso benchmark).
  * **Month 02: Knowledge Core & AI Agents**  
    * Deploy Neo4j Knowledge Graph + PostgreSQL pgvector (RRF).  
    * Ship station-side Work Assistant with strict citation verification.  
    * Develop RCA Agent with 5-Why reasoning linked to Mock Sigma MES.
  * **Month 03: Evaluation & Pilot Rollout**  
    * Run Ragas benchmark across Golden Set (30+ validation queries).  
    * Conduct A/B testing on novice technicians learning station workflows.  
    * Optimize latency and package final Usefulness Evaluation Report.
* **Closing Human-Centric Manifesto:**
  * *"Preserve Master Know-How — Empower Human Artisans, Never Replace Them."*
* **Project Reference Chip:**
  * GitHub Branch: `vinh/feat-api-ui` | Pull Request: [PR #17](https://github.com/Trung1234/mentormind-knowhow-ai/pull/17)
* **Speaker Script (30 seconds):**
  > "Our 3-month roadmap is execution-ready: Month 1 delivers standardized capture. Month 2 activates our GraphRAG core and Dual Agents. Month 3 validates with Ragas and tests live on novice technicians at the Denso assembly line. We leave you with our founding motto: 'Preserve Master Know-How — Empower Human Artisans, Never Replace Them.' Thank you!"

---

## Section B: One-Click Master Prompt for AI Tools
*(Copy and paste the text block below directly into **Gamma.app**, **Tome**, **Beautiful.ai**, **Canva AI**, **Claude**, or **ChatGPT** to generate the entire slide deck immediately)*

```markdown
Create a highly professional, 8-slide industrial presentation deck in 16:9 widescreen format based on the following detailed brief. 

Theme & Aesthetic:
- Topic: "MentorMind: Accumulate Master Know-How for AI to Learn (Denso Hackathon 2026)"
- Style: Industrial Cyber-Precision, Sleek Dark Mode (Obsidian black #07090E, Denso red #E60012, cyber cyan #00D2FF, emerald green #10B981). High contrast, premium enterprise engineering aesthetic.
- Tone: Inspiring, technically authoritative, human-centric, ethical AI.

Slide 1: Title & Overview
- Title: Accumulate Master Know-How for AI to Learn
- Subtitle: Digitizing expert craftsman know-how on the factory floor — capturing tacit knowledge directly from operational workflow and verbal reasoning without manual documentation.
- Meta: Denso Hackathon AI Challenge 2026 | Team MentorMind | Automotive Kitting & Packing Process | GitHub: vinh/feat-api-ui
- Layout: Large hero title on the left with gradient cyber accents, agenda pill stepper (Context -> Challenge -> Case Study -> Paradigm Shift -> Solution -> Architecture -> Roadmap).

Slide 2: Context & Critical Shopfloor Pain Points
- Title: Expert Knowledge Is Silently Leaving the Factory Floor
- Subtitle: The looming retirement wave and the deep divide between static documentation and real-world high-precision assembly.
- 3 Pain Points:
  1. Master Artisans Retiring: Decades of unwritten tacit know-how lost with veteran retirements.
  2. SOPs Cannot Keep Up: Static manuals fail to capture micro-gestures, hand orientations, and live troubleshooting instincts.
  3. Multimodal VLM + RAG Opportunity: Vision-Language Models and GraphRAG can capture and preserve this craftsmanship.
- Highlight Box (Denso Specialization): Automotive precision components have zero tolerance for error. A 1mm angular deviation in kitting triggers cascading lot defects. Key Stats: 80% Unwritten Knowledge | <= 5 Min Containment Window.

Slide 3: The Challenge & 4 Measurable Deliverables
- Title: Accumulate Master Know-How for AI to Learn
- Subtitle: Capture workflows and reasoning into a centralized knowledge base, reusing tacit wisdom with LLMs — zero manual documentation required.
- 4 Deliverables (Bento Grid Layout):
  1. Deliverable 01 - Standardized Capture Template: Machine-readable WorkProfile schema (JSON/JSONL) capturing steps, key points, "why" reasons, and exceptions.
  2. Deliverable 02 - Hybrid Knowledge Base: Neo4j Knowledge Graph + PostgreSQL pgvector dense/lexical RRF.
  3. Deliverable 03 - Dual LLM Assistants: Station Work Assistant (apprentice guidance with citations) + RCA 5-Why Agent (Sigma MES).
  4. Deliverable 04 - Usefulness Evaluation Report: Empirical Ragas benchmark (Faithfulness >= 0.85) + Novice A/B testing.
- Tech Stack Strip: Qwen3-VL 8B (Self-Hosted), Neo4j GraphRAG, pgvector, MediaPipe Hands, Docling OCR, FastAPI.

Slide 4: International Case Study & Cautionary Lessons
- Title: When Knowledge Capture Takes an Exploitative Turn
- Subtitle: Cautionary lessons from investigative reporting: "Factory Workers Are Training AI to Replace Them… Here's the Truth" (Source: youtu.be/5BoTtw8s33g).
- 2-Column Comparison:
  - Collection Method (Passive Exploitation): Workers equipped with head-mounted cameras all shift; capturing first-person egocentric motor dexterity; taking advantage of low wages (~$240/mo) and loose regulations.
  - Ethical Risks & Backlash: Workers unknowingly train their own replacements; triggers shopfloor paranoia, sabotage, and knowledge hoarding; macroeconomic dilemma of displaced consumers.
- Takeaway Callout: "AI must never be deployed as a covert surveillance tool that destroys worker trust."

Slide 5: Paradigm Shift — Replacement vs. Empowerment
- Title: Two Opposing Approaches: Replacement vs. Empowerment
- Subtitle: The fundamental distinction between an AI project that triggers shopfloor resistance and one embraced by factory artisans.
- Comparison Table:
  - Purpose: Extract & Replace = Outright worker replacement | Capture & Empower = Preserve and amplify know-how for future generations.
  - Expert Role: Extract & Replace = Passive, covertly monitored | Capture & Empower = Active co-creator, final approver, cited in every answer.
  - Incentives: Extract & Replace = None (low base wage) | Capture & Empower = Career recognition, rewards for explaining "why".
  - Outcome: Extract & Replace = Broken trust, knowledge hoarding | Capture & Empower = Knowledge succession, collaborative pride.

Slide 6: The MentorMind 4-Step Solution Loop
- Title: Non-Invasive Capture + Verbal Explanation Incentives
- Subtitle: A streamlined 4-step loop transforming real-world craftsmanship into structured digital intelligence.
- 4-Step Pipeline:
  - Step 1 - Non-Invasive Capture: Fixed station camera records 3-5 min natural work cycles without altering takt time.
  - Step 2 - Explain & Incentivize: Artisan pauses 30s to explain "why rotate 90°?" and earns immediate bonus points.
  - Step 3 - Multimodal AI Processing: 3-pass self-hosted VLM + Docling OCR auto-generates WorkProfile drafts for artisan approval.
  - Step 4 - Store & Activate: Ingested into GraphRAG + Vector, citing artisan name in all future AI answers.
- Core Banner: "Experts are approvers, not document writers. Experts are rewarded for sharing know-how, never covertly exploited."

Slide 7: 5-Layer System Architecture
- Title: MentorMind 5-Layer System Architecture
- Subtitle: Air-gapped self-hosted VLM, Hybrid Retrieval (GraphRAG + pgvector), and Dual AI Agents guaranteeing enterprise-grade data security.
- 5 Layers:
  - Layer 1 (Ingestion): Station video (4-8 fps), audio commentary, Docling OCR for blueprints & SOPs.
  - Layer 2 (Multimodal VLM): MediaPipe Hands segmentation + air-gapped Qwen3-VL 8B (BF16 on 24GB GPU) + Task Graph synthesis.
  - Layer 3 (Knowledge Base): Neo4j GraphRAG (Equipment-Symptom-RootCause-Procedure) + PostgreSQL pgvector RRF + Sigma MES.
  - Layer 4 (Dual Agents): Station Work Assistant (strict citations & refusal guards) + RCA 5-Why Agent (A3/8D drafts).
  - Layer 5 (Evaluation): Continuous Ragas evaluation (Faithfulness >= 0.85) + Novice A/B testing.

Slide 8: 3-Month Execution Roadmap & Vision
- Title: From Factory Capture to AI Assistant in 3 Months
- Subtitle: A pragmatic, milestone-driven execution plan aligned with Denso Hackathon evaluation gates.
- Milestones:
  - Month 01: Capture & Standardization (JSON schema, Docling OCR, Kitting & Packing pilot video).
  - Month 02: Knowledge Core & AI Agents (Neo4j GraphRAG + pgvector, Work Assistant citations, RCA 5-Why).
  - Month 03: Evaluation & Pilot Rollout (Ragas Golden QA 30+, Novice A/B testing, Usefulness Report).
- Closing Callout: "Preserve Master Know-How — Empower Human Artisans, Never Replace Them."
- GitHub Reference: https://github.com/Trung1234/mentormind-knowhow-ai/tree/vinh/feat-api-ui (PR #17)
```

---

## Section C: Marp Markdown Presentation Code
*(Can be pasted into VS Code with the Marp extension or converted to PPTX/PDF via `npx @marp-team/marp-cli`)*

```markdown
---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    background-color: #07090E;
    color: #F1F5F9;
    font-family: 'Inter', sans-serif;
    padding: 40px 60px;
  }
  h1, h2, h3 {
    color: #FFFFFF;
    font-family: 'Outfit', sans-serif;
  }
  h1 { font-size: 2.4rem; line-height: 1.1; margin-bottom: 0.5rem; }
  h2 { font-size: 1.9rem; color: #FFFFFF; margin-bottom: 0.3rem; }
  p { font-size: 1.05rem; color: #94A3B8; line-height: 1.5; }
  .badge {
    display: inline-block;
    background: rgba(230, 0, 18, 0.2);
    color: #FF2A3B;
    border: 1px solid rgba(230, 0, 18, 0.4);
    font-size: 0.75rem;
    font-weight: bold;
    padding: 4px 10px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .cyan { color: #00D2FF; }
  .red { color: #E60012; }
  .green { color: #10B981; }
  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
  .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
  .card {
    background: rgba(16, 23, 38, 0.8);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 10px;
    padding: 16px;
  }
  table {
    width: 100%;
    font-size: 0.9rem;
    border-collapse: collapse;
    margin-top: 10px;
  }
  th { background: rgba(255,255,255,0.08); color: #00D2FF; padding: 8px; text-align: left; }
  td { padding: 8px; border-bottom: 1px solid rgba(255,255,255,0.06); }
---

<!-- Slide 1 -->
<span class="badge">Denso Hackathon · AI Challenge 2026</span>

# Accumulate Master <span class="cyan">Know-How</span> for AI to Learn
### MentorMind: Digitizing Craftsman Wisdom on the Factory Floor

Capturing tacit knowledge directly from operational workflow and verbal reasoning — zero manual documentation required.

- **Focus Process:** Precision Kitting & Packing Assembly (Denso Benchmark)
- **Repository:** `Trung1234/mentormind-knowhow-ai` (`vinh/feat-api-ui`)
- **Key Agenda:** Context → Challenge → Case Study → Paradigm Shift → Solution → Architecture → Roadmap

---

<!-- Slide 2 -->
<span class="badge">Section 01 · Factory Reality</span>
## Expert Knowledge Is Silently Leaving the Factory Floor

<div class="grid-2">
<div class="card">

### Critical Shopfloor Pain Points
- **Master Artisans Retiring:** Decades of unwritten tribal wisdom lost with veteran retirements.
- **SOPs Cannot Keep Up:** Bulky paper manuals fail to capture micro-gestures and live troubleshooting instincts.
- **VLM + GraphRAG Opportunity:** Multimodal AI allows capturing craftsmanship at the right moment.
</div>

<div class="card" style="border-color: rgba(230,0,18,0.4);">

### Denso Automotive Stakes
- Automotive components require ultra-tight tolerances.
- A 1mm angular deviation in kitting triggers cascading lot defects.
- **Key Stats:**
  - **80%** Tacit unwritten knowledge.
  - **≤ 5 Mins** Target containment window.
</div>
</div>

---

<!-- Slide 3 -->
<span class="badge">Section 02 · Challenge & Deliverables</span>
## Accumulate Master Know-How for AI to Learn

<div class="grid-4">
<div class="card">
<h4 class="cyan">01. Capture Template</h4>
Standardized WorkProfile JSON schema capturing steps, key points, reasons, and exceptions.
</div>
<div class="card">
<h4 class="cyan">02. Hybrid Knowledge Base</h4>
Neo4j Knowledge Graph combined with PostgreSQL pgvector (dense + lexical RRF).
</div>
<div class="card">
<h4 class="cyan">03. Dual AI Assistants</h4>
Station Work Assistant with strict citations + 5-Why RCA Agent for Sigma MES.
</div>
<div class="card">
<h4 class="cyan">04. Usefulness Report</h4>
Empirical Ragas benchmark (Faithfulness ≥ 0.85) + Novice A/B testing on shopfloor.
</div>
</div>

**Suggested Tech Stack:** Qwen3-VL 8B (Self-Hosted) · Neo4j GraphRAG · pgvector · MediaPipe Hands · Docling OCR · FastAPI

---

<!-- Slide 4 -->
<span class="badge">Section 03 · International Case Study</span>
## When Knowledge Capture Takes an Exploitative Turn

<div class="grid-2">
<div class="card">

### Passive Exploitation (Investigative Case)
- Workers wore head-mounted cameras across full shifts.
- Capturing fine-motor dexterous data impossible to synthesize in labs.
- Exploiting low-wage regions (~$240/mo) with zero data sovereignty laws.
</div>

<div class="card" style="border-color: rgba(230,0,18,0.4);">

### Ethical Backlash & Hazard
- Workers unknowingly trained their own automated replacements.
- Caused workplace paranoia, knowledge hoarding, and passive sabotage.
- **Key Lesson:** AI must never be deployed as a covert surveillance tool that destroys worker trust.
</div>
</div>

---

<!-- Slide 5 -->
<span class="badge">Section 04 · Core Philosophy</span>
## Paradigm Shift: Replacement vs. Empowerment

| Dimension | Extract & Replace (The Trap) | Capture & Empower (MentorMind) |
| :--- | :--- | :--- |
| **Purpose** | Outright worker replacement | Preserve & amplify know-how for next generations |
| **Artisan Role** | Passive, covertly surveilled | Active co-creator, final approver, cited in AI answers |
| **Incentives** | None (low basic wage) | Career benefits & rewards for explaining "why" |
| **Outcome** | Broken trust, knowledge hoarding | Knowledge succession secured, collaborative pride |

---

<!-- Slide 6 -->
<span class="badge">Section 05 · Comprehensive Solution</span>
## Non-Invasive Capture + Verbal Explanation Incentives

<div class="grid-4">
<div class="card">
<h4 class="cyan">Step 1: Capture</h4>
Station camera records 3–5 min natural work cycles with zero takt time impact.
</div>
<div class="card">
<h4 class="cyan">Step 2: Explain</h4>
Artisan pauses 30s to explain "why rotate 90°?" and earns reward credits.
</div>
<div class="card">
<h4 class="cyan">Step 3: AI Process</h4>
3-pass self-hosted VLM + Docling OCR auto-generates WorkProfile draft.
</div>
<div class="card">
<h4 class="cyan">Step 4: Activate</h4>
Ingested into GraphRAG + Vector, citing artisan name in future station Q&A.
</div>
</div>

> **Core Differentiator:** Experts are approvers, not document writers. Experts are rewarded for sharing know-how, never covertly exploited.

---

<!-- Slide 7 -->
<span class="badge">Section 06 · Technical Architecture</span>
## MentorMind 5-Layer System Architecture

- **Layer 1 (Ingestion):** Station video (4–8 fps), commentary microphone, Docling OCR for blueprints & SOPs.
- **Layer 2 (Multimodal VLM):** MediaPipe Hands segmentation + self-hosted Qwen3-VL 8B (BF16 on 24GB GPU) + Task Graph synthesis.
- **Layer 3 (Hybrid Knowledge Base):** Neo4j Graph (`Equipment-Symptom-RootCause-Procedure`) + PostgreSQL pgvector RRF + Sigma MES.
- **Layer 4 (Dual AI Agents):** Station Work Assistant (citations & refusal guards) + RCA 5-Why Agent (A3/8D drafts).
- **Layer 5 (Evaluation):** Automated Ragas evaluation (Faithfulness ≥ 0.85) + Novice technician A/B testing.

---

<!-- Slide 8 -->
<span class="badge">Section 07 · 3-Month Plan & Vision</span>
## From Factory Capture to AI Assistant in 3 Months

<div class="grid-2">
<div class="card">

### Execution Timeline
- **Month 01:** Capture & Standardization (JSON schema, Docling OCR, Kitting pilot).
- **Month 02:** Knowledge Core & Agents (Neo4j GraphRAG, pgvector, Dual Agents).
- **Month 03:** Evaluation & Pilot Rollout (Ragas Golden QA 30+, Novice A/B testing).
</div>

<div class="card" style="border-color: rgba(16,185,129,0.5);">

### Closing Manifesto
> *"Preserve Master Know-How — Empower Human Artisans, Never Replace Them."*

- **GitHub PR:** [PR #17](https://github.com/Trung1234/mentormind-knowhow-ai/pull/17)
- **Branch:** `vinh/feat-api-ui`
</div>
</div>
```

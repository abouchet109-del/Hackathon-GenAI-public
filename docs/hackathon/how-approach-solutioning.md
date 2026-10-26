# How to APPROACH Solutioning For Your Track

**OPEN AGENT HACKATHON 2026 | Build an agent that does real work**

This guide helps you choose a feasible track and use case, scope your build correctly, assess whether the data is practical to use, and avoid common execution risks before you build.

The strongest teams will not necessarily pick the hardest idea. They will pick something they can execute convincingly within the hackathon constraints:

- **144-hour build window (22 October, 00:00 UTC to 27 October, 23:45 UTC)**
- **One primary track: one of the three challenge tracks, or the bonus track for existing projects (Wildcard [Tinkerer])**
- **Solo, or teams of up to 5 builders, with every participant on a team on HackOS**
- **Zetaris as your data layer, at least one Meterless Engine in a working feature, Meterless Nightshift as your primary AI provider, and NVIDIA wherever it contributes**
- **A working agent, not a demo or a chatbot**
- **Evidence of how the system reached its output**
- **Submission through HackOS by 27 October, 23:45 UTC**

---

## 1. The Goal: Pick a Use Case You Can Actually Deliver

This hackathon is not a theory exercise. Your submission must be a **working agent** that can be run and judged on what it produces.

A good use case choice balances four things:

| Factor | What You Need |
|---|---|
| **Problem fit** | A real business, societal, industry, or operational problem |
| **Team capability** | Skills you or your team already have or can learn quickly |
| **Data availability** | Open, accessible, lightweight data you can serve through Zetaris reliably |
| **Execution feasibility** | Runs end to end without manual setup |

**Do not choose based only on what sounds impressive.** Choose based on what you can build, test, explain, and defend.

---

## 2. The APPROACH Method

Use the **APPROACH** method before committing to a use case.

| Step | Meaning | Key Question |
|---|---|---|
| **A** | Assess the problem | Is the problem clear, valuable, and narrow enough? |
| **P** | Pick the right ambition level | Is this realistic for your team size and experience? |
| **P** | Prove data availability | Can you access usable data through Zetaris without manual steps or private keys? |
| **R** | Reduce the scope | What is the smallest impressive version you can build? |
| **O** | Outline agent collaboration | Do agents interact, critique, retry, or escalate? |
| **A** | Align with constraints | Will it run reliably and meet the sponsor technology requirements? |
| **C** | Confirm evaluation fit | Does it score well against the judging criteria? |
| **H** | Harden for submission | Can you deliver the demo video, slide deck, repository and sponsor explanation? |

---

## 3. Step A — Assess the Problem

Before writing code, define the problem in one sentence.

Use this format:

> **We are building an agent that helps [user/stakeholder] solve [specific problem] by [agent capability] using [data source], producing [output].**

### Good Examples

**Track 01: Solving Fragmented Intelligence**

> We are building an agent that helps an operations lead answer supplier questions by querying three disconnected systems through Zetaris, reconciling conflicting records, and producing a single sourced summary with the systems each fact came from.

**Track 02: The Agent That Can Explain Why**

> We are building an agent that helps a research analyst answer one bounded market question by gathering evidence across several sources, connecting the findings, and producing a cited recommendation that shows the evidence behind each conclusion.

**Track 03: Reasoning Architecture**

> We are building an agent that helps a small clinic's front desk decide how to handle incoming appointment requests by combining availability rules, priority policy, and memory of past decisions, and producing a prioritised booking list with the reasoning for each decision.

**Wildcard [Tinkerer]: Bring Your Own Project**

> We are extending our existing document-search prototype with Zetaris and a Meterless Engine to add a capability it did not have before, powered through Meterless Nightshift, and showing clearly what was built during the hackathon.

### Weak Examples

Avoid vague definitions such as:

- "We will build an AI platform for healthcare."
- "We will create a smart city agent."
- "We will automate investment decisions."
- "We will build a legal AI assistant."

These are too broad. Narrow the user, input, output, and decision supported.

---

## 4. Step P — Pick the Right Ambition Level

The tracks do not carry difficulty ratings. You set your own ambition level, and that decision matters more than the track you choose.

Use these three levels to judge what is realistic in 144 hours.

---

### Level 1 — Focused

Best if you want a high-quality, reliable, polished submission.

Typically involves:

- Clear input and output structure
- One accessible data source
- Low domain risk
- Fast prototyping
- Room to show real agent behaviour rather than plumbing

**Recommended for:**

- Solo builders
- Teams of two
- Teams new to agent frameworks
- Teams prioritising execution quality over complexity

**Aim for:** 2–4 agents, one data source in Zetaris, one Meterless Engine, one clear output, one refinement loop.

---

### Level 2 — Ambitious

Best if your team has strong engineering skills and can manage data pipelines, retrieval, evaluation, or domain-specific interpretation.

Typically involves:

- More complex orchestration
- Multiple data sources or APIs
- Higher need for reasoning quality
- More challenging evaluation

**Recommended for:**

- Teams of 2–5 builders
- Builders with agent framework experience
- Teams comfortable with APIs, retrieval, or graph data
- Teams that can cut scope aggressively when needed

**Aim for:** 3–5 agents, one or two data sources in Zetaris, one or two Meterless Engines, one bounded domain, at least one branch or retry path.

---

### Level 3 — High-risk

The most ambitious builds. They can score very well, but they are also the easiest to under-deliver.

They often involve:

- Complex domain knowledge
- Scientific, financial, medical, security, or city-scale problems
- Harder validation
- Larger datasets
- Greater risk of unsafe or unsupported claims

**Only choose this level if:**

- Your team has domain expertise
- You can build a narrow prototype rather than a platform
- You can rely on sample data or lightweight API calls
- You can explain limitations clearly
- You can avoid overclaiming accuracy, safety, or production readiness

**Aim for:** a very narrow slice, a small curated dataset, strong caveats, and no heavy training or simulation at runtime.

---

## 5. Step P — Prove Data Availability

A use case is only feasible if the data is accessible, legal to use, small enough, and reliable during judging.

Zetaris is your data layer. It can connect to databases, files such as CSV and Parquet, and web APIs, and lets your agent query all of them with SQL from one place. The Participant Setup Guide shows how to register a web API as a table and run your first query.

You can bring data in three ways:

| Option | Description | Good For | Risk |
|---|---|---|---|
| **A. Static data** | Small datasets in `/data`, placed where Zetaris can reach them | Reliability and reproducibility | Keep it small |
| **B. Automated download** | Script downloads data at build or runtime | Larger open datasets | Can fail or time out |
| **C. Public APIs registered in Zetaris** | The agent queries a public API through Zetaris during execution | Real-time or fresh data | API failures, rate limits, latency |

Zetaris can't read a file sitting on your laptop. Put files in storage Zetaris can reach, such as an S3 bucket, before registering them.

Large raw datasets should not be committed. Instead:

- Use a small curated sample
- Provide a download script
- Use lightweight API queries
- Include a `SAMPLE_MODE=true` fallback
- Cache only what the demo and judging need

If you prepare data before the build window opens, declare it as a pre-existing component in the submission form.

---

## 6. Data Guidance by Track

| Track | What Data Looks Like | Guidance |
|---|---|---|
| **Solving Fragmented Intelligence** | Several small sources that do not agree with each other: a CSV export, a public API, a database table, a document set | Register three or four small sources in Zetaris rather than one large one. The value is in discovering and working across them, not in volume. |
| **The Agent That Can Explain Why** | Documents, articles, filings, papers, records, or reports relevant to one question | Bound the question, the time window, and the source count. Keep every conclusion traceable to the evidence behind it, and cache a sample so the demo works if an API fails. |
| **Reasoning Architecture** | Operational records, rules or policies, and the state or memory of prior decisions | Define the decision and the action first, then the data, knowledge, and memory the agent needs to reach them reliably. A Meterless Engine such as H-MEM or World Model can hold memory and state. |
| **Wildcard [Tinkerer]** | Your existing project's data, plus what Zetaris and Meterless add | Keep what existed before separate from what you add during the hackathon, and declare pre-existing components, so the new work is easy to see. |

For all tracks, use small realistic or synthetic samples and avoid real personal or confidential data.

---

## 7. Data Availability Checklist

Before locking your use case, answer every question below.

### Access

- [ ] Is the dataset publicly accessible?
- [ ] Does it require registration, approval, or authentication?
- [ ] If authentication is required, can you avoid it by using a small permitted sample?
- [ ] Can you register it in Zetaris?
- [ ] Can a judge run your solution without manual data steps?

### Size

- [ ] Is the static data in your repository as small as it can be?
- [ ] Can the agent run using a small sample?
- [ ] Are large downloads avoided during execution?
- [ ] Have you removed unused files, raw archives, checkpoints, videos, and temporary data?

### Reliability

- [ ] Does your agent still work if a public API, Zetaris or Nightshift is down?
- [ ] Do you have a `SAMPLE_MODE=true` fallback?
- [ ] Are API calls bounded by timeouts?
- [ ] Are retries limited so a run cannot hang?

### Licensing and Sensitivity

- [ ] Is the data allowed for hackathon and prototype use?
- [ ] Does the data contain sensitive personal information?
- [ ] Have you avoided private, proprietary, confidential, or restricted datasets?
- [ ] Have you documented all data sources in your README?

### Evaluation

- [ ] Can judges understand how the data supports the output?
- [ ] Can your agent cite or reference evidence from the data?
- [ ] Can your system produce useful output from your sample inputs?

---

## 8. Step R — Reduce the Scope

Most weak submissions fail because they try to build too much.

Your goal is a **small but complete agent system**.

Use this formula:

> **One user + one decision + one data slice + one strong output + clear agent behaviour.**

### Scope Reduction Patterns

| If Your Idea Is Too Broad | Reduce It To |
|---|---|
| All systems in the organisation | Three disconnected sources that disagree |
| All markets | One company, sector, or scenario |
| All legal documents | One contract type or clause category |
| All healthcare diagnostics | One structured case type with safety caveats |
| All city operations | One city function such as traffic or incidents |
| All global news | One topic, one region, one time window |
| All research literature | 5–10 documents on one question |
| A full knowledge graph | 20–30 entities and their relationships on one topic |
| Full production dashboard | A working output plus an optional simple interface |
| Real-time ingestion | Cached sample plus an optional live mode |
| Memory of everything, forever | One decision type, with memory of prior decisions |
| Every Meterless Engine | One engine powering one clear feature |

### Recommended Minimum Viable Agent System

A strong build can be as simple as:

1. **Planner Agent** — interprets the request, chooses data and tools, delegates tasks
2. **Specialist Agent** — queries Zetaris, performs the analysis, produces evidence-backed findings
3. **Evaluator/Critic Agent** — reviews the output, flags gaps, risks, or unsupported claims, sends feedback for revision
4. **Reporter Agent** *(optional)* — produces the final structured response with confidence, limitations, and next steps

Add at least one Meterless Engine where it helps: H-MEM for memory across sessions, Markovian for long-running tasks, World Model for shared state between agents, or Scout Intent for routing requests to the right tool.

You do not need five agents if three collaborate well. **Quality of interaction matters more than number of agents.**

---

## 9. Step O — Outline Real Agent Behaviour

Judges are looking for agents that do real work, not task chaining.

### Weak Pattern

```text
Agent A → Agent B → Agent C → Final Output
```

This is weak if:

- Agents do not talk back to each other
- There is no critique or validation
- There are no retries
- There is no shared state or memory
- Each agent is just a prompt wrapper

### Strong Pattern

```text
Planner Agent
   ↓
Retriever / Analyst Agent (queries Zetaris)
   ↓
Evaluator Agent
   ↘ if weak evidence: sends revision request back to Analyst
   ↘ if risk detected: escalates to Risk Agent
   ↓
Reporter Agent
   ↓
Final Output with evidence, confidence, and limitations
```

Strong behaviour includes:

- Dynamic task delegation
- Back-and-forth communication
- Agents validating outputs
- Shared memory or state
- Branching based on confidence or risk
- Retry and recovery behaviour
- Role specialisation with real interdependence

### Collaboration Design Checklist

Your architecture should include at least three of these:

- [ ] Planner delegates subtasks based on the input
- [ ] Specialist agent uses data or tools
- [ ] Evaluator critiques the specialist output
- [ ] Agent revises output after critique
- [ ] Risk or safety agent flags unsupported claims
- [ ] Agents write structured messages to shared memory
- [ ] Workflow branches based on confidence
- [ ] Fallback path activates if data or an API fails
- [ ] Final answer includes traceable evidence

---

## 10. Step A — Align With Technical Constraints

Your use case must fit the execution environment and the sponsor technology requirements.

| Requirement | Rule |
|---|---|
| **Zetaris** | Required: your project's data layer, running locally in Docker |
| **Meterless** | Required: at least one Meterless Engine in a working feature, and Meterless Nightshift as your primary AI provider |
| **Cursor (with Space XAI)** | Optional: recommended AI coding tool. Any coding tool works |
| **NVIDIA** | Integrate wherever it contributes. Connect NVIDIA models through Nightshift |
| **Languages and frameworks** | Open choice |
| **Hardware** | Zetaris needs a laptop with 16 GB of RAM or more, or AWS. No local GPU needed |
| **Pre-existing work** | Work committed before the build window is not eligible, except clearly declared pre-existing components |
| **Runtime** | Keep runs bounded and predictable |
| **Static data** | Keep the repository light; use samples |
| **Secrets** | No API keys committed. The NVIDIA key goes in Nightshift, not your project |
| **Environment variables** | Use `.env.example` with placeholder values only |
| **Logs** | Save or print agent activity, including which model handled each request |
| **Examples** | Include sample inputs and outputs |
| **No manual setup** | Data loading and execution must be automated |
| **Submission** | Through HackOS by 27 October, 23:45 UTC, with the components listed in Step H |

---

## 11. Runtime Discipline

Even without a published time limit, a system that takes a long time to run is harder to demo, harder to judge, and more likely to fail during judging.

### How to Keep Runs Bounded

Do:

- Use small data samples
- Limit the number of documents processed
- Limit agent turns
- Set timeouts for Zetaris queries, Nightshift requests and external APIs
- Cache embeddings or sample data
- Include `SAMPLE_MODE=true`

Avoid:

- Full dataset downloads at runtime
- Processing thousands of documents
- Long unbounded agent debates
- Unbounded retries
- Large audio or video processing during the demo
- Model training at runtime
- Installing packages at runtime

### Suggested Runtime Budget

| Step | Target Time |
|---|---:|
| Startup | Under 30 seconds |
| Data load / Zetaris query | 30–90 seconds |
| Agent planning | 30–60 seconds |
| Retrieval / analysis | 1–4 minutes |
| Critique / refinement loop | 1–3 minutes |
| Final output generation | 30–90 seconds |
| Logging and response | Under 30 seconds |
| **Total target** | **5–10 minutes** |

---

## 12. Keeping the Repository Light

### Good Static Data Choices

- Sample CSV files
- Small JSON files
- Pre-filtered records
- Small text corpora
- Short transcripts
- Small synthetic test cases
- Precomputed lightweight indexes

### Risky Static Data Choices

- Raw full datasets
- Large archives
- Model checkpoints
- Full video or audio datasets
- Uncompressed logs
- Full Wikipedia or arXiv dumps
- Large database files

### Recommended Data Structure

```text
/project-root
│── data/
│   │── sample/
│   │   │── records_sample.json
│   │   │── metadata.csv
│   │── README.md
│   │── download_data.py           # optional
│── scripts/
│   │── register_zetaris_sources.sql
│── input_examples/
│── output_examples/
```

In `data/README.md`, document:

- Source URL
- Licence or usage note
- What subset you used
- How many records are included
- How it is registered in Zetaris
- How to regenerate or download the sample
- Any limitations

---

## 13. Step C — Confirm Evaluation Fit

Your use case should be designed to score well against the judging criteria. Judging begins immediately after submissions close, and each submission is reviewed by at least three judges.

| Criterion | Points | How Your Use Case Choice Affects It |
|---|---:|---|
| Impact | 30 | Choose a real problem with an obvious user and a decision that improves |
| Technical | 20 | Pick data and tools you can actually make work end to end, reliably |
| Innovation | 15 | Add a thoughtful agent pattern rather than a familiar workflow |
| Demo | 15 | Choose something you can show clearly in 1–4 minutes |
| Product & UX | 10 | Make the output intuitive and usable by the person it is meant for |
| Sponsor Tech | 10 | Show how Zetaris, your Meterless Engine, Nightshift and NVIDIA address the problem and enhance the product |
| **Total** | **100** | |

Ties are resolved on the Impact score, then on submission timestamp.

### Self-Scoring Before You Build

Score your proposed idea honestly.

| Question | Score 0–2 |
|---|---:|
| Can we explain the problem clearly in 30 seconds? |  |
| Do we know who the user is? |  |
| Do we have accessible data we can serve through Zetaris? |  |
| Can we build a working version in 144 hours? |  |
| Can it run quickly and predictably? |  |
| Do Zetaris and a Meterless Engine have a real role in the build? |  |
| Do agents interact more than once? |  |
| Is there critique, validation, or retry? |  |
| Can we show useful output in a 1–4 minute demo? |  |
| Can we document limitations clearly? |  |

**Interpretation:**

| Total | Recommendation |
|---:|---|
| 16–20 | Strong candidate use case |
| 11–15 | Feasible, but reduce scope |
| 6–10 | High risk; simplify significantly |
| 0–5 | Choose another use case |

---

## 14. Step H — Harden for Submission

Before committing to a use case, make sure you can meet the submission requirements. Submit through HackOS before 27 October, 23:45 UTC.

### Required Submission Components

| Component | Requirement |
|---|---|
| **Demo video** | 1–4 minutes, showing the main workflow, how the agent solves the selected challenge, its key features, and how Zetaris and Meterless are integrated |
| **Slide deck** | The problem and target users, the solution, the agent workflow or architecture, the technical stack, how Zetaris and Meterless were used, what was unique about your use of the sponsor technologies, product visuals, and future enhancements |
| **GitHub repository** | A public repository with all source code and a README covering setup, usage and dependencies. If your agents run in Google Colab, include the Colab links |
| **Sponsor technology explanation** | How Zetaris was integrated; which Meterless Engine(s) you implemented, what each does and the test showing it works; how your app connects to Meterless Nightshift; where NVIDIA technology contributes; and what was unique about your use of the sponsor technologies |

Declare any pre-existing components, including pre-existing product code, in the submission form.

### To Support Your Technical and Demo Scores

- A repository that runs from a clean setup
- Sample inputs and outputs
- Logs or traces showing how the agents worked
- A sample mode that runs without Zetaris, Nightshift or live credentials

---

## 15. Sponsor Technology Planning

| Workshop | Focus | Date |
|---|---|---|
| **DATA with Zetaris** | Setting up Zetaris and serving the data your agent works with | 12 October |
| **POWER** | Powering your product through Meterless Nightshift with NVIDIA models | 19 October |
| **BUILD with Meterless and Cursor** | Vibe coding a small agent with Cursor and the Meterless Engines prompt library | 21 October (two sessions) |

All recordings are in the Resource Center on HackOS, together with the **Participant Setup Guide**. Technical questions go to the #help desk channel, and sponsor questions to each sponsor's Help channel on HackOS.

The sponsor technology exists so you do not have to rebuild foundations during the build window. Zetaris and Meterless are required in every submission, including the Wildcard [Tinkerer] track, so design them into your architecture from the start rather than adding them at the end.

### Planning Tips

- Plan what data Zetaris will serve, which Meterless Engine you'll implement, and where NVIDIA models contribute, before day one.
- Start the Zetaris install first: it takes 30 to 45 minutes.
- Use the prompts at meterless.ai/engines.html to choose and implement your engine, including **POWER → Add Meterless as a provider** to connect your app to Nightshift.
- Run your connection tests on the first day, not the last.
- Keep prompts and payloads compact.
- Avoid passing full documents between agents; use summaries and shared state.
- Log errors from sponsor services clearly.
- Include fallback behaviour if a service is unavailable.
- Watch the sponsor workshop recordings before you design the architecture.

---

## 16. Track Selection by Team Type

### Solo Builder

Remember to create a team on HackOS with just yourself in it.

Recommended:

- **Solving Fragmented Intelligence** with three small sources
- **The Agent That Can Explain Why** on one bounded question
- **Wildcard [Tinkerer]** if you already have a working prototype

Avoid unless you have deep expertise:

- Any build needing several data pipelines
- Any regulated domain with heavy validation requirements

### Small Team — 2 to 3 Builders

Recommended:

- **The Agent That Can Explain Why** with a critic loop across several sources
- **Solving Fragmented Intelligence** with reconciliation and conflict handling
- **Reasoning Architecture** with a domain expert on the team

### Larger Team — 4 to 5 Builders

Recommended if roles are clear:

- **The Agent That Can Explain Why** with an interface that shows the evidence behind each answer
- **Reasoning Architecture** combining data, knowledge, memory, and a usable interface
- **Solving Fragmented Intelligence** across four or more sources

Split the work into:

- Agent orchestration
- Zetaris data setup and Meterless integration
- Domain logic
- Evaluation and testing
- Demo, slide deck and documentation

---

## 17. Recommended Scope by Ambition Level

### Focused

- 2–4 agents
- 1 data source in Zetaris
- 1 Meterless Engine
- 3–5 sample inputs
- 1 clear output format
- 1 refinement loop

```text
Planner ↔ Analyst ↔ Evaluator → Reporter
```

### Ambitious

- 3–5 agents
- 1–2 data sources in Zetaris
- 1–2 Meterless Engines
- One bounded domain or time window
- Retrieval or lightweight analytics
- At least one branch or retry path

```text
Planner
  ├── Retriever
  ├── Domain Analyst
  └── Risk / Critic
        ↘ revision loop
Reporter
```

### High-risk

- 3–5 agents
- Very narrow domain
- Small curated dataset
- Strong caveats and risk handling
- No heavy training or simulation at runtime
- A working fallback mode

```text
Planner
  ├── Evidence Retriever
  ├── Domain Reasoner
  ├── Safety / Risk Evaluator
  └── Recommendation Agent
        ↺ revise if unsupported
Final Report with limitations
```

---

## 18. Red Flags: Choose a Different Scope If…

You should reduce scope or pick another use case if:

- You need a private API key you do not have.
- You cannot access the dataset quickly.
- The dataset requires manual approval.
- The raw dataset is many GBs and you have no sample strategy.
- Your workflow requires GPU training.
- Your agents only run once in a fixed sequence.
- Zetaris and Meterless have no real role in your build.
- No feature of your product actually uses a Meterless Engine.
- You cannot explain the value clearly.
- Your output is mostly generic text.
- The system fails if an external API is unavailable.
- The demo requires manual steps not documented in the README.
- You cannot produce sample inputs and outputs.
- You cannot show how the agent reached its output.

---

## 19. Good Use Case Examples

### Example 1 — Solving Fragmented Intelligence

**User:** Operations lead  
**Data:** A supplier CSV export, a public risk API, and a ticket system extract, all registered in Zetaris  
**Agents:**

- Source Mapper
- Reconciler
- Conflict Critic
- Reporter

**Workflow:**

1. Source Mapper identifies which source can answer which part of the question.
2. Reconciler queries the sources through Zetaris and merges the records into one view.
3. Conflict Critic flags contradictions between sources and requests clarification.
4. Reconciler resolves or marks the conflict as unresolved.
5. Reporter produces a single sourced answer showing where each fact came from.

**Meterless Engine:** World Model keeps the shared record state consistent while the Reconciler and Conflict Critic both work on it.

**Why it works:** the disagreement between sources is the problem, the output is decision-oriented, and the provenance trail is easy to demo.

### Example 2 — The Agent That Can Explain Why

**User:** Research analyst  
**Data:** Sources for one bounded question, served through Zetaris  
**Agents:**

- Research Planner
- Retriever
- Evidence Summarizer
- Insight Critic
- Report Writer

**Workflow:**

1. Planner decomposes the question.
2. Retriever fetches a bounded set of sources, or uses cached samples.
3. Summarizer extracts findings and connects them across sources.
4. Insight Critic checks whether each claim is actually supported.
5. Report Writer produces a cited recommendation showing the evidence behind each conclusion.

**Meterless Engine:** Markovian keeps a multi-step investigation within bounded context, so the agent can work through more evidence without losing track.

**Why it works:** narrow scope, strong retrieval potential, easy to show critique, and every answer can be traced to its evidence.

### Example 3 — Reasoning Architecture

**User:** Clinic front desk  
**Data:** Synthetic appointment requests, availability rules, priority policy, and a record of past decisions  
**Agents:**

- Intake Agent
- Rules Checker
- Memory Keeper
- Priority Critic
- Scheduler

**Workflow:**

1. Intake Agent structures incoming requests.
2. Rules Checker tests each against availability and policy held in Zetaris.
3. Memory Keeper supplies past decisions on similar requests.
4. Priority Critic challenges decisions that look unfair, unsafe, or inconsistent with past decisions.
5. Scheduler produces a prioritised booking list with the reasoning for each decision.

**Meterless Engine:** H-MEM gives the Memory Keeper persistent memory of past decisions across sessions.

**Why it works:** data, rules, memory, and reasoning come together into a decision and an action that could realistically be used.

### Example 4 — Wildcard [Tinkerer]: Bring Your Own Project

**User:** Your existing project's users  
**Data:** Your existing project's data, extended with Zetaris and Meterless  
**Approach:**

1. Record the state of your project before the build window opens, and declare it as a pre-existing component.
2. Pick one capability the project does not have today.
3. Build that capability with Zetaris and a Meterless Engine, and connect the project to Meterless Nightshift as its AI provider.
4. Show the before and after in your demo.

**Why it works:** scoring covers the new work rather than prior development, so a clear before-and-after makes that work easy to see and score.

---

## 20. Weak Use Case Examples

### Weak Example 1 — Too Broad

> "We will build a smart city platform for traffic, utilities, safety, emergency response, and planning."

Problem: too many domains, too much data, hard to judge, likely to become a generic dashboard.

Better:

> "We will build an incident triage agent that analyses a small urban incident dataset and recommends resource allocation for three incident types."

### Weak Example 2 — No Real Agents

> "Agent 1 summarises data, Agent 2 writes the final answer, Agent 3 formats it."

Problem: linear pipeline, no critique, no dynamic decision-making, agents are prompt wrappers.

Better:

> "Planner assigns tasks, Analyst produces findings, Evaluator challenges unsupported claims, Analyst revises, Reporter creates the final output."

### Weak Example 3 — Data Too Heavy

> "We will download all of Wikipedia, arXiv, and a global news archive to build a knowledge graph."

Problem: impossible within the build window, too large, high failure risk.

Better:

> "We will build a small knowledge graph from 25 documents on one topic and generate hypotheses from the relationships."

### Weak Example 4 — Unsafe Overclaiming

> "Our healthcare agent diagnoses patients and recommends treatment."

Problem: high clinical risk, hard to validate, unsafe without caveats.

Better:

> "Our healthcare agent structures a synthetic patient case, generates possible differential diagnoses with evidence, flags red-flag symptoms, and recommends clinician review."

### Weak Example 5 — Sponsor Tech in Name Only

> "We installed a Meterless Engine and mention it in our README."

Problem: an engine no feature uses doesn't meet the Meterless requirement.

Better:

> "Our agent uses H-MEM to remember a user's earlier decisions and apply them in a later session, and our test shows it working."

---

## 21. One-Page Use Case Decision Worksheet

Complete this before building.

### Problem

**Selected track:**  
**Problem statement:**  
**Target user:**  
**Decision supported:**  
**Final output:**  

### Scope

**What we will build in 144 hours:**  
**What we will not build:**  
**Main demo scenario:**  
**Pre-existing components to declare:**  

### Data

**Primary data source:**  
**How it is registered in Zetaris:**  
**Static data size estimate:**  
**Runtime API required?** Yes / No  
**Fallback sample mode?** Yes / No  
**Licensing or sensitivity concerns:**  

### Sponsor Technology

| Sponsor | Requirement | Where It Fits in Our Build |
|---|---|---|
| Zetaris | Required: data layer |  |
| Meterless Engine(s) | Required: at least one in a working feature |  |
| Meterless Nightshift | Required: primary AI provider |  |
| NVIDIA | Where it contributes, through Nightshift |  |
| AI coding tool | Your choice (Cursor recommended) |  |

### Agents

| Agent | Role | Input | Output | Collaborates With |
|---|---|---|---|---|
| Agent 1 |  |  |  |  |
| Agent 2 |  |  |  |  |
| Agent 3 |  |  |  |  |
| Agent 4 |  |  |  |  |

### Collaboration

Check all that apply:

- [ ] Delegation
- [ ] Critique
- [ ] Revision loop
- [ ] Shared memory
- [ ] Branching
- [ ] Retry
- [ ] Escalation
- [ ] Confidence scoring
- [ ] Human-in-the-loop

### Constraints

- [ ] Runs from a clean setup with no manual steps
- [ ] Runs quickly and predictably
- [ ] Repository is light
- [ ] No hardcoded outputs
- [ ] No committed API keys
- [ ] Logs show how the agent worked
- [ ] Sample inputs and outputs included
- [ ] Zetaris is the data layer, a Meterless Engine works in a feature, Nightshift is the AI provider, and NVIDIA use is documented

---

## 22. Final Recommendation

Pick the use case where you can say **yes** to all five statements:

1. **We understand the problem and the user.**
2. **We can access the data reliably through Zetaris.**
3. **We can build a narrow working version in 144 hours, with Zetaris, a Meterless Engine and Nightshift integrated.**
4. **We can show agents doing real work.**
5. **We can run it cleanly and explain it in a 1–4 minute demo.**

If any answer is "no," reduce scope before you build.

The best submissions will be **focused, functional, evidence-backed, and reproducible**.

Build a system that works. Show agents that do real work. Use data responsibly. Stay within the constraints. Then make the demo clear.
# Trading Agents (LangGraph Edition)

A production-ready research and execution pipeline for single-name equities.  
The system ingests structured + unstructured data, fans out into domain personas,
debates bull/bear theses, and returns an auditable trade recommendation with
per-step artifacts.

## Architecture Overview

```
Seed → EvidenceHub → AnalystHub → ResearchDebateHub → ConsensusHub
       ↓               ↓                 ↓              ↓
    (mappers)     (tech/val/event/ macro/flow)   (bull vs bear)   (referee)

ConsensusHub → RiskHub → TraderHub → OversightHub → FinalizeDecision → Consolidate
```

### Stage Breakdown
| Stage | Description |
|-------|-------------|
| **EvidenceHub** | Parallel mappers fetch market, fundamentals, general news, policy news, and macro signals. Each mapper returns normalized `SourceObject` evidence. |
| **AnalystHub** | Domain specialists (technical, valuation, event, macro, flow) read the evidence and push structured JSON (stance, summary, evidence refs). |
| **ResearchDebateHub** | Bull and Bear researchers build opposing theses using analyst outputs. A neutral ResearchReferee synthesizes both into a consensus view with score/confidence. |
| **RiskHub / TraderHub / OversightHub** | Risk Manager sizes exposure, Trader creates the playbook, and Risk Judge enforces guardrails, producing the final governance-approved action. |
| **FinalizeDecision & Consolidate** | Final node converts oversight output into a canonical `decision` payload and `consolidate_state` merges all mapper/persona outputs into `data_sources` / `analyses` for downstream consumers. |

Every node writes a unique `m__` or `a__` key, so LangGraph can run everything in parallel without key collisions. After each stage, a hub node (e.g., `AnalystHub`) runs `consolidate_state` to hydrate the shared `GraphState` for the next set of personas.

## Key Modules
| Path | Purpose |
|------|---------|
| `tradingagents/langgraph/runner_langgraph.py` | Builds/compiles the LangGraph pipeline, streams progress logs, and writes step-by-step artifacts through `StepTracker`. |
| `tradingagents/langgraph/personas/*` | Persona implementations (analysts, researchers, traders). Each inherits from `BasePersona`, which handles prompt loading, LLM calls (real or mock), and JSON parsing/usage tracking. |
| `tradingagents/langgraph/personas/data_agents.py` | Evidence mappers for market data, fundamentals, news, policy, and macro. Each mapper outputs normalized `SourceObject` lists. |
| `tradingagents/langgraph/state.py` | Pydantic `GraphState` schema + helpers for token accounting and provenance. |
| `tradingagents/langgraph/builder_consolidate.py` | Consolidates mapper/persona outputs, aggregates token usage, and builds the final decision payload. |
| `tradingagents/utils/step_tracker.py` | Persists every node’s output to `data/reports/<TICKER>/<DATE>/steps/NN_Node.json` + the final state for audit/replay. |
| `tradingagents/utils/report_writer.py` | Saves JSON + Markdown reports (with telemetry, summaries, and links to step artifacts). |
| `sitecustomize.py` | Auto-loads `.env` files for *every* Python process (tests, LangGraph CLI, uvicorn) so LangSmith/OpenAI keys are always available. |

## Setup

### Prerequisites
- Python 3.12+
- Poetry 1.7+ (manages virtualenv + dependency locking)
- (Optional) LangSmith account for tracing

### Installation
```bash
poetry install
```

### Environment Configuration
Create `.env` at the repo root (or `.env.local` to override) with at least:
```
OPENAI_API_KEY=<your OpenAI key>      # or leave blank to run in mock/offline mode
LLM_MODEL=gpt-4o-mini                 # default in BasePersona
LANGSMITH_API_KEY=<your LangSmith key>
LANGSMITH_PROJECT=trading-agents
AUTO_SAVE_REPORTS=true                # writes JSON/Markdown after each run
REPORTS_DIR=./data/reports            # optional override
```

`sitecustomize.py` ensures these variables are loaded even when you run tools like
`poetry run langgraph dev` or `uvicorn`, so there’s no need to export them manually.

## Running the Pipeline

### 1. CLI Orchestrator
Runs the full pipeline once and logs each stage.
```bash
poetry run python -m tradingagents.services.orchestrator AAPL 2025-01-15
```
Outputs:
- Streaming INFO logs (mapper/analyst start + finish)
- Step artifacts under `data/reports/AAPL/2025-01-15/steps`
- Final JSON + Markdown report (`data/reports/AAPL/2025-01-15.{json,md}`)

### 2. LangGraph Studio (visual debugger)
```bash
poetry run langgraph dev tradingagents/langgraph/runner_langgraph.py:graph_app
```
Open the printed URL (default http://localhost:2023) to inspect the DAG, enter
run inputs, and stream intermediate results. LangSmith tracing automatically
captures runs if `LANGSMITH_API_KEY` is set.

### 3. Mermaid Diagram
Each CLI run writes `workflow.mmd` at the repo root. You can copy it into
your documentation or preview it with any Mermaid renderer.

## Observability & Audit Trail
- **LangSmith**: Traces every persona call + token usage. Data is grouped under
  `LANGSMITH_PROJECT`.
- **StepTracker**: JSON snapshots for *every* node, stored chronologically,
  which is critical for compliance audits or debugging.
- **Reports**: Human-readable Markdown summarizing decisions, telemetry, and
  linking back to the recorded step files.

## Development Notes
- The system degrades gracefully when vendor APIs are unavailable (deterministic
  synthetic market data, fallback fundamentals/policy/news items, mock LLM
  responses). This keeps CI and offline development predictable.
- Persona prompts live in `tradingagents/langgraph/prompts/`. Updating a prompt
  requires no code changes thanks to `BasePersona`’s auto-loader.
- Add new personas or data sources by creating a mapper/persona class and
  plugging it into `_fanout_stage` in `runner_langgraph.py`.

## Future Enhancements
- Plug real pricing/fundamental data vendors for production deployment.
- Extend personas for sector specialists or options strategists.
- Add automated regression tests per persona with frozen evidence fixtures.

Happy trading! 🚀

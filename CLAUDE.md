# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A production-ready LangGraph-based research and execution pipeline for single-name equities trading. The system uses a multi-agent architecture where specialized personas (analysts, researchers, traders) collaborate through a staged workflow to produce auditable trade recommendations.

## Development Commands

### Setup
```bash
poetry install                           # Install all dependencies
```

### Running the Pipeline
```bash
# Run full analysis pipeline via CLI orchestrator
poetry run python -m tradingagents.services.orchestrator AAPL 2025-01-15

# Run with LangGraph Studio (visual debugger)
poetry run langgraph dev tradingagents/langgraph/runner_langgraph.py:graph_app
```

### Testing
```bash
poetry run pytest tests/                 # Run all tests
poetry run pytest tests/unit/            # Run unit tests only
poetry run pytest tests/integration/     # Run integration tests only
```

## Environment Configuration

The project uses `sitecustomize.py` to auto-load environment variables from `.env` files for ALL Python processes (pytest, langgraph CLI, uvicorn). This means environment variables are automatically available without manual exports.

**Required environment variables:**
- `OPENAI_API_KEY` - LLM calls (leave blank for mock/offline mode)
- `LLM_MODEL` - Default model (e.g., `gpt-4o-mini`)
- `LANGSMITH_API_KEY` - Optional tracing
- `LANGSMITH_PROJECT` - LangSmith project name
- `AUTO_SAVE_REPORTS=true` - Auto-save JSON/Markdown reports after runs

See `.env.example` for complete configuration options including vendor API keys (Alpha Vantage, NewsAPI), cost controls, risk parameters, and cache settings.

## Architecture

### Pipeline Stages (Sequential)

The LangGraph workflow is organized into stages that execute in sequence, with parallel execution within each stage:

1. **Seed** → Initializes empty state
2. **EvidenceHub** → Parallel mappers fetch market/fundamentals/news/policy/macro data
3. **AnalystHub** → Domain specialists (technical/valuation/event/macro/flow) analyze evidence
4. **ResearchDebateHub** → Bull and Bear researchers build opposing theses
5. **ConsensusHub** → ResearchReferee synthesizes debate into consensus view
6. **RiskHub** → RiskManager sizes exposure
7. **TraderHub** → Trader creates execution playbook
8. **OversightHub** → RiskJudge enforces governance guardrails
9. **FinalizeDecision** → Converts oversight output to canonical decision
10. **Consolidate** → Merges all outputs into final state

### State Management

**GraphState Schema** (`tradingagents/langgraph/state.py`):
- Inputs: `ticker`, `as_of_date` (immutable)
- Raw data: `price_snapshot`, `fundamentals`, `news_general`, `news_policy`
- Ephemeral keys: `m__*` for mapper outputs (e.g., `m__market`, `m__fundamentals`)
- Persona keys: `a__*` for individual persona outputs (e.g., `a__TechnicalAnalyst`)
- Consolidated: `data_sources` (mappers), `analyses` (personas)
- Final: `decision`, `research_view`
- Telemetry: `token_usage`, `cost_usd`, `notes`

**Key Design Principle**: Each persona returns ONLY a unique top-level key (e.g., `{"a__TechnicalAnalyst": {...}}`) to prevent write collisions during parallel execution. The `consolidate_state` function merges these into shared keys after each stage completes.

### Persona System

**BasePersona** (`tradingagents/langgraph/personas/base_persona.py`):
- All personas inherit from `BasePersona`
- Auto-loads system prompts from `tradingagents/langgraph/prompts/`
- Handles LLM calls via `LLMService` with usage tracking
- Returns structured JSON outputs with stance/confidence/rationale
- Gracefully degrades when APIs unavailable (mock responses)

**Persona Types**:
- **Data Mappers**: Market, Fundamentals, News, Policy, Macro (return normalized `SourceObject` lists)
- **Domain Analysts**: Technical, Valuation, Event, Macro, Flow (structured JSON analysis)
- **Research Agents**: BullResearcher, BearResearcher, ResearchReferee (thesis building & synthesis)
- **Trading Agents**: RiskManager, Trader, RiskJudge (sizing, execution, governance)

### Observability

**StepTracker** (`tradingagents/utils/step_tracker.py`):
- Persists every node's output to `data/reports/<TICKER>/<DATE>/steps/NN_Node.json`
- Records final state for audit/replay
- Provides chronological snapshots for compliance

**LangSmith Integration**:
- Auto-enabled when `LANGSMITH_API_KEY` is set
- Traces every persona call with token usage
- Groups runs under `LANGSMITH_PROJECT`

**Reports**:
- Auto-generated if `AUTO_SAVE_REPORTS=true`
- JSON + Markdown formats at `data/reports/<TICKER>/<DATE>.{json,md}`
- Includes decision, telemetry, and links to step artifacts

## Key Implementation Details

### Adding New Personas

1. Create persona class inheriting from `BasePersona` in `tradingagents/langgraph/personas/`
2. Add system prompt to `tradingagents/langgraph/prompts/<persona_name>.txt`
3. Override `render_user_prompt()` for domain-specific formatting
4. Add to appropriate stage in `_fanout_stage()` call in `runner_langgraph.py`
5. Add persona key to `GraphState` schema if needed (e.g., `a__NewPersona`)

### Modifying Prompts

Prompts live in `tradingagents/langgraph/prompts/` and are loaded automatically by `BasePersona`. Update prompt files directly—no code changes required.

### Consolidation Logic

`consolidate_state()` in `builder_consolidate.py`:
- Merges `m__*` keys → `data_sources[<type>]`
- Merges `a__*` keys → `analyses[<persona_name>]`
- Aggregates token usage across all personas
- Must return small delta dict (not full state) to avoid conflicts

`finalize_decision()`:
- Extracts final action from RiskJudge > Trader > ResearchReferee (priority order)
- Builds canonical `decision` payload with stance/action/rationale/confidence

### Offline/Mock Mode

When `OPENAI_API_KEY` is blank or vendor APIs fail:
- `LLMService` returns deterministic mock responses
- Data mappers generate synthetic market data and fallback news items
- Pipeline remains fully functional for testing/CI

### Testing Strategy

- Unit tests in `tests/unit/` focus on individual components
- Integration tests in `tests/integration/` test full pipeline flows
- Minimal test coverage currently—expand with frozen evidence fixtures for reproducibility

## Common Development Workflows

### Debug a Single Persona
```bash
# Use LangGraph Studio to step through nodes
poetry run langgraph dev tradingagents/langgraph/runner_langgraph.py:graph_app
```

### Inspect Step Artifacts
```bash
# Check intermediate outputs from a run
cat data/reports/AAPL/2025-01-15/steps/05_TechnicalAnalyst.json
```

### Add a New Data Source

1. Create mapper class in `tradingagents/langgraph/personas/data_agents.py`
2. Return list of `SourceObject` dicts with `id`, `type`, `content`, `meta`, `timestamp`
3. Add to EvidenceHub stage in `runner_langgraph.py`
4. Add `m__<source_name>` field to `GraphState`

### Tune Cost Controls

Adjust in `.env`:
- `COST_MAX_USD` - Total run budget
- `COST_PER_NODE_TOKEN_CAP` - Per-persona token limit
- `COST_TRUNCATE_STRATEGY` - How to truncate context (middle/start/end)

### View Mermaid Workflow Diagram

Each run writes `workflow.mmd` at repo root. Preview with Mermaid renderer or LangGraph Studio.

## Dependencies

- **Python**: 3.12.3 (managed by Poetry)
- **Core**: LangGraph, LangChain, OpenAI, Pydantic
- **Data**: yfinance, pandas, numpy, ta (technical analysis)
- **Observability**: LangSmith (optional)
- **CLI**: langgraph-cli with inmem extras

## Project Structure Notes

- `tradingagents/langgraph/` - Core pipeline and personas
- `tradingagents/services/` - Orchestration layer
- `tradingagents/utils/` - Step tracking, report generation
- `tradingagents/config/` - Logging, defaults, provider configs
- `data/reports/` - Auto-generated analysis artifacts
- `tests/` - Unit and integration tests

from __future__ import annotations

import asyncio
import os
from datetime import date
from typing import Any, Dict, Iterable, Mapping

from langgraph.graph import END, START, StateGraph

from tradingagents.config.logging_config import get_logger, setup_logging
from tradingagents.langgraph.builder_consolidate import (
    consolidate_state,
    finalize_decision,
)

# import existing persona nodes (they're already callable)
from tradingagents.langgraph.personas.data_agents import (
    FundamentalsMapper,
    MacroMapper,
    MarketMapper,
    NewsMapper,
)
from tradingagents.langgraph.personas.domain_analysts import build_domain_analysts
from tradingagents.langgraph.personas.research_agents import (
    PersonaConfig,
    Synthesis,
)
from tradingagents.langgraph.personas.trader_agents import build_execution_personas
from tradingagents.langgraph.state import GraphState
from tradingagents.utils.step_tracker import StepTracker

setup_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)


def _fanout_stage(
    graph: StateGraph,
    *,
    upstreams: Iterable[str],
    stage_label: str,
    nodes: Mapping[str, Any],
) -> str:
    """
    Attach a stage of personas/mappers to the graph and consolidate their outputs.

    Parameters
    ----------
    graph : StateGraph
        The mutable LangGraph.
    upstreams : Iterable[str]
        Node names that must finish before this stage fan-out executes.
    stage_label : str
        Used to generate a human-readable hub node (e.g., "EvidenceHub").
    nodes : Mapping[str, Any]
        Mapping of node name → callable (persona or mapper).

    Returns
    -------
    str
        The name of the consolidation hub feeding the next stage.
    """
    hub_name = f"{stage_label}Hub"

    for node_name, persona in nodes.items():
        graph.add_node(node_name, persona)
        for upstream in upstreams:
            graph.add_edge(upstream, node_name)

    graph.add_node(hub_name, consolidate_state)
    for node_name in nodes.keys():
        graph.add_edge(node_name, hub_name)

    return hub_name


def build_langgraph_pipeline() -> StateGraph:
    """
    Optimized institutional-grade trading workflow.

    Flow: Seed → DataCollection → Analysis → Synthesis → RiskAssessment →
          ExecutionPlan → FinalOversight → FinalizeDecision → Consolidate → End

    Key improvements:
    - Consolidated PolicyMapper into NewsMapper
    - Replaced Bull/Bear/Referee debate with single Synthesis node
    - Sequential risk → execution → oversight flow (cleaner than separate hubs)
    - Time-horizon aware at every stage
    """
    g = StateGraph(GraphState)

    def seed_fn(state: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize empty state to avoid key collisions."""
        return {}

    g.add_node("Seed", seed_fn)
    g.add_edge(START, "Seed")

    # Stage 1: Data Collection (parallel mappers)
    # Returns: DataCollectionHub (with consolidated mapper outputs)
    data_stage_hub = _fanout_stage(
        graph=g,
        upstreams=["Seed"],
        stage_label="DataCollection",
        nodes={
            "MarketMapper": MarketMapper(),
            "FundamentalsMapper": FundamentalsMapper(),
            "NewsMapper": NewsMapper(),  # Now includes policy news
            "MacroMapper": MacroMapper(),
        },
    )

    # Stage 2: Analysis (parallel domain analysts)
    # Returns: AnalysisHub (with consolidated analyst outputs)
    analysts = build_domain_analysts()
    analysis_stage_hub = _fanout_stage(
        graph=g,
        upstreams=[data_stage_hub],
        stage_label="Analysis",
        nodes={
            "TechnicalAnalyst": analysts["technical"],
            "FundamentalAnalyst": analysts["fundamental"],
            "SentimentAnalyst": analysts["sentiment"],
            "MacroAnalyst": analysts["macro"],
            "FlowAnalyst": analysts["flow"],
        },
    )

    # Stage 3: Synthesis (replaces 3-node debate with single synthesis)
    synthesis_node = Synthesis(
        PersonaConfig(
            name="Synthesis",
            system_prompt_path="synthesis.txt",
            max_tokens=600,
            temperature=0.2,
        )
    )
    g.add_node("Synthesis", synthesis_node)
    g.add_edge(analysis_stage_hub, "Synthesis")

    # Stage 4-6: Execution Pipeline (sequential: risk → plan → oversight)
    execution = build_execution_personas()

    g.add_node("RiskAssessment", execution["RiskAssessment"])
    g.add_edge("Synthesis", "RiskAssessment")

    g.add_node("ExecutionPlan", execution["ExecutionPlan"])
    g.add_edge("RiskAssessment", "ExecutionPlan")

    g.add_node("FinalOversight", execution["FinalOversight"])
    g.add_edge("ExecutionPlan", "FinalOversight")

    # Stage 7: Finalize Decision (canonical decision payload)
    g.add_node("FinalizeDecision", finalize_decision)
    g.add_edge("FinalOversight", "FinalizeDecision")

    # Stage 8: Final Consolidate
    g.add_node("Consolidate", consolidate_state)
    g.add_edge("FinalizeDecision", "Consolidate")

    g.add_edge("Consolidate", END)
    return g


async def run_langgraph_pipeline(ticker: str, as_of_date: str, time_horizon: str = "medium") -> Dict[str, Any]:
    """
    Run optimized LangGraph workflow with visualization + per-step tracking.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        as_of_date: Analysis date in ISO format (e.g., "2025-01-15")
        time_horizon: Trading horizon - "short" (days-weeks), "medium" (1-6 months), "long" (1+ years)
    """
    print(f"🚀 Starting LangGraph analysis for {ticker} @ {as_of_date} (horizon: {time_horizon.upper()})")

    logger.info("🧠 Building optimized LangGraph pipeline...")
    graph = build_langgraph_pipeline()
    app = graph.compile()
    logger.info("🧱 Graph compiled.")

    try:
        g = app.get_graph()
        mermaid = g.draw_mermaid()
        with open("workflow.mmd", "w") as f:
            f.write(mermaid)
        print(
            "✅ Mermaid diagram saved as workflow.mmd (open it in VS Code with a Mermaid preview plugin or the LangGraph Studio)"
        )
    except Exception as e:
        print(f"⚠️ Could not export Mermaid graph: {e}")

    initial_state = GraphState(ticker=ticker, as_of_date=as_of_date, time_horizon=time_horizon).model_dump()
    logger.info("📥 Initial state prepared for %s @ %s (horizon: %s)", ticker, as_of_date, time_horizon)

    tracker = StepTracker(ticker, as_of_date)
    final_state: Dict[str, Any] | None = None

    async for event in app.astream_events(initial_state, version="v2"):
        name = event.get("name")
        ev_type = event.get("event")
        print(f"even name:{name}, ev_type: {ev_type}")
        if not name or not ev_type.startswith("on_chain_"):
            continue

        if ev_type == "on_chain_start" and name != "LangGraph":
            logger.info("➡️ %s started", name)
            continue

        if ev_type == "on_chain_end":
            output = event.get("data", {}).get("output")
            if name == "LangGraph":
                final_state = (
                    output.model_dump() if hasattr(output, "model_dump") else output
                )
                continue
            tracker.record_step(name, output)
            logger.info("✅ %s completed", name)

    if final_state is None:
        raise RuntimeError("LangGraph run did not produce a final state.")

    tracker.record_final_state(final_state)
    logger.info("🏁 LangGraph execution finished.")
    print("✅ Pipeline complete.")
    return final_state


graph_app = build_langgraph_pipeline().compile()


# ─────────────────────────────────────────────────────────────
# Standalone run for testing
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":

    async def _demo():
        print("🔧 Building LangGraph pipeline...")
        final_state = await run_langgraph_pipeline("AAPL", date.today().isoformat())
        print(f"\n✅ Final decision: {final_state}")
        if isinstance(final_state, dict):
            print(final_state.get("decision", {}))
        else:
            try:
                print(final_state.decision)
            except Exception:
                print({})

    asyncio.run(_demo())

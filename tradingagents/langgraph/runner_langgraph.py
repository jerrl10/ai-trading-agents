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

# import existing persona nodes (they’re already callable)
from tradingagents.langgraph.personas.data_agents import (
    FundamentalsMapper,
    MacroMapper,
    MarketMapper,
    NewsMapper,
    PolicyMapper,
)
from tradingagents.langgraph.personas.domain_analysts import build_domain_analysts
from tradingagents.langgraph.personas.research_agents import (
    BearResearcher,
    BullResearcher,
    PersonaConfig,
    ResearchReferee,
)
from tradingagents.langgraph.personas.trader_agents import build_trader_personas
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
    """Compose the institutional-grade trading workflow."""
    g = StateGraph(GraphState)

    def seed_fn(state: Dict[str, Any]) -> Dict[str, Any]:
        """Prime the graph with an empty delta to avoid key collisions."""
        return {}

    g.add_node("Seed", seed_fn)
    g.add_edge(START, "Seed")

    # Stage 1: Evidence ingestion (markets, fundamentals, news, policy, macro).
    evidence_stage = _fanout_stage(
        graph=g,
        upstreams=["Seed"],
        stage_label="Evidence",
        nodes={
            "MarketMapper": MarketMapper(),
            "FundamentalsMapper": FundamentalsMapper(),
            "NewsMapper": NewsMapper(),
            "PolicyMapper": PolicyMapper(),
            "MacroMapper": MacroMapper(),
        },
    )

    # Stage 2: Domain specialists digest the evidence.
    analysts = build_domain_analysts()
    analyst_stage = _fanout_stage(
        graph=g,
        upstreams=[evidence_stage],
        stage_label="Analyst",
        nodes={
            "technical": analysts["technical"],
            "valuation": analysts["valuation"],
            "event": analysts["event"],
            "macro": analysts["macro"],
            "flow": analysts["flow"],
        },
    )

    # Stage 3: Debate between bullish and bearish research leads.
    debate_stage = _fanout_stage(
        graph=g,
        upstreams=[analyst_stage],
        stage_label="ResearchDebate",
        nodes={
            "BullResearcher": BullResearcher(
                PersonaConfig(
                    name="BullResearcher",
                    system_prompt_path="bull_researcher.txt",
                    max_tokens=500,
                )
            ),
            "BearResearcher": BearResearcher(
                PersonaConfig(
                    name="BearResearcher",
                    system_prompt_path="bear_researcher.txt",
                    max_tokens=500,
                )
            ),
        },
    )

    # Stage 4: A neutral referee synthesizes the debate into a consensus view.
    consensus_stage = _fanout_stage(
        graph=g,
        upstreams=[debate_stage],
        stage_label="Consensus",
        nodes={
            "ResearchReferee": ResearchReferee(
                PersonaConfig(
                    name="ResearchReferee",
                    system_prompt_path="research_referee.txt",
                    max_tokens=500,
                )
            )
        },
    )

    # Stage 5: Risk, execution, and oversight.
    traders = build_trader_personas()
    risk_stage = _fanout_stage(
        graph=g,
        upstreams=[consensus_stage],
        stage_label="Risk",
        nodes={"RiskManager": traders["RiskManager"]},
    )
    trader_stage = _fanout_stage(
        graph=g,
        upstreams=[risk_stage],
        stage_label="Trader",
        nodes={"Trader": traders["Trader"]},
    )
    oversight_stage = _fanout_stage(
        graph=g,
        upstreams=[trader_stage],
        stage_label="Oversight",
        nodes={"RiskJudge": traders["RiskJudge"]},
    )

    # Decision desk: convert oversight output into a canonical decision payload.
    g.add_node("FinalizeDecision", finalize_decision)
    g.add_edge(oversight_stage, "FinalizeDecision")

    g.add_node("Consolidate", consolidate_state)
    g.add_edge("FinalizeDecision", "Consolidate")

    g.add_edge("Consolidate", END)
    return g


async def run_langgraph_pipeline(ticker: str, as_of_date: str) -> Dict[str, Any]:
    """Run LangGraph workflow with visualization + per-step tracking."""
    print(f"🚀 Starting LangGraph analysis for {ticker} @ {as_of_date}")

    logger.info("🧠 Building LangGraph pipeline...")
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

    initial_state = GraphState(ticker=ticker, as_of_date=as_of_date).model_dump()
    logger.info("📥 Initial state prepared for %s @ %s", ticker, as_of_date)

    tracker = StepTracker(ticker, as_of_date)
    final_state: Dict[str, Any] | None = None

    async for event in app.astream_events(initial_state, version="v2"):
        name = event.get("name")
        ev_type = event.get("event")
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

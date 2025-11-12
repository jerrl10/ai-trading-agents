from __future__ import annotations

from typing import Any, Dict, Union

from tradingagents.langgraph.builder import Node, SimpleGraph

# Data mappers
from tradingagents.langgraph.personas.data_agents import (
    FundamentalsMapper,
    MacroMapper,
    MarketMapper,
    NewsMapper,
    PolicyMapper,
)

# Domain analysts
from tradingagents.langgraph.personas.domain_analysts import build_domain_analysts

# Research (bull/bear/referee)
from tradingagents.langgraph.personas.research_agents import (
    BearResearcher,
    BullResearcher,
    PersonaConfig,
    ResearchReferee,
)

# Execution & governance (risk manager → trader → judge)
from tradingagents.langgraph.personas.trader_agents import build_trader_personas
from tradingagents.langgraph.state import GraphState


# ----------------------------------------------------------------------
# Graph construction
# ----------------------------------------------------------------------
def build_professional_graph() -> SimpleGraph:
    """
    Professional-grade trading DAG:
      Mappers (parallel) → Analysts (parallel) → Bull & Bear → Referee → Risk → Trader → Judge
    """
    g = SimpleGraph()

    # --------------------------- ENTRY: Seed ---------------------------
    def seed(state: Union[Dict[str, Any], GraphState]) -> Dict[str, Any]:
        """
        Ensure GraphState schema and defaults are established for any incoming state.
        """
        # 🧩 Handle both dict and GraphState gracefully
        if isinstance(state, GraphState):
            gs = state
        else:
            gs = GraphState(**state)
        return gs.model_dump()

    n_seed = Node("SeedState", seed)
    g.add_node(n_seed, entry=True)

    # --------------------------- MAPPERS ---------------------------
    n_market = Node("MarketMapper", MarketMapper())
    n_funds = Node("FundamentalsMapper", FundamentalsMapper())
    n_news = Node("NewsMapper", NewsMapper())
    n_policy = Node("PolicyMapper", PolicyMapper())
    n_macro = Node("MacroMapper", MacroMapper())

    n_seed.connect(n_market, n_funds, n_news, n_policy, n_macro)

    # --------------------------- ANALYSTS ---------------------------
    analysts = build_domain_analysts()
    n_tech = Node("TechnicalAnalyst", analysts["technical"])
    n_val = Node("ValuationAnalyst", analysts["valuation"])
    n_evt = Node("EventAnalyst", analysts["event"])
    n_macr = Node("MacroAnalyst", analysts["macro"])
    n_flow = Node("FlowAnalyst", analysts["flow"])

    for mapper_node in (n_market, n_funds, n_news, n_policy, n_macro):
        mapper_node.connect(n_tech, n_val, n_evt, n_macr, n_flow)

    # --------------------------- RESEARCH ---------------------------
    bull = BullResearcher(
        PersonaConfig(
            name="BullResearcher",
            system_prompt_path="bull_researcher.txt",
            max_tokens=500,
        )
    )
    bear = BearResearcher(
        PersonaConfig(
            name="BearResearcher",
            system_prompt_path="bear_researcher.txt",
            max_tokens=500,
        )
    )
    ref = ResearchReferee(
        PersonaConfig(
            name="ResearchReferee",
            system_prompt_path="research_referee.txt",
            max_tokens=500,
        )
    )

    n_bull = Node("BullResearcher", bull)
    n_bear = Node("BearResearcher", bear)
    n_ref = Node("ResearchReferee", ref)

    # Research depends on analysts
    for analyst_node in (n_tech, n_val, n_evt, n_macr, n_flow):
        analyst_node.connect(n_bull, n_bear)

    # Both bull & bear → referee
    n_bull.connect(n_ref)
    n_bear.connect(n_ref)

    # --------------------------- EXECUTION ---------------------------
    traders = build_trader_personas()
    n_risk_mgr = Node("RiskManager", traders["RiskManager"])
    n_trader = Node("Trader", traders["Trader"])
    n_judge = Node("RiskJudge", traders["RiskJudge"])

    n_ref.connect(n_risk_mgr)
    n_risk_mgr.connect(n_trader)
    n_trader.connect(n_judge)

    return g


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------
async def run_professional_graph(ticker: str, as_of_date: str) -> Dict[str, Any]:
    """
    Run the professional trading graph and return the final enriched state.
    """
    # Initialize state safely
    state: Dict[str, Any] = GraphState(ticker=ticker, as_of_date=as_of_date).model_dump()

    g = build_professional_graph()
    final_state = await g.run(state)

    analyses = final_state.get("analyses", {})

    # Convenience: derive a summary decision
    if "RiskJudge" in analyses:
        rj = analyses["RiskJudge"]
        final_state["decision"] = {
            "ticker": ticker,
            "stance": rj.get("stance", "neutral"),
            "decision": rj.get("final_action", rj.get("decision", "hold")),
            "rationale": rj.get("summary") or rj.get("rationale", ""),
        }
    elif "Trader" in analyses:
        tr = analyses["Trader"]
        final_state["decision"] = {
            "ticker": ticker,
            "stance": tr.get("stance", "neutral"),
            "decision": tr.get("decision", "hold"),
            "rationale": tr.get("summary") or tr.get("rationale", ""),
        }

    return final_state
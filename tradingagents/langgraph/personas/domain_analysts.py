from __future__ import annotations

from typing import Any, Dict, List, Optional

from tradingagents.langgraph.personas.base_persona import BasePersona, PersonaConfig
from tradingagents.langgraph.state import GraphState

# ──────────────────────────────────────────────────────────────
# Utility to select top evidence snippets for prompting
# ──────────────────────────────────────────────────────────────


def _sample_sources(
    gs: GraphState, source_key: str, n: int = 3
) -> List[Dict[str, Any]]:
    """Return up to n readable snippets from gs.data_sources[source_key]."""
    items = gs.data_sources.get(source_key, [])[:n]
    return [f"- {src.get('title') or src.get('content','')[:150]}" for src in items]


# ──────────────────────────────────────────────────────────────
# Domain-specific analyst personas
# ──────────────────────────────────────────────────────────────


class TechnicalAnalyst(BasePersona):
    """
    Examines market price action & volatility patterns.
    Looks at indicators, trend direction, and momentum.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        _ = context  # Reserved for future use
        # Get full market data for technical analysis (not just 3 samples)
        market_data = gs.data_sources.get("market", [])

        # Format price history for technical analysis
        if not market_data:
            snippets = "No market data available."
        else:
            # Show all available data (up to 20 days) for trend/pattern analysis
            price_lines = []
            for src in market_data[:20]:
                meta = src.get("meta", {})
                date = meta.get("date", "N/A")
                close = meta.get("close", 0)
                change = meta.get("change", 0)
                volume = meta.get("volume", 0)
                price_lines.append(
                    f"  {date[:10]}: ${close:.2f} ({change:+.1%}), Vol: {volume:,}"
                )

            # Calculate price statistics for trend identification
            if len(market_data) >= 5:
                prices = [src.get("meta", {}).get("close", 0) for src in market_data[:20]]
                changes = [src.get("meta", {}).get("change", 0) for src in market_data[:20]]

                recent_price = prices[0] if prices else 0
                oldest_price = prices[-1] if prices else 0
                total_change = ((recent_price - oldest_price) / oldest_price) if oldest_price else 0
                avg_daily_change = sum(changes) / len(changes) if changes else 0

                snippets = "\n".join(price_lines)
                snippets += f"\n\n  Price Statistics ({len(prices)} days):\n"
                snippets += f"  - Total change: {total_change:+.1%}\n"
                snippets += f"  - Average daily change: {avg_daily_change:+.2%}\n"
                snippets += f"  - Current price: ${recent_price:.2f}\n"
                snippets += f"  - Period range: ${min(prices):.2f} - ${max(prices):.2f}\n"
            else:
                snippets = "\n".join(price_lines)

        horizon_context = {
            "short": "Focus on near-term price action (days to weeks): momentum, volatility, support/resistance.",
            "medium": "Focus on intermediate trends (1-6 months): sustained momentum, trend strength, pattern breakouts.",
            "long": "Focus on long-term positioning (1+ years): major trend direction, structural levels, cyclical patterns."
        }.get(gs.time_horizon, "")

        return (
            f"You are a seasoned Technical Analyst evaluating {gs.ticker}.\n"
            f"Today: {gs.as_of_date}.\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n"
            f"Recent market data:\n{snippets}\n\n"
            "Analyze the price action and identify:\n"
            "- Trend direction (uptrend, downtrend, or sideways)\n"
            "- Momentum strength and consistency\n"
            "- Key support/resistance levels from recent price action\n"
            "- Volatility patterns and significant moves\n\n"
            "Return your technical stance with confidence. Support each claim with evidence_ref "
            "from market data."
        )


class FundamentalAnalyst(BasePersona):
    """
    Evaluates fundamental valuation, growth metrics, and financial health.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        _ = context  # Reserved for future use
        snippets = "\n".join(_sample_sources(gs, "fundamentals"))
        horizon_context = {
            "short": "Focus on near-term earnings catalysts, guidance, and valuation gaps.",
            "medium": "Focus on sustainable growth, margin trends, and competitive positioning over 1-6 months.",
            "long": "Focus on structural moats, long-term growth trajectory, and strategic position for 1+ years."
        }.get(gs.time_horizon, "")

        return (
            f"You are a Fundamental Analyst assessing {gs.ticker}.\n"
            f"As of {gs.as_of_date}, recent fundamental ratios:\n{snippets}\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n\n"
            "Determine if the company appears undervalued or overvalued relative to history "
            "and peers. Provide stance, key metrics, and confidence."
        )


class SentimentAnalyst(BasePersona):
    """
    Analyzes news & policy events for sentiment impact across different time horizons.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        _ = context  # Reserved for future use
        news = "\n".join(_sample_sources(gs, "news"))
        horizon_context = {
            "short": "Focus on immediate sentiment shocks, headline reactions, and near-term narrative shifts.",
            "medium": "Focus on evolving themes, sector trends, and sustained narrative changes over 1-6 months.",
            "long": "Focus on structural regulatory changes, secular trends, and long-term sentiment drivers."
        }.get(gs.time_horizon, "")

        return (
            f"You are a Sentiment Analyst covering {gs.ticker}.\n"
            f"Relevant company, sector, and policy news:\n{news}\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n\n"
            "Summarize how these events might affect investor sentiment and price direction. "
            "Return structured JSON with stance, reasons, and evidence_refs."
        )


class MacroAnalyst(BasePersona):
    """
    Reviews macroeconomic indicators and global context.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        _ = context  # Reserved for future use
        snippets = "\n".join(_sample_sources(gs, "macro"))
        horizon_context = {
            "short": "Focus on immediate rate decisions, data surprises, and near-term policy shifts.",
            "medium": "Focus on evolving monetary/fiscal policy, growth trajectory, and inflation trends over 1-6 months.",
            "long": "Focus on structural economic cycles, regime changes, and long-term policy direction."
        }.get(gs.time_horizon, "")

        return (
            f"You are a Macro Analyst.\n"
            f"Latest macro context:\n{snippets}\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n\n"
            f"Explain how macro trends could influence {gs.ticker}'s sector or index exposure. "
            "State whether the macro environment is supportive, neutral, or hostile for the stock."
        )


class FlowAnalyst(BasePersona):
    """
    Observes positioning, flow, and market microstructure.
    """

    def render_user_prompt(
        self, gs: GraphState, context: Optional[Dict[str, Any]] = None
    ) -> str:
        _ = context  # Reserved for future use
        # Get more market data for flow analysis (not just 3 samples)
        market_data = gs.data_sources.get("market", [])

        # Format volume and price action for flow analysis
        if not market_data:
            snippets = "No market data available."
        else:
            # Show last 15 days (or all available) with volume emphasis
            flow_lines = []
            for src in market_data[:15]:
                meta = src.get("meta", {})
                date = meta.get("date", "N/A")
                close = meta.get("close", 0)
                change = meta.get("change", 0)
                volume = meta.get("volume", 0)
                flow_lines.append(
                    f"  {date[:10]}: ${close:.2f} ({change:+.1%}), "
                    f"Volume: {volume:,}"
                )

            # Calculate volume statistics if we have enough data
            if len(market_data) >= 5:
                volumes = [src.get("meta", {}).get("volume", 0) for src in market_data[:15]]
                avg_vol = sum(volumes) / len(volumes)
                recent_vol = volumes[0] if volumes else 0
                vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0

                snippets = "\n".join(flow_lines)
                snippets += f"\n\n  Volume Statistics:\n"
                snippets += f"  - Recent volume: {recent_vol:,}\n"
                snippets += f"  - Average volume: {avg_vol:,.0f}\n"
                snippets += f"  - Volume ratio: {vol_ratio:.2f}x average\n"
            else:
                snippets = "\n".join(flow_lines)

        horizon_context = {
            "short": "Focus on intraday/weekly flows, liquidity, and positioning imbalances.",
            "medium": "Focus on institutional flow trends, sentiment extremes, and positioning over 1-6 months.",
            "long": "Focus on structural changes in ownership, long-term capital allocation trends."
        }.get(gs.time_horizon, "")

        return (
            f"You are a Flow & Positioning Analyst for {gs.ticker}.\n"
            f"Recent market flow data:\n{snippets}\n"
            f"Time Horizon: {gs.time_horizon.upper()} - {horizon_context}\n\n"
            "Analyze volume patterns, price-volume relationships, and potential positioning:\n"
            "- Are volumes elevated/declining vs historical average?\n"
            "- Do volume spikes correspond with price moves (capitulation/accumulation)?\n"
            "- Are there signs of crowded positioning or squeeze risk?\n\n"
            "Estimate whether current positioning is crowded long, neutral, or short. "
            "Support claims with reasoning and confidence."
        )


# ──────────────────────────────────────────────────────────────
# Factory for easy graph construction
# ──────────────────────────────────────────────────────────────


def build_domain_analysts() -> Dict[str, BasePersona]:
    """
    Create all domain analysts with consistent config.
    Returns analysts keyed by their role names for easy graph construction.
    """
    return {
        "technical": TechnicalAnalyst(
            PersonaConfig(
                name="TechnicalAnalyst",
                system_prompt_path="technical_analyst.txt",
                temperature=0.2,
                max_tokens=400,
            )
        ),
        "fundamental": FundamentalAnalyst(
            PersonaConfig(
                name="FundamentalAnalyst",
                system_prompt_path="fundamental_analyst.txt",
                temperature=0.2,
                max_tokens=400,
            )
        ),
        "sentiment": SentimentAnalyst(
            PersonaConfig(
                name="SentimentAnalyst",
                system_prompt_path="sentiment_analyst.txt",
                temperature=0.2,
                max_tokens=500,
            )
        ),
        "macro": MacroAnalyst(
            PersonaConfig(
                name="MacroAnalyst",
                system_prompt_path="macro_analyst.txt",
                temperature=0.2,
                max_tokens=400,
            )
        ),
        "flow": FlowAnalyst(
            PersonaConfig(
                name="FlowAnalyst",
                system_prompt_path="flow_analyst.txt",
                temperature=0.2,
                max_tokens=400,
            )
        ),
    }

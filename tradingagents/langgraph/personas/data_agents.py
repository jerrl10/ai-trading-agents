from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Union

from pydantic import BaseModel, Field

from tradingagents.config.defaults import DEFAULT_CONFIG
from tradingagents.config.logging_config import get_logger
from tradingagents.data.adapters.fundamentals_av import fetch_fundamentals
from tradingagents.data.adapters.macro_av import fetch_macro_indicators
from tradingagents.data.adapters.news_general_av import fetch_news_general
from tradingagents.data.adapters.news_policy_us import fetch_policy_news_us
from tradingagents.data.adapters.prices_yf import fetch_prices
from tradingagents.langgraph.state import GraphState

logger = get_logger(__name__)

# ==========================================================
# 1) Shared normalized evidence structure
# ==========================================================


class SourceObject(BaseModel):
    """
    A single normalized evidence record from a data source.
    """

    id: str  # e.g. "news:3" or "ratio:pe_ttm"
    type: str  # market | fundamentals | news | policy | macro
    title: str | None = None
    content: str | None = None
    url: str | None = None
    published_at: str | None = None
    meta: Dict[str, Any] = Field(default_factory=dict)


# ==========================================================
# 2) Base mapper — returns a UNIQUE key per node
# ==========================================================


class BaseMapper:
    """
    IMPORTANT: Each mapper returns ONLY a unique top-level key
    (e.g., 'm__market', 'm__fundamentals', …). It MUST NOT return
    the whole state (no ticker/as_of_date), otherwise parallel nodes
    will collide on LastValue channels in LangGraph 1.0.x.
    """

    type: str = "generic"  # subclass overrides

    def __call__(self, state: Union[Dict[str, Any], GraphState]) -> Dict[str, Any]:
        gs = _ensure_graph_state(state)
        d = date.fromisoformat(gs.as_of_date)

        logger.info("🔹 %s mapper started for %s", self.type.capitalize(), gs.ticker)
        sources = self.load(gs, d)  # -> List[SourceObject]
        logger.info(
            "🔸 %s mapper finished (%d items)",
            self.type.capitalize(),
            len(sources),
        )

        # ✅ Return a single, unique key. No collisions.
        # Downstream, a consolidator will merge these into data_sources.
        return {f"m__{self.type}": [s.model_dump() for s in sources]}

    def load(self, gs: GraphState, d: date) -> List[SourceObject]:
        raise NotImplementedError


# ==========================================================
# 3) Concrete mappers
# ==========================================================


class MarketMapper(BaseMapper):
    type = "market"

    def load(self, gs: GraphState, d: date) -> List[SourceObject]:
        # Use configured lookback days (default 120) for proper historical context
        lookback_days = DEFAULT_CONFIG["research"]["lookback_days"]
        prices = fetch_prices(gs.ticker, d, lookback_days=lookback_days)

        # Return all price data (not just 10) for technical analysis
        # Analysts will see the full history for identifying trends, support/resistance
        return [
            SourceObject(
                id=f"market:{i}",
                type=self.type,
                title=f"{gs.ticker} price on {p.date}",
                content=f"{p.date}: close=${p.close:.2f}, change={p.change:.2%}, volume={p.volume or 0:,}",
                meta=p.model_dump(),
            )
            for i, p in enumerate(prices.series)
        ]


class FundamentalsMapper(BaseMapper):
    type = "fundamentals"

    def load(self, gs: GraphState, d: date) -> List[SourceObject]:
        fundamentals = fetch_fundamentals(gs.ticker, d)
        items: List[SourceObject] = []

        # Extract ratios (nested dict)
        for key, value in fundamentals.ratios.items():
            items.append(
                SourceObject(
                    id=f"ratio:{key}",
                    type=self.type,
                    title=f"{key}={value}",
                    content=f"{key}={value}",
                    meta={"value": value, "category": "ratio"},
                )
            )

        # Extract trends (nested dict)
        for key, value in fundamentals.trend.items():
            items.append(
                SourceObject(
                    id=f"trend:{key}",
                    type=self.type,
                    title=f"{key}={value}",
                    content=f"{key}={value}",
                    meta={"value": value, "category": "trend"},
                )
            )

        return items


class NewsMapper(BaseMapper):
    type = "news"

    def load(self, gs: GraphState, d: date) -> List[SourceObject]:
        news_items = fetch_news_general(gs.ticker, d)
        out: List[SourceObject] = []
        for i, n in enumerate(news_items[:10]):
            # NewsItem has: headline, summary, published_at, source, url, sentiment
            out.append(
                SourceObject(
                    id=f"news:{i}",
                    type=self.type,
                    title=n.headline,
                    content=n.summary,
                    url=n.url,
                    published_at=str(n.published_at) if n.published_at else None,
                    meta=n.model_dump(),
                )
            )
        return out


class PolicyMapper(BaseMapper):
    type = "policy"

    def load(self, gs: GraphState, d: date) -> List[SourceObject]:
        news_items = fetch_policy_news_us(d)
        out: List[SourceObject] = []
        for i, n in enumerate(news_items[:10]):
            # NewsItem has: headline, summary, published_at, source, url, sentiment
            out.append(
                SourceObject(
                    id=f"policy:{i}",
                    type=self.type,
                    title=n.headline,
                    content=n.summary,
                    url=n.url,
                    published_at=str(n.published_at) if n.published_at else None,
                    meta=n.model_dump(),
                )
            )
        return out


class MacroMapper(BaseMapper):
    type = "macro"

    def load(self, gs: GraphState, d: date) -> List[SourceObject]:
        """
        Fetch real macro economic indicators from Alpha Vantage.
        Returns key indicators like CPI, Federal Funds Rate, Unemployment, GDP, etc.
        """
        indicators = fetch_macro_indicators(d)
        out: List[SourceObject] = []

        for ind in indicators:
            # Format the indicator for display
            title = (
                f"{ind.indicator}: {ind.value}{ind.unit if ind.unit != 'index' else ''}"
            )
            content = f"{ind.indicator} = {ind.value} {ind.unit} (as of {ind.date}, {ind.interval})"

            out.append(
                SourceObject(
                    id=f"macro:{ind.indicator.lower()}",
                    type=self.type,
                    title=title,
                    content=content,
                    published_at=ind.date,
                    meta={
                        "indicator": ind.indicator,
                        "value": ind.value,
                        "unit": ind.unit,
                        "interval": ind.interval,
                    },
                )
            )

        return out


# ==========================================================
# 4) Helpers
# ==========================================================


def _ensure_graph_state(state: Union[GraphState, Dict[str, Any]]) -> GraphState:
    return state if isinstance(state, GraphState) else GraphState(**state)


def run_all_mappers(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sequential fallback runner (handy for tests). Returns a flat dict of node outputs:
      {
        "m__market": [...],
        "m__fundamentals": [...],
        ...
      }
    """
    gs = _ensure_graph_state(state)
    outputs: Dict[str, Any] = {}
    for mapper in [
        MarketMapper(),
        FundamentalsMapper(),
        NewsMapper(),
        PolicyMapper(),
        MacroMapper(),
    ]:
        outputs.update(mapper(gs.model_dump()))
    return outputs

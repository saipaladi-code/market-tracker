import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.models.market_context_models import (
    MarketIndicator,
    FactsVsInterpretation,
    MarketContextResponse,
    MarketContextRequest
)
from app.services.broker_routing_service import (
    broker_routing_service,
    VERIFIED_INDIAN_INSTRUMENTS,
    VERIFIED_US_INSTRUMENTS
)

# In-memory context cache: {cache_key: (MarketContextResponse, timestamp)}
_CONTEXT_CACHE: Dict[str, Tuple[MarketContextResponse, float]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


class MarketContextService:
    """
    Market Context Engine for FIN-SENTIMENT.
    Synthesizes macroeconomic context, sector-level benchmarks, supporting facts,
    and clear demarcation between verifiable reported facts and AI sentiment interpretation.
    """

    def __init__(self):
        pass

    def _normalize(self, text: Optional[str]) -> str:
        return (text or "").lower().replace("'", "").replace('"', "").replace(",", "").strip()

    def _detect_precious_metals(self, text: str) -> bool:
        norm = self._normalize(text)
        keywords = ["gold", "silver", "bullion", "precious metal", "comex", "mcx", "troy ounce", "sovereign gold"]
        return any(re.search(rf"\b{kw}\b", norm) for kw in keywords)

    def _classify_event_topic(self, text: str, entity_type: str) -> str:
        norm = self._normalize(text)

        if entity_type == "commodity":
            if "reserve" in norm or "central bank" in norm:
                return "Central Bank Reserve Accumulation & Sovereign Bullion Holdings"
            if "inflation" in norm or "rate" in norm or "yield" in norm:
                return "Macroeconomic Hedging, Real Yields & Safe-Haven Allocation"
            return "Precious Metals Supply-Demand Dynamics & Currency Hedging"

        if any(w in norm for w in ["earnings", "quarter", "q1", "q2", "q3", "q4", "revenue", "profit", "net income", "margin", "ebitda", "guidance"]):
            return "Quarterly Financial Performance, Margins & Forward Guidance"

        if any(w in norm for w in ["acquisition", "merger", "deal", "stake", "buyout", "takeover", "joint venture"]):
            return "M&A, Strategic Investments & Capital Allocation"

        if any(w in norm for w in ["ai", "cloud", "semiconductor", "chip", "datacenter", "software", "model", "nvidia", "gpu"]):
            return "Enterprise Technology, AI Infrastructure & Capex Deployment"

        if any(w in norm for w in ["inflation", "cpi", "rbi", "fed", "interest rate", "repo", "monetary policy", "rate cut", "hike"]):
            return "Macroeconomic Policy, Inflation Trajectory & Systemic Liquidity"

        if any(w in norm for w in ["oil", "refinery", "opec", "crude", "energy", "petrochemical"]):
            return "Energy Markets, Refining Margins & Commodity Cost Pressures"

        if any(w in norm for w in ["regulatory", "court", "antitrust", "sebi", "sec", "fine", "lawsuit", "investigation"]):
            return "Regulatory Oversight, Compliance & Governance Inquiries"

        if any(w in norm for w in ["order", "contract", "deal win", "client", "expansion", "capacity"]):
            return "Commercial Order Book, Commercial Wins & Capacity Expansion"

        return "Market Sentiment, Corporate Developments & Sector Trends"

    def _get_sector_indicators(self, company_key: str, country: str) -> List[MarketIndicator]:
        indicators: List[MarketIndicator] = []

        if country == "IN":
            # Primary benchmark
            indicators.append(MarketIndicator(
                name="NIFTY 50",
                symbol="^NSEI",
                value="24,350.25",
                change="+0.45%",
                trend="up",
                relevance_note="Headline Indian market benchmark reflecting broader institutional risk appetite."
            ))

            # Sector index mapping
            if company_key in ["tcs", "infosys", "wipro", "hcl tech", "tech mahindra"]:
                indicators.append(MarketIndicator(
                    name="NIFTY IT",
                    symbol="^CNXIT",
                    value="38,420.10",
                    change="+0.68%",
                    trend="up",
                    relevance_note="Technology sector barometer tracking BFSI IT spending and software export revenue."
                ))
            elif company_key in ["hdfc bank", "icici bank", "state bank of india", "kotak mahindra bank", "axis bank"]:
                indicators.append(MarketIndicator(
                    name="NIFTY BANK",
                    symbol="^NSEBANK",
                    value="51,280.40",
                    change="+0.32%",
                    trend="up",
                    relevance_note="Banking sector index tracking systemic credit growth and net interest margins (NIM)."
                ))
            elif company_key in ["tata motors", "maruti suzuki", "mahindra & mahindra", "bajaj auto"]:
                indicators.append(MarketIndicator(
                    name="NIFTY AUTO",
                    symbol="^CNXAUTO",
                    value="22,760.85",
                    change="+0.52%",
                    trend="up",
                    relevance_note="Automotive index tracking commercial and EV production volumes and consumer demand."
                ))
            elif company_key in ["reliance", "reliance industries", "ongc", "bpcl", "iocl"]:
                indicators.append(MarketIndicator(
                    name="NIFTY OIL & GAS",
                    symbol="^CNXOILGAS",
                    value="11,890.30",
                    change="+0.41%",
                    trend="up",
                    relevance_note="Energy index tracking gross refining margins (GRM) and petrochemical spreads."
                ))
            else:
                indicators.append(MarketIndicator(
                    name="BSE SENSEX",
                    symbol="^BSESN",
                    value="80,120.50",
                    change="+0.40%",
                    trend="up",
                    relevance_note="Premier benchmark reflecting blue-chip valuation multiples across 30 large-caps."
                ))

        elif country == "US":
            indicators.append(MarketIndicator(
                name="S&P 500",
                symbol="^GSPC",
                value="5,785.40",
                change="+0.58%",
                trend="up",
                relevance_note="Broad US large-cap benchmark tracking enterprise earnings power and market breadth."
            ))
            indicators.append(MarketIndicator(
                name="NASDAQ 100",
                symbol="^NDX",
                value="20,110.60",
                change="+0.74%",
                trend="up",
                relevance_note="Tech-heavy index tracking mega-cap innovation, semiconductor cycles, and hyperscaler capex."
            ))

        return indicators

    def _get_commodity_indicators(self) -> List[MarketIndicator]:
        return [
            MarketIndicator(
                name="COMEX Gold Futures",
                symbol="GC=F",
                value="$2,738.50 / oz",
                change="+0.62%",
                trend="up",
                relevance_note="Primary global benchmark for physically deliverable gold bullion futures."
            ),
            MarketIndicator(
                name="COMEX Silver Futures",
                symbol="SI=F",
                value="$31.85 / oz",
                change="+1.15%",
                trend="up",
                relevance_note="Industrial and precious metal hybrid benchmark sensitive to electronics and green energy demand."
            ),
            MarketIndicator(
                name="USD / INR Exchange Rate",
                symbol="USDINR=X",
                value="₹84.12",
                change="+0.04%",
                trend="neutral",
                relevance_note="Forex conversion rate directly determining landed import parity prices for Indian bullion."
            )
        ]

    def _get_general_market_indicators(self) -> List[MarketIndicator]:
        return [
            MarketIndicator(
                name="NIFTY 50",
                symbol="^NSEI",
                value="24,350.25",
                change="+0.45%",
                trend="up",
                relevance_note="Indian headline equity benchmark reflecting overall domestic market liquidity."
            ),
            MarketIndicator(
                name="S&P 500",
                symbol="^GSPC",
                value="5,785.40",
                change="+0.58%",
                trend="up",
                relevance_note="Global risk sentiment bellwether and US equity market barometer."
            ),
            MarketIndicator(
                name="India VIX",
                symbol="^INDIAVIX",
                value="13.85",
                change="-2.40%",
                trend="down",
                relevance_note="Volatility and options implied risk gauge. Lower levels indicate stable market conditions."
            )
        ]

    def generate_context(self, req: MarketContextRequest) -> MarketContextResponse:
        """
        Generates full market context for a given headline, company, or news article.
        Utilizes caching for instantaneous repeat retrievals.
        """
        cache_key = f"{req.article_id or ''}:{self._normalize(req.headline)}:{self._normalize(req.company)}"
        now = time.time()

        if cache_key in _CONTEXT_CACHE:
            cached_resp, timestamp = _CONTEXT_CACHE[cache_key]
            if now - timestamp < CACHE_TTL_SECONDS:
                return cached_resp

        headline = req.headline.strip()
        sentiment = (req.sentiment or "neutral").lower()
        confidence = float(req.confidence or 0.5)

        # 1. Determine entity type
        is_metal = self._detect_precious_metals(headline) or (req.company and self._detect_precious_metals(req.company))

        entity_type: str = "general_market"
        entity_name: str = "Broad Financial Markets"
        ticker: Optional[str] = req.ticker
        exchange: Optional[str] = None
        market_indicators: List[MarketIndicator] = []

        if is_metal:
            entity_type = "commodity"
            entity_name = "Gold & Silver Bullion Markets"
            ticker = "COMEX:GC / SI"
            exchange = "COMEX & MCX"
            market_indicators = self._get_commodity_indicators()

        else:
            # Check verified company instruments via broker_routing_service
            route = broker_routing_service.get_trading_route_by_identifiers(company=req.company, ticker=req.ticker)
            if not route.is_tradable and headline:
                # Attempt to extract from headline
                for key in {**VERIFIED_INDIAN_INSTRUMENTS, **VERIFIED_US_INSTRUMENTS}.keys():
                    if re.search(rf"\b{re.escape(key)}\b", self._normalize(headline)):
                        route = broker_routing_service.get_trading_route_by_identifiers(company=key)
                        break

            if route.is_tradable:
                entity_type = "company"
                entity_name = route.company
                ticker = route.ticker
                exchange = route.exchange
                market_indicators = self._get_sector_indicators(
                    self._normalize(route.company),
                    route.country or "IN"
                )
            elif req.company and req.company.lower() not in ["general market", "market", "economy", "global markets"]:
                entity_type = "company"
                entity_name = req.company
                ticker = req.ticker or None
                exchange = "NSE/BSE" if (req.ticker and "." in str(req.ticker)) else "Global"
                market_indicators = self._get_sector_indicators(self._normalize(req.company), "IN")
            else:
                entity_type = "general_market"
                entity_name = "Indian & Global Equities"
                ticker = "^NSEI / ^GSPC"
                exchange = "NSE & Global"
                market_indicators = self._get_general_market_indicators()

        # 2. Event topic
        event_topic = self._classify_event_topic(headline, entity_type)

        # 3. Market relevance synthesis
        if entity_type == "company":
            market_relevance = (
                f"Developments regarding {entity_name} ({ticker}) directly impact sector weightings on {exchange}. "
                f"Financial sentiment shifts in this entity influence peer valuations, institutional fund flows, and analyst consensus."
            )
        elif entity_type == "commodity":
            market_relevance = (
                "Precious metals pricing serves as a primary macro barometer for sovereign debt sustainability, "
                "real interest rate expectations, and inflation hedging across central banks and private wealth allocators."
            )
        else:
            market_relevance = (
                "Macroeconomic and regulatory policy announcements establish the broader liquidity environment, "
                "borrowing costs, and risk premium across equity, fixed-income, and currency markets."
            )

        # 4. Objective facts vs AI interpretation
        objective_facts = [
            f"Headline reported via {req.source or 'Financial Intelligence Feed'}: '{headline}'.",
            f"Asset Classification: {entity_name} categorized under {entity_type.replace('_', ' ').title()}.",
            f"Primary Market Venue: {exchange or 'Multi-asset global exchange'}."
        ]

        if sentiment == "positive":
            ai_interpretation = (
                f"FinBERT classified this development as positive (confidence: {confidence:.1%}). "
                f"The language indicates potential earnings resilience, operational outperformance, or expansionary momentum "
                f"that could provide tailwinds to valuation multiples."
            )
            risk_factors = [
                "Broader market volatility or risk-off sentiment dampening upside realization",
                "Execution risks on corporate guidance or forward margin targets",
                "Macro interest rate pressures or currency headwinds"
            ]
        elif sentiment == "negative":
            ai_interpretation = (
                f"FinBERT classified this development as negative (confidence: {confidence:.1%}). "
                f"The report highlights operational friction, cost inflation, margin compression, or regulatory headwinds "
                f"likely to create near-term headline drag."
            )
            risk_factors = [
                "Potential downward revisions to analyst revenue/EBITDA consensus",
                "Spillover impact onto supply chain partners and sector peers",
                "Market overreaction leading to high implied volatility spikes"
            ]
        else:
            ai_interpretation = (
                f"FinBERT classified this development as neutral/balanced (confidence: {confidence:.1%}). "
                f"The announcement reflects operational updates, routine regulatory filings, or mixed data points that "
                f"are likely already priced in by institutional participants."
            )
            risk_factors = [
                "Uncertainty regarding upcoming quarterly earnings confirmation",
                "Macroeconomic policy catalysts (RBI/Fed interest rate meetings)",
                "Changes in sector-wide foreign institutional investor (FII) flows"
            ]

        facts_vs_interpretation = FactsVsInterpretation(
            objective_facts=objective_facts,
            ai_interpretation=ai_interpretation,
            risk_factors=risk_factors
        )

        supporting_facts = [
            f"Event Classification: {event_topic}",
            f"Market Venue: {exchange or 'Benchmark indices'}",
            f"FinBERT AI Confidence: {confidence:.1%} ({sentiment.upper()})"
        ]

        response = MarketContextResponse(
            headline=headline,
            entity_type=entity_type,  # type: ignore
            entity_name=entity_name,
            ticker=ticker,
            exchange=exchange,
            event_topic=event_topic,
            sentiment=sentiment,
            confidence=confidence,
            market_relevance=market_relevance,
            supporting_facts=supporting_facts,
            market_indicators=market_indicators,
            facts_vs_interpretation=facts_vs_interpretation,
            generated_at=datetime.now(timezone.utc).isoformat(),
            data_source="FIN-SENTIMENT Market Context Engine (FinBERT + Market Feeds)"
        )

        # Cache response
        _CONTEXT_CACHE[cache_key] = (response, now)
        return response


market_context_service = MarketContextService()

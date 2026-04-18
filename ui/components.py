"""
Reusable Streamlit UI components.
"""

import streamlit as st
import pandas as pd


def render_company_header(info: dict, google_data: dict = None):
    """Render the company header with name, sector, price, and key metrics."""
    name = info.get("name", "Unknown")
    sector = info.get("sector", "N/A")
    industry = info.get("industry", "N/A")
    current_price = info.get("current_price")
    prev_close = info.get("previous_close")
    currency = info.get("currency", "INR")

    st.markdown(f'<div class="company-header">', unsafe_allow_html=True)
    st.markdown(f"## {name}")
    st.markdown(f'<span class="subtitle">{sector} | {industry}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Price row
    cols = st.columns([2, 1, 1, 1, 1])
    if current_price:
        change = (current_price - prev_close) if prev_close else 0
        change_pct = (change / prev_close * 100) if prev_close else 0
        color = "green" if change >= 0 else "red"
        arrow = "+" if change >= 0 else ""
        cols[0].metric(
            "Current Price",
            f"{currency} {current_price:,.2f}",
            f"{arrow}{change:,.2f} ({arrow}{change_pct:.2f}%)"
        )

    market_cap = info.get("market_cap")
    if market_cap:
        if market_cap >= 1e12:
            cap_str = f"{currency} {market_cap/1e12:.2f}T"
        elif market_cap >= 1e9:
            cap_str = f"{currency} {market_cap/1e9:.2f}B"
        elif market_cap >= 1e7:
            cap_str = f"{currency} {market_cap/1e7:.2f}Cr"
        else:
            cap_str = f"{currency} {market_cap:,.0f}"
        cols[1].metric("Market Cap", cap_str)

    hi52 = info.get("fifty_two_week_high")
    lo52 = info.get("fifty_two_week_low")
    if hi52:
        cols[2].metric("52W High", f"{currency} {hi52:,.2f}")
    if lo52:
        cols[3].metric("52W Low", f"{currency} {lo52:,.2f}")

    pe = info.get("trailing_pe")
    if pe:
        cols[4].metric("P/E Ratio", f"{pe:.2f}")


def render_metric_card(metric):
    """Render a single metric score as a styled card."""
    if metric.label == "N/A":
        css_class = "neutral"
    elif metric.score >= 1:
        css_class = "bullish"
    elif metric.score <= -1:
        css_class = "bearish"
    else:
        css_class = "neutral"

    score_color = "green" if metric.score > 0 else ("red" if metric.score < 0 else "amber")
    value_display = f"{metric.value:.2f}" if isinstance(metric.value, (int, float)) else str(metric.value or "N/A")

    html = f"""
    <div class="metric-card {css_class}">
        <div class="metric-name">{metric.name}</div>
        <div class="metric-value">{value_display}
            <span class="score-badge {score_color}">{metric.label} ({metric.score:+d})</span>
        </div>
        <div class="metric-explanation">{metric.explanation}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_verdict_banner(verdict):
    """Render the main verdict recommendation banner."""
    rec = verdict.recommendation
    css_class = rec.lower().replace(" ", "-")

    html = f"""
    <div class="verdict-banner {css_class}">
        <h1>{rec}</h1>
        <div class="confidence">Confidence: {verdict.confidence:.0f}% | Composite Score: {verdict.composite_score:.0f}/100</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_advanced_levels_verdict_banner(al_result):
    """Render the Advanced Levels standalone verdict banner."""
    verdict_text = getattr(al_result, "verdict", "Neutral")
    css_class = verdict_text.lower().replace(" ", "-")
    score = getattr(al_result, "normalized_score", 50)
    summary = getattr(al_result, "summary", "")

    html = f"""
    <div class="al-verdict-banner {css_class}">
        <h2>{verdict_text}</h2>
        <div class="al-score">Advanced Levels Score: {score:.0f}/100</div>
        <div class="al-summary">{summary}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_advanced_levels_table(stock_levels, current_price):
    """Render the multi-timeframe MA levels as styled cards."""
    if not stock_levels:
        st.info("No MA levels available.")
        return

    cols = st.columns(min(len(stock_levels), 6))
    for i, level in enumerate(stock_levels[:6]):
        tf = getattr(level, "timeframe", "?")
        ma_val = getattr(level, "ma_value", 0)
        group = getattr(level, "group", "L1").lower()
        position = getattr(level, "position", "near")
        dist = getattr(level, "distance_pct", 0) * 100

        pos_arrow = {"support": "&#9650; Support", "resistance": "&#9660; Resistance", "near": "&#9644; Near"}.get(position, "?")

        html = f"""
        <div class="al-level-card">
            <div class="al-tf">{tf}</div>
            <div class="al-value">&#8377;{ma_val:,.2f}</div>
            <div><span class="al-group {group}">{group.upper()}</span></div>
            <div class="al-pos {position}">{pos_arrow} ({dist:.1f}%)</div>
        </div>
        """
        cols[i % len(cols)].markdown(html, unsafe_allow_html=True)


def render_index_context_table(index_levels):
    """Render reference index MA context as styled info."""
    if not index_levels:
        st.info("No index data available.")
        return

    for idx in index_levels:
        name = getattr(idx, "name", "Unknown")
        fetched = getattr(idx, "fetched", False)
        if not fetched:
            st.caption(f"{name}: Data unavailable")
            continue

        ma_val = getattr(idx, "ma_value", 0)
        cur_price = getattr(idx, "current_price", 0)
        position = getattr(idx, "position", "")
        dist = getattr(idx, "distance_pct", 0) * 100

        if position == "above":
            color = "#00C853"
            icon = "&#9650;"
        elif position == "below":
            color = "#FF1744"
            icon = "&#9660;"
        else:
            color = "#FFC107"
            icon = "&#9644;"

        st.markdown(
            f'<div style="display:flex; justify-content:space-between; padding:6px 0; '
            f'border-bottom:1px solid #333; font-size:0.9rem;">'
            f'<span><strong>{name}</strong></span>'
            f'<span>144-MA: &#8377;{ma_val:,.2f}</span>'
            f'<span>Price: &#8377;{cur_price:,.2f}</span>'
            f'<span style="color:{color};">{icon} {position.title()} ({dist:.1f}%)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_elliott_verdict_banner(ew_verdict):
    """Render the Elliott Wave standalone verdict banner."""
    rec = getattr(ew_verdict, "recommendation", "No Signal")
    css_class = rec.lower().replace(" ", "-")
    headline = getattr(ew_verdict, "headline", "")
    rationale = getattr(ew_verdict, "rationale", "")
    confidence = getattr(ew_verdict, "confidence", 0)
    conf_label = getattr(ew_verdict, "confidence_label", "N/A")

    html = f"""
    <div class="ew-verdict-banner {css_class}">
        <h2>{rec}</h2>
        <div class="ew-headline">{headline}</div>
        <div class="ew-confidence">Wave Confidence: {confidence:.0f}% ({conf_label})</div>
        <div class="ew-rationale">{rationale}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_target_cards(verdict, current_price: float):
    """Render entry, target, and stop-loss price cards."""
    cols = st.columns(4)

    cols[0].markdown(f"""
    <div class="target-card">
        <div class="label">Current Price</div>
        <div class="price">₹{current_price:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    cols[1].markdown(f"""
    <div class="target-card">
        <div class="label">Entry Price</div>
        <div class="price green">₹{verdict.entry_price:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    cols[2].markdown(f"""
    <div class="target-card">
        <div class="label">Target Price</div>
        <div class="price green">₹{verdict.target_price:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    cols[3].markdown(f"""
    <div class="target-card">
        <div class="label">Stop Loss</div>
        <div class="price red">₹{verdict.stop_loss:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)


def render_position_card(verdict):
    """Render position P&L and advice if user holds a position."""
    if not verdict.position_advice:
        return

    pnl_color = "green" if verdict.pnl_pct >= 0 else "red"
    arrow = "+" if verdict.pnl_pct >= 0 else ""

    st.markdown(f"""
    <div class="position-card">
        <h4>Your Position</h4>
        <p>P&L: <span style="color: {'#00C853' if verdict.pnl_pct >= 0 else '#FF1744'}; font-weight: 700;">
            {arrow}{verdict.pnl_pct:.2f}% ({arrow}₹{verdict.pnl_value:,.2f})
        </span></p>
        <p><strong>Recommendation:</strong> {verdict.position_advice}</p>
    </div>
    """, unsafe_allow_html=True)


def render_pattern_signals(recent_patterns: list):
    """Render recent candlestick pattern signals."""
    if not recent_patterns:
        st.info("No candlestick patterns detected in recent candles")
        return

    for p in recent_patterns[:8]:
        direction = p["direction"].lower()
        date_str = p["date"].strftime("%d %b %Y") if hasattr(p["date"], "strftime") else str(p["date"])
        st.markdown(f"""
        <div class="pattern-signal {direction}">
            <strong>{p['pattern']}</strong> — {date_str}
        </div>
        """, unsafe_allow_html=True)


def render_news(news_items: list):
    """Render Google Finance news headlines."""
    if not news_items:
        st.info("No recent news available")
        return

    for item in news_items[:8]:
        st.markdown(f'<div class="news-item">{item}</div>', unsafe_allow_html=True)


def render_holders_table(holders: dict):
    """Render institutional and mutual fund holders."""
    if holders.get("major") is not None and not holders["major"].empty:
        st.subheader("Major Holders")
        st.dataframe(holders["major"], use_container_width=True, hide_index=True)

    if holders.get("institutional") is not None and not holders["institutional"].empty:
        st.subheader("Top Institutional Holders")
        inst = holders["institutional"].copy()
        if "Date Reported" in inst.columns:
            inst["Date Reported"] = pd.to_datetime(inst["Date Reported"]).dt.strftime("%d %b %Y")
        st.dataframe(inst.head(10), use_container_width=True, hide_index=True)

    if holders.get("mutualfund") is not None and not holders["mutualfund"].empty:
        st.subheader("Top Mutual Fund Holders")
        mf = holders["mutualfund"].copy()
        if "Date Reported" in mf.columns:
            mf["Date Reported"] = pd.to_datetime(mf["Date Reported"]).dt.strftime("%d %b %Y")
        st.dataframe(mf.head(10), use_container_width=True, hide_index=True)

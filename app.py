"""
Stock Analyzer — Indian Markets (NSE/BSE)
Streamlit application combining fundamental, technical, and candlestick pattern analysis.
"""

import streamlit as st
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.ticker_map import resolve_ticker
from config import settings
from data.fetcher import fetch_all
from analysis.fundamental import analyze as analyze_fundamentals
from analysis.technical import analyze as analyze_technicals
from analysis.candlestick_patterns import detect_all_patterns, score_candlestick_signals, get_recent_signals
from analysis.market_structure import identify_trend, find_support_resistance, compute_fibonacci_levels
from analysis.elliott_wave import analyze as analyze_elliott_wave
from analysis.verdict import generate_verdict
from ui.styles import inject_css
from ui.components import (
    render_company_header,
    render_metric_card,
    render_verdict_banner,
    render_target_cards,
    render_position_card,
    render_pattern_signals,
    render_news,
    render_holders_table,
)
from ui.charts import (
    build_candlestick_chart,
    build_rsi_macd_chart,
    build_shareholding_chart,
    build_fundamental_radar,
    build_score_gauge,
)

# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Stock Analyzer - Indian Markets",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ─── Sidebar ─────────────────────────────────────────────────────────────────

st.sidebar.title("Stock Analyzer")
st.sidebar.markdown("*Indian Markets (NSE/BSE)*")

stock_input = st.sidebar.text_input(
    "Stock Name or Ticker",
    placeholder="e.g. RELIANCE, TCS, HDFCBANK",
    help="Enter NSE/BSE symbol, company name, or ticker with suffix (.NS / .BO)",
)

exchange = st.sidebar.radio("Exchange", ["NSE", "BSE"], horizontal=True)

st.sidebar.markdown("---")
st.sidebar.markdown("**Chart Timeframe**")

timeframe_options = list(settings.TIMEFRAME_OPTIONS.keys())
selected_timeframe = st.sidebar.selectbox(
    "Timeframe",
    timeframe_options,
    index=timeframe_options.index(settings.DEFAULT_TIMEFRAME),
    help="Select the chart timeframe for technical analysis",
)

tf_config = settings.TIMEFRAME_OPTIONS[selected_timeframe]
st.sidebar.caption(f"📊 {tf_config['label']} — Best for: {tf_config['best_for']}")

st.sidebar.markdown("---")
st.sidebar.markdown("**Your Position (Optional)**")

user_units = st.sidebar.number_input(
    "Units Held", min_value=0.0, value=0.0, step=1.0,
    help="Number of shares you currently hold",
)

user_buy_price = st.sidebar.number_input(
    "Buy Price (INR)", min_value=0.0, value=0.0, step=0.1,
    help="Your average buy price per share",
)

analyze_btn = st.sidebar.button("Analyze", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<small>Data: yfinance + Google Finance + NSE India<br>"
    "Analysis: Fundamental + Technical + Candlestick Patterns<br>"
    "Candlestick patterns from <i>The Candlestick Trading Bible</i></small>",
    unsafe_allow_html=True,
)

# ─── Main Content ────────────────────────────────────────────────────────────

if not analyze_btn and "stock_data" not in st.session_state:
    st.markdown("## Welcome to Stock Analyzer")
    st.markdown(
        "Enter a stock ticker in the sidebar and click **Analyze** to get a comprehensive "
        "fundamental, technical, and candlestick pattern analysis with a Buy/Sell/Hold recommendation."
    )
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Fundamental Analysis")
        st.markdown(
            "- P/E, P/B, ROE, ROCE\n"
            "- Debt/Equity ratio\n"
            "- Earnings & Revenue growth\n"
            "- Promoter holding & pledge\n"
            "- Dividend yield & margins"
        )
    with col2:
        st.markdown("#### Technical Analysis")
        st.markdown(
            "- Moving Averages (SMA/EMA)\n"
            "- RSI, MACD, Bollinger Bands\n"
            "- Support & Resistance levels\n"
            "- Trend detection (ADX)\n"
            "- Volume analysis"
        )
    with col3:
        st.markdown("#### Candlestick Patterns")
        st.markdown(
            "- Engulfing (Bullish/Bearish)\n"
            "- Doji, Dragonfly, Gravestone\n"
            "- Morning & Evening Star\n"
            "- Hammer & Shooting Star\n"
            "- Inside Bar, Tweezers"
        )
    st.stop()

# ─── Run Analysis ────────────────────────────────────────────────────────────

if analyze_btn:
    if not stock_input:
        st.error("Please enter a stock name or ticker.")
        st.stop()

    ticker, display_name = resolve_ticker(stock_input, exchange)
    if not ticker:
        st.error("Could not resolve ticker. Please check the input.")
        st.stop()

    # Fetch data with selected timeframe
    tf = settings.TIMEFRAME_OPTIONS[selected_timeframe]
    with st.spinner(f"Fetching {selected_timeframe.lower()} data for {display_name} ({ticker})..."):
        stock_data = fetch_all(ticker, period=tf["period"], interval=tf["interval"])

    if stock_data.history.empty:
        st.error(f"No price data found for {ticker}. Please check the ticker and try again.")
        st.stop()

    # Run analysis
    with st.spinner("Running fundamental analysis..."):
        fundamental_result = analyze_fundamentals(stock_data.info, stock_data.shareholding)

    with st.spinner("Running technical analysis..."):
        technical_result = analyze_technicals(stock_data.history)

    with st.spinner("Detecting candlestick patterns..."):
        patterns = detect_all_patterns(stock_data.history)
        market_struct = identify_trend(stock_data.history)
        sr_levels = find_support_resistance(stock_data.history)
        fib_levels = compute_fibonacci_levels(stock_data.history, market_struct["trend"])

        candle_score = score_candlestick_signals(
            patterns,
            market_struct["trend"],
            sr_levels["support_levels"],
            sr_levels["resistance_levels"],
            sr_levels["current_price"],
            ema_21=technical_result.ema_21,
            fib_levels=fib_levels,
            df=stock_data.history,
        )

    with st.spinner("Detecting Elliott Wave patterns..."):
        elliott_result = analyze_elliott_wave(
            stock_data.history,
            trend=market_struct["trend"],
            timeframe=selected_timeframe,
        )

    with st.spinner("Generating verdict..."):
        current_price = stock_data.info.get("current_price") or stock_data.history["close"].iloc[-1]
        final_verdict = generate_verdict(
            fundamental_result,
            technical_result,
            candle_score,
            market_struct,
            sr_levels,
            current_price,
            user_units,
            user_buy_price,
            selected_timeframe=selected_timeframe,
            elliott_result=elliott_result,
        )

    # Store in session state
    st.session_state["stock_data"] = stock_data
    st.session_state["fundamental_result"] = fundamental_result
    st.session_state["technical_result"] = technical_result
    st.session_state["patterns"] = patterns
    st.session_state["market_struct"] = market_struct
    st.session_state["sr_levels"] = sr_levels
    st.session_state["candle_score"] = candle_score
    st.session_state["final_verdict"] = final_verdict
    st.session_state["current_price"] = current_price
    st.session_state["fib_levels"] = fib_levels
    st.session_state["timeframe"] = selected_timeframe
    st.session_state["tf_config"] = tf
    st.session_state["elliott_result"] = elliott_result

# ─── Display Results ─────────────────────────────────────────────────────────

if "stock_data" in st.session_state:
    stock_data = st.session_state["stock_data"]
    fundamental_result = st.session_state["fundamental_result"]
    technical_result = st.session_state["technical_result"]
    patterns = st.session_state["patterns"]
    market_struct = st.session_state["market_struct"]
    sr_levels = st.session_state["sr_levels"]
    candle_score = st.session_state["candle_score"]
    final_verdict = st.session_state["final_verdict"]
    current_price = st.session_state["current_price"]
    fib_levels = st.session_state.get("fib_levels", {})
    timeframe = st.session_state.get("timeframe", "Daily")
    tf_config = st.session_state.get("tf_config", settings.TIMEFRAME_OPTIONS["Daily"])
    elliott_result = st.session_state.get("elliott_result", None)

    # Company header
    render_company_header(stock_data.info, stock_data.google_data)

    # Show errors if any
    if stock_data.errors:
        with st.expander("Data fetch warnings"):
            for err in stock_data.errors:
                st.warning(err)

    # ─── Tabs ────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Overview",
        "Fundamental Analysis",
        "Technical Analysis",
        "Shareholding & Investors",
        "Final Verdict",
    ])

    # ─── Tab 1: Overview ─────────────────────────────────────────────────
    with tab1:
        # Company description
        description = stock_data.info.get("long_description", "")
        if description:
            st.markdown("### About the Company")
            st.markdown(description)

        st.markdown("---")

        # Key metrics grid
        st.markdown("### Key Metrics")
        info = stock_data.info
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Sector", info.get("sector", "N/A"))
            st.metric("P/E Ratio", f"{info['trailing_pe']:.2f}" if info.get("trailing_pe") else "N/A")
            st.metric("EPS (TTM)", f"₹{info['eps_trailing']:.2f}" if info.get("eps_trailing") else "N/A")

        with col2:
            st.metric("Industry", info.get("industry", "N/A"))
            st.metric("P/B Ratio", f"{info['price_to_book']:.2f}" if info.get("price_to_book") else "N/A")
            st.metric("Beta", f"{info['beta']:.2f}" if info.get("beta") else "N/A")

        with col3:
            emp = info.get("employees")
            st.metric("Employees", f"{emp:,}" if emp else "N/A")
            roe = info.get("return_on_equity")
            st.metric("ROE", f"{roe*100:.1f}%" if roe else "N/A")
            dy = info.get("dividend_yield")
            st.metric("Dividend Yield", f"{dy*100:.2f}%" if dy else "N/A")

        with col4:
            de = info.get("debt_to_equity")
            st.metric("Debt/Equity", f"{de:.2f}" if de else "N/A")
            pm = info.get("profit_margins")
            st.metric("Profit Margin", f"{pm*100:.1f}%" if pm else "N/A")
            rg = info.get("revenue_growth")
            st.metric("Revenue Growth", f"{rg*100:.1f}%" if rg else "N/A")

        # News
        news = stock_data.google_data.get("news", [])
        if news:
            st.markdown("---")
            st.markdown("### Recent News")
            render_news(news)

    # ─── Tab 2: Fundamental Analysis ─────────────────────────────────────
    with tab2:
        st.markdown("### Fundamental Analysis")

        # Score gauges
        col1, col2 = st.columns([1, 2])
        with col1:
            fig_gauge = build_score_gauge(fundamental_result.normalized_score, "Fundamental Score")
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.markdown(f"**Verdict: {fundamental_result.verdict}**")
            st.markdown(fundamental_result.summary)

        with col2:
            fig_radar = build_fundamental_radar(fundamental_result.metrics)
            if fig_radar.data:
                st.plotly_chart(fig_radar, use_container_width=True)

        st.markdown("---")
        st.markdown("### Metric Breakdown")

        # Metrics in 2-column layout
        col1, col2 = st.columns(2)
        for i, metric in enumerate(fundamental_result.metrics):
            with col1 if i % 2 == 0 else col2:
                render_metric_card(metric)

    # ─── Tab 3: Technical Analysis ───────────────────────────────────────
    with tab3:
        st.markdown("### Technical Analysis")
        st.markdown(
            f"<div style='background:rgba(33,150,243,0.1); padding:8px 14px; border-radius:6px; "
            f"margin-bottom:12px; display:inline-block;'>"
            f"📊 <b>Timeframe:</b> {tf_config['label']} ({tf_config['candle_label']} candles) "
            f"&nbsp;·&nbsp; Best for: {tf_config['best_for']}</div>",
            unsafe_allow_html=True,
        )

        # Score gauge
        col1, col2 = st.columns([1, 3])
        with col1:
            fig_gauge = build_score_gauge(technical_result.normalized_score, "Technical Score")
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.markdown(f"**Verdict: {technical_result.verdict}**")
            st.markdown(technical_result.summary)
            st.markdown(f"**Trend: {market_struct['trend'].title()}** ({market_struct['strength']})")
            st.markdown(market_struct["description"])

        with col2:
            pass  # Space for layout balance

        st.markdown("---")

        # Candlestick chart with overlays
        st.markdown(f"### Price Chart — {tf_config['candle_label']} Candles")
        fig_candle = build_candlestick_chart(
            stock_data.history,
            patterns=patterns,
            support_levels=sr_levels["support_levels"],
            resistance_levels=sr_levels["resistance_levels"],
            sma_20=technical_result.sma_20,
            sma_50=technical_result.sma_50,
            sma_200=technical_result.sma_200,
            bb_upper=technical_result.bb_upper,
            bb_lower=technical_result.bb_lower,
            ema_21=technical_result.ema_21,
            fib_levels=fib_levels,
            timeframe_label=tf_config["candle_label"],
            elliott_wave=elliott_result,
        )
        st.plotly_chart(fig_candle, use_container_width=True)

        # RSI / MACD chart
        st.markdown("### Indicators")
        fig_indicators = build_rsi_macd_chart(
            stock_data.history,
            technical_result.rsi,
            technical_result.macd_line,
            technical_result.macd_signal,
            technical_result.macd_hist,
        )
        st.plotly_chart(fig_indicators, use_container_width=True)

        # Indicator scores
        st.markdown("### Indicator Breakdown")
        col1, col2 = st.columns(2)
        for i, ind in enumerate(technical_result.indicators):
            with col1 if i % 2 == 0 else col2:
                render_metric_card(ind)

        # Candlestick patterns
        st.markdown("---")
        st.markdown("### Recent Candlestick Patterns")
        st.markdown(f"**Candlestick Verdict: {candle_score['verdict']}** (Score: {candle_score['score']})")
        st.markdown(candle_score["explanation"])
        render_pattern_signals(candle_score["recent_patterns"])

        # Pin Bar Entry Levels (Enhancement 1)
        pin_entries = candle_score.get("pin_bar_entries", [])
        if pin_entries:
            st.markdown("---")
            st.markdown("### Pin Bar Entry Levels")
            st.markdown("*Per 'The Candlestick Trading Bible' — 3 entry strategies for pin bars:*")
            for entry in pin_entries:
                st.markdown(f"**{entry.get('type', 'Pin Bar')}**")
                ec1, ec2, ec3, ec4 = st.columns(4)
                ec1.metric("Aggressive Entry", f"₹{entry['aggressive']:,.2f}")
                ec2.metric("50% Retracement", f"₹{entry['retracement_50']:,.2f}")
                ec3.metric("Breakout Entry", f"₹{entry['breakout']:,.2f}")
                ec4.metric("Stop Loss", f"₹{entry['stop_loss']:,.2f}")

        # Fibonacci Levels
        if fib_levels and fib_levels.get("fib_500"):
            st.markdown("---")
            st.markdown("### Fibonacci Retracement Levels")
            fc1, fc2, fc3 = st.columns(3)
            fc1.metric("38.2% Level", f"₹{fib_levels['fib_382']:,.2f}")
            fc2.metric("50.0% Level", f"₹{fib_levels['fib_500']:,.2f}")
            fc3.metric("61.8% Level", f"₹{fib_levels['fib_618']:,.2f}")

        # Elliott Wave Analysis
        st.markdown("---")
        st.markdown("### Elliott Wave Analysis")
        if elliott_result and elliott_result.detected:
            # Confidence badge
            conf_colors = {
                "High": "#00C853", "Moderate": "#FFC107",
                "Low": "#FF9800", "Speculative": "#FF5252",
            }
            conf_color = conf_colors.get(elliott_result.confidence_label, "#666")
            wave_desc = elliott_result.wave_type.replace("_", " ").title()

            st.markdown(
                f'<div style="background:rgba(41,182,246,0.1); padding:10px 16px; '
                f'border-radius:8px; margin-bottom:12px; border-left:4px solid {conf_color};">'
                f'<strong>{wave_desc}</strong> '
                f'&nbsp;&middot;&nbsp; Confidence: {elliott_result.confidence:.0f}/100 '
                f'({elliott_result.confidence_label})'
                f'&nbsp;&middot;&nbsp; Currently in Wave {elliott_result.current_wave} '
                f'({elliott_result.current_wave_progress})</div>',
                unsafe_allow_html=True,
            )

            st.markdown(elliott_result.summary)

            # Rule validation (expandable) — only for impulse waves
            if elliott_result.rules_validation:
                with st.expander("Cardinal Rule Validation"):
                    for rule in elliott_result.rules_validation:
                        status = "PASS" if rule.passed else "FAIL"
                        color = "#00C853" if rule.passed else "#FF1744"
                        st.markdown(
                            f'<div style="padding:4px 0;">'
                            f'<span style="color:{color}; font-weight:700;">{status}</span> '
                            f'<strong>{rule.rule_name}</strong>: {rule.description}<br>'
                            f'<span style="color:#aaa; font-size:0.85rem;">{rule.detail}</span></div>',
                            unsafe_allow_html=True,
                        )

            # Fibonacci relationships
            if elliott_result.fib_relationships:
                with st.expander("Fibonacci Wave Relationships"):
                    for fib in elliott_result.fib_relationships:
                        deviation_pct = fib.deviation * 100
                        quality = "Excellent" if deviation_pct < 3 else (
                            "Good" if deviation_pct < 8 else "Approximate"
                        )
                        st.markdown(
                            f"- **{fib.description}**: {fib.actual_ratio:.3f} "
                            f"(ideal: {fib.ideal_ratio:.3f}, {quality})"
                        )
                    st.markdown(f"**Fibonacci Alignment Score: {elliott_result.fib_score:.0f}/100**")

            # Projections
            if elliott_result.projections:
                st.markdown("#### Where could the price go next?")
                for proj in elliott_result.projections[:3]:
                    conf_icon = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(proj.confidence, "⚪")
                    st.markdown(
                        f'{conf_icon} **{proj.label}** — **₹{proj.price:,.2f}** '
                        f'&nbsp; <span style="color:#888; font-size:0.85rem;">'
                        f'Probability: {proj.confidence}</span>',
                        unsafe_allow_html=True,
                    )
                    st.caption(f"    {getattr(proj, 'meaning', '')}")
                st.markdown("")

            # Warnings
            for w in elliott_result.warnings:
                st.caption(f"— {w}")
        else:
            st.info(
                "No clear Elliott Wave pattern detected in the current timeframe. "
                "This is normal — Elliott Wave patterns require well-defined swing structure "
                "and not all price action forms identifiable wave counts."
            )

    # ─── Tab 4: Shareholding & Investors ─────────────────────────────────
    with tab4:
        st.markdown("### Shareholding Pattern")

        # Shareholding chart
        if stock_data.shareholding and any(v is not None for k, v in stock_data.shareholding.items() if k != "quarters"):
            fig_sh = build_shareholding_chart(stock_data.shareholding)
            st.plotly_chart(fig_sh, use_container_width=True)

            # Current holdings summary
            sh = stock_data.shareholding
            cols = st.columns(4)
            if sh.get("promoter") is not None:
                cols[0].metric("Promoter", f"{sh['promoter']:.2f}%")
            if sh.get("fii") is not None:
                cols[1].metric("FII/FPI", f"{sh['fii']:.2f}%")
            if sh.get("dii") is not None:
                cols[2].metric("DII", f"{sh['dii']:.2f}%")
            if sh.get("public") is not None:
                cols[3].metric("Public", f"{sh['public']:.2f}%")

            if sh.get("promoter_pledge") is not None and sh["promoter_pledge"] > 0:
                st.warning(f"Promoter Pledge: {sh['promoter_pledge']:.2f}% of promoter shares are pledged")
        else:
            st.info("Shareholding data not available from NSE. Showing yfinance holder data.")

        st.markdown("---")

        # Institutional & MF holders from yfinance
        render_holders_table(stock_data.holders)

    # ─── Tab 5: Final Verdict ────────────────────────────────────────────
    with tab5:
        st.markdown("### Final Verdict")
        st.caption(f"Based on {tf_config['label']} technical analysis")

        # Verdict banner
        render_verdict_banner(final_verdict)

        # Target prices
        st.markdown("### Price Targets")
        render_target_cards(final_verdict, current_price)

        st.markdown(f"**Suggested Timeframe:** {final_verdict.timeframe}")

        # Position advice
        if final_verdict.position_advice:
            st.markdown("---")
            st.markdown("### Position Advice")
            render_position_card(final_verdict)

        # Reasoning
        st.markdown("---")
        st.markdown("### Analysis Breakdown")
        for reason in final_verdict.reasoning:
            st.markdown(f"- {reason}")

        # Score breakdown
        st.markdown("---")
        st.markdown("### Score Components")
        col1, col2, col3 = st.columns(3)
        with col1:
            fig = build_score_gauge(fundamental_result.normalized_score, "Fundamental")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = build_score_gauge(technical_result.normalized_score, "Technical")
            st.plotly_chart(fig, use_container_width=True)
        with col3:
            candle_normalized = (candle_score["score"] + 100) / 2
            fig = build_score_gauge(candle_normalized, "Candlestick")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.caption(
            "Disclaimer: This analysis is for educational purposes only and should not be considered as "
            "financial advice. Always do your own research and consult a qualified financial advisor "
            "before making investment decisions."
        )

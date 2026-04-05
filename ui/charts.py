"""
Plotly chart builders for the Stock Analyzer.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


def build_candlestick_chart(
    df: pd.DataFrame,
    patterns: dict = None,
    support_levels: list = None,
    resistance_levels: list = None,
    sma_20: pd.Series = None,
    sma_50: pd.Series = None,
    sma_200: pd.Series = None,
    bb_upper: pd.Series = None,
    bb_lower: pd.Series = None,
    ema_21: pd.Series = None,
    fib_levels: dict = None,
    timeframe_label: str = "1D",
    elliott_wave=None,
) -> go.Figure:
    """Build interactive candlestick chart with overlays."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.8, 0.2],
        subplot_titles=(f"Price ({timeframe_label})", "Volume"),
    )

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Price",
        increasing_line_color="#00C853",
        decreasing_line_color="#FF1744",
    ), row=1, col=1)

    # Moving averages
    if sma_20 is not None and not sma_20.empty:
        fig.add_trace(go.Scatter(
            x=df.index, y=sma_20, name="SMA 20",
            line=dict(color="#FFC107", width=1, dash="dot"),
            opacity=0.7,
        ), row=1, col=1)

    if sma_50 is not None and not sma_50.empty:
        fig.add_trace(go.Scatter(
            x=df.index, y=sma_50, name="SMA 50",
            line=dict(color="#2196F3", width=1.5),
            opacity=0.8,
        ), row=1, col=1)

    if sma_200 is not None and not sma_200.empty:
        fig.add_trace(go.Scatter(
            x=df.index, y=sma_200, name="SMA 200",
            line=dict(color="#9C27B0", width=2),
            opacity=0.8,
        ), row=1, col=1)

    # 21-EMA: Dynamic S/R per "The Candlestick Trading Bible" (pages 88-91)
    if ema_21 is not None and not ema_21.empty:
        fig.add_trace(go.Scatter(
            x=df.index, y=ema_21, name="EMA 21 (Dynamic S/R)",
            line=dict(color="#FF9800", width=1.5, dash="dash"),
            opacity=0.85,
        ), row=1, col=1)

    # Fibonacci Retracement Levels (pages 120, 154)
    if fib_levels and fib_levels.get("fib_382"):
        fib_colors = {"38.2%": "#78909C", "50.0%": "#546E7A", "61.8%": "#37474F"}
        for label, key in [("38.2%", "fib_382"), ("50.0%", "fib_500"), ("61.8%", "fib_618")]:
            val = fib_levels.get(key)
            if val:
                fig.add_hline(
                    y=val, row=1, col=1,
                    line=dict(color=fib_colors[label], width=1, dash="dot"),
                    annotation_text=f"Fib {label}: ₹{val:,.0f}",
                    annotation_position="top right",
                    annotation_font_size=9,
                    annotation_font_color=fib_colors[label],
                )

    # Bollinger Bands
    if bb_upper is not None and not bb_upper.empty and bb_lower is not None and not bb_lower.empty:
        fig.add_trace(go.Scatter(
            x=df.index, y=bb_upper, name="BB Upper",
            line=dict(color="rgba(150,150,150,0.3)", width=1),
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=bb_lower, name="BB Lower",
            line=dict(color="rgba(150,150,150,0.3)", width=1),
            fill="tonexty",
            fillcolor="rgba(150,150,150,0.05)",
            showlegend=False,
        ), row=1, col=1)

    # Support levels
    if support_levels:
        for level in support_levels[:3]:
            fig.add_hline(
                y=level, row=1, col=1,
                line=dict(color="#00C853", width=1, dash="dash"),
                annotation_text=f"S: ₹{level:,.0f}",
                annotation_position="top left",
            )

    # Resistance levels
    if resistance_levels:
        for level in resistance_levels[:3]:
            fig.add_hline(
                y=level, row=1, col=1,
                line=dict(color="#FF1744", width=1, dash="dash"),
                annotation_text=f"R: ₹{level:,.0f}",
                annotation_position="bottom left",
            )

    # Pattern annotations
    if patterns:
        _add_pattern_markers(fig, df, patterns)

    # Elliott Wave overlay
    if elliott_wave and elliott_wave.detected:
        _add_elliott_wave_overlay(fig, elliott_wave)

    # Volume bars
    if "volume" in df.columns:
        colors = ["#00C853" if c >= o else "#FF1744" for c, o in zip(df["close"], df["open"])]
        fig.add_trace(go.Bar(
            x=df.index, y=df["volume"], name="Volume",
            marker_color=colors, opacity=0.5,
            showlegend=False,
        ), row=2, col=1)

    fig.update_layout(
        height=600,
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=11),
    )
    fig.update_yaxes(title_text="Price (INR)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)

    return fig


def _add_pattern_markers(fig: go.Figure, df: pd.DataFrame, patterns: dict):
    """Add candlestick pattern markers to the chart."""
    pattern_labels = {
        "engulfing": {100: "BE", -100: "SE"},
        "doji": {100: "DF", -100: "GS", 50: "D"},
        "morning_evening_star": {100: "MS", -100: "ES"},
        "hammer_shooting_star": {100: "H", -100: "SS"},
        "inside_bar": {50: "IB"},
        "tweezers": {100: "TB", -100: "TT"},
        "false_breakout": {100: "FB", -100: "FB"},
    }

    for pattern_key, signals in patterns.items():
        labels = pattern_labels.get(pattern_key, {})
        for idx, val in signals.items():
            if val != 0 and int(val) in labels:
                is_bullish = val > 0
                y_pos = df.loc[idx, "low"] * 0.995 if is_bullish else df.loc[idx, "high"] * 1.005
                color = "#00C853" if is_bullish else "#FF1744"

                fig.add_annotation(
                    x=idx, y=y_pos,
                    text=labels[int(val)],
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=0.8,
                    arrowcolor=color,
                    ax=0,
                    ay=25 if is_bullish else -25,
                    font=dict(size=9, color=color, family="monospace"),
                    bgcolor="rgba(30,30,46,0.8)",
                    bordercolor=color,
                    borderwidth=1,
                    borderpad=2,
                )


def _add_elliott_wave_overlay(fig: go.Figure, elliott_wave) -> None:
    """Add Elliott Wave lines, labels, and projection targets to the chart."""
    wave_color = "#29B6F6"  # Light blue — distinct from all existing overlays

    wp = elliott_wave.wave_points
    if not wp:
        return

    # Wave connecting line with labels
    x_vals = [pt.index for pt in wp]
    y_vals = [pt.price for pt in wp]
    labels = [pt.wave_label for pt in wp]

    # Determine text position: above for highs, below for lows
    text_positions = []
    for i, pt in enumerate(wp):
        if i == 0:
            text_positions.append("top center")
        elif pt.price > wp[i - 1].price:
            text_positions.append("top center")
        else:
            text_positions.append("bottom center")

    fig.add_trace(go.Scatter(
        x=x_vals, y=y_vals,
        mode="lines+markers+text",
        name="Elliott Wave",
        line=dict(color=wave_color, width=2),
        marker=dict(size=10, symbol="diamond", color=wave_color,
                    line=dict(width=1, color="white")),
        text=labels,
        textposition=text_positions,
        textfont=dict(size=11, color=wave_color, family="Arial Black"),
        hovertemplate="Wave %{text}<br>₹%{y:,.0f}<extra></extra>",
    ), row=1, col=1)

    # Projection target lines
    for proj in elliott_wave.projections:
        fig.add_hline(
            y=proj.price, row=1, col=1,
            line=dict(color=wave_color, width=1, dash="dashdot"),
            annotation_text=f"{proj.label}: ₹{proj.price:,.0f}",
            annotation_position="top right",
            annotation_font_size=9,
            annotation_font_color=wave_color,
            opacity=0.6,
        )


def build_rsi_macd_chart(
    df: pd.DataFrame,
    rsi: pd.Series,
    macd_line: pd.Series,
    macd_signal: pd.Series,
    macd_hist: pd.Series,
) -> go.Figure:
    """Build RSI and MACD subplot chart."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("RSI (14)", "MACD (12, 26, 9)"),
        row_heights=[0.5, 0.5],
    )

    # RSI
    if not rsi.empty:
        fig.add_trace(go.Scatter(
            x=df.index, y=rsi, name="RSI",
            line=dict(color="#2196F3", width=1.5),
        ), row=1, col=1)
        fig.add_hline(y=70, row=1, col=1, line=dict(color="#FF1744", width=1, dash="dash"))
        fig.add_hline(y=30, row=1, col=1, line=dict(color="#00C853", width=1, dash="dash"))
        fig.add_hline(y=50, row=1, col=1, line=dict(color="gray", width=0.5, dash="dot"))
        fig.add_hrect(y0=70, y1=100, row=1, col=1, fillcolor="rgba(255,23,68,0.05)", line_width=0)
        fig.add_hrect(y0=0, y1=30, row=1, col=1, fillcolor="rgba(0,200,83,0.05)", line_width=0)

    # MACD
    if not macd_line.empty:
        fig.add_trace(go.Scatter(
            x=df.index, y=macd_line, name="MACD",
            line=dict(color="#2196F3", width=1.5),
        ), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=macd_signal, name="Signal",
            line=dict(color="#FF9800", width=1.5),
        ), row=2, col=1)
        colors = ["#00C853" if v >= 0 else "#FF1744" for v in macd_hist]
        fig.add_trace(go.Bar(
            x=df.index, y=macd_hist, name="Histogram",
            marker_color=colors, opacity=0.5,
        ), row=2, col=1)
        fig.add_hline(y=0, row=2, col=1, line=dict(color="gray", width=0.5))

    fig.update_layout(
        height=400,
        template="plotly_dark",
        margin=dict(l=50, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=11),
    )

    return fig


def build_shareholding_chart(shareholding: dict) -> go.Figure:
    """Build shareholding pattern stacked bar chart."""
    quarters = shareholding.get("quarters", [])

    if not quarters:
        # Use single point data
        labels = ["Latest"]
        promoter = [shareholding.get("promoter", 0) or 0]
        fii = [shareholding.get("fii", 0) or 0]
        dii = [shareholding.get("dii", 0) or 0]
        public = [shareholding.get("public", 0) or 0]
    else:
        labels = [q.get("quarter", f"Q{i+1}") for i, q in enumerate(reversed(quarters))]
        promoter = [q.get("promoter", 0) or 0 for q in reversed(quarters)]
        fii = [q.get("fii", 0) or 0 for q in reversed(quarters)]
        dii = [q.get("dii", 0) or 0 for q in reversed(quarters)]
        public = [q.get("public", 0) or 0 for q in reversed(quarters)]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Promoter", x=labels, y=promoter, marker_color="#2196F3"))
    fig.add_trace(go.Bar(name="FII/FPI", x=labels, y=fii, marker_color="#FF9800"))
    fig.add_trace(go.Bar(name="DII", x=labels, y=dii, marker_color="#00C853"))
    fig.add_trace(go.Bar(name="Public", x=labels, y=public, marker_color="#9C27B0"))

    fig.update_layout(
        barmode="stack",
        height=350,
        template="plotly_dark",
        margin=dict(l=50, r=20, t=20, b=20),
        yaxis_title="Holding %",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(size=11),
    )

    return fig


def build_fundamental_radar(metrics: list) -> go.Figure:
    """Build radar/spider chart for fundamental metrics."""
    scored = [m for m in metrics if m.label != "N/A" and m.value is not None]
    if not scored:
        return go.Figure()

    categories = [m.name for m in scored]
    # Normalize scores from [-2, 2] to [0, 100]
    values = [(m.score + 2) / 4 * 100 for m in scored]
    values.append(values[0])  # Close the polygon
    categories.append(categories[0])

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        fillcolor="rgba(33, 150, 243, 0.2)",
        line=dict(color="#2196F3", width=2),
        name="Fundamental Score",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False),
            bgcolor="rgba(30,30,46,0.5)",
        ),
        height=350,
        template="plotly_dark",
        margin=dict(l=60, r=60, t=20, b=20),
        font=dict(size=11),
        showlegend=False,
    )

    return fig


def build_score_gauge(score: float, title: str) -> go.Figure:
    """Build a gauge chart for displaying a score."""
    if score >= 75:
        color = "#00C853"
    elif score >= 60:
        color = "#4CAF50"
    elif score >= 40:
        color = "#FFC107"
    elif score >= 25:
        color = "#FF5252"
    else:
        color = "#FF1744"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title=dict(text=title, font=dict(size=14)),
        number=dict(suffix="/100", font=dict(size=20)),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1),
            bar=dict(color=color),
            bgcolor="rgba(30,30,46,0.5)",
            steps=[
                dict(range=[0, 25], color="rgba(255,23,68,0.15)"),
                dict(range=[25, 40], color="rgba(255,82,82,0.1)"),
                dict(range=[40, 60], color="rgba(255,193,7,0.1)"),
                dict(range=[60, 75], color="rgba(76,175,80,0.1)"),
                dict(range=[75, 100], color="rgba(0,200,83,0.15)"),
            ],
            threshold=dict(line=dict(color="white", width=2), value=score),
        ),
    ))

    fig.update_layout(
        height=200,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=10),
        font=dict(size=11),
    )

    return fig

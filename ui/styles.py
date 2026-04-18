"""
Custom CSS styles for the Streamlit app.
"""

CUSTOM_CSS = """
<style>
    /* Main container */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }

    /* Metric cards */
    .metric-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 6px 0;
        border-left: 4px solid #666;
    }
    .metric-card.bullish { border-left-color: #00C853; }
    .metric-card.bearish { border-left-color: #FF1744; }
    .metric-card.neutral { border-left-color: #FFC107; }

    .metric-card .metric-name {
        font-size: 0.85rem;
        color: #aaa;
        margin-bottom: 4px;
    }
    .metric-card .metric-value {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 4px;
    }
    .metric-card .metric-label {
        font-size: 0.8rem;
        font-weight: 600;
    }
    .metric-card .metric-explanation {
        font-size: 0.78rem;
        color: #bbb;
        margin-top: 4px;
    }

    /* Verdict banner */
    .verdict-banner {
        border-radius: 16px;
        padding: 28px 32px;
        text-align: center;
        margin: 16px 0;
    }
    .verdict-banner.strong-buy {
        background: linear-gradient(135deg, #004d25, #00C853);
        color: white;
    }
    .verdict-banner.buy {
        background: linear-gradient(135deg, #1b5e20, #4CAF50);
        color: white;
    }
    .verdict-banner.hold {
        background: linear-gradient(135deg, #e65100, #FFC107);
        color: white;
    }
    .verdict-banner.sell {
        background: linear-gradient(135deg, #b71c1c, #FF5252);
        color: white;
    }
    .verdict-banner.strong-sell {
        background: linear-gradient(135deg, #4a0000, #FF1744);
        color: white;
    }
    .verdict-banner h1 {
        margin: 0;
        font-size: 2.2rem;
    }
    .verdict-banner .confidence {
        font-size: 1rem;
        opacity: 0.9;
        margin-top: 6px;
    }

    /* Score badge */
    .score-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .score-badge.green { background: #00C853; color: white; }
    .score-badge.red { background: #FF1744; color: white; }
    .score-badge.amber { background: #FFC107; color: #333; }

    /* Position card */
    .position-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 12px 0;
        border: 1px solid #333;
    }

    /* News items */
    .news-item {
        padding: 8px 0;
        border-bottom: 1px solid #333;
        font-size: 0.9rem;
    }

    /* Pattern signal */
    .pattern-signal {
        padding: 8px 12px;
        border-radius: 8px;
        margin: 4px 0;
        font-size: 0.85rem;
    }
    .pattern-signal.bullish { background: rgba(0, 200, 83, 0.15); border-left: 3px solid #00C853; }
    .pattern-signal.bearish { background: rgba(255, 23, 68, 0.15); border-left: 3px solid #FF1744; }
    .pattern-signal.neutral { background: rgba(255, 193, 7, 0.15); border-left: 3px solid #FFC107; }

    /* Target card */
    .target-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        border: 1px solid #333;
    }
    .target-card .label {
        font-size: 0.8rem;
        color: #aaa;
        margin-bottom: 4px;
    }
    .target-card .price {
        font-size: 1.5rem;
        font-weight: 700;
    }
    .target-card .price.green { color: #00C853; }
    .target-card .price.red { color: #FF1744; }
    .target-card .price.amber { color: #FFC107; }

    /* Company header */
    .company-header {
        padding: 8px 0 16px 0;
    }
    .company-header h1 {
        margin-bottom: 0;
    }
    .company-header .subtitle {
        color: #aaa;
        font-size: 0.9rem;
    }
    /* Advanced Levels Verdict Banner */
    .al-verdict-banner { border-radius: 16px; padding: 24px 32px; text-align: center; margin: 16px 0; }
    .al-verdict-banner.strong-support { background: linear-gradient(135deg, #004d25, #00C853); color: white; }
    .al-verdict-banner.support { background: linear-gradient(135deg, #2e7d32, #66BB6A); color: white; }
    .al-verdict-banner.neutral { background: linear-gradient(135deg, #e65100, #FFC107); color: white; }
    .al-verdict-banner.resistance { background: linear-gradient(135deg, #c62828, #FF5252); color: white; }
    .al-verdict-banner.strong-resistance { background: linear-gradient(135deg, #4a0000, #FF1744); color: white; }
    .al-verdict-banner h2 { margin: 0; font-size: 1.8rem; }
    .al-verdict-banner .al-score { font-size: 1rem; opacity: 0.9; margin-top: 6px; }
    .al-verdict-banner .al-summary { font-size: 0.85rem; opacity: 0.8; margin-top: 8px; font-style: italic; }

    /* Advanced Levels MA Card */
    .al-level-card { background: #1e1e2e; border-radius: 10px; padding: 12px 16px; text-align: center; border: 1px solid #333; margin: 4px 0; }
    .al-level-card .al-tf { font-size: 0.75rem; color: #aaa; text-transform: uppercase; }
    .al-level-card .al-value { font-size: 1.1rem; font-weight: 700; margin: 4px 0; }
    .al-level-card .al-group { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 0.7rem; font-weight: 700; }
    .al-level-card .al-group.l1 { background: #78909C; color: white; }
    .al-level-card .al-group.l2 { background: #E91E63; color: white; }
    .al-level-card .al-group.l3 { background: #7C4DFF; color: white; }
    .al-level-card .al-pos { font-size: 0.8rem; margin-top: 4px; }
    .al-level-card .al-pos.support { color: #00C853; }
    .al-level-card .al-pos.resistance { color: #FF1744; }
    .al-level-card .al-pos.near { color: #FFC107; }

    /* Elliott Wave Verdict Banner */
    .ew-verdict-banner {
        border-radius: 16px;
        padding: 24px 32px;
        text-align: center;
        margin: 16px 0;
    }
    .ew-verdict-banner.bullish {
        background: linear-gradient(135deg, #1b5e20, #4CAF50);
        color: white;
    }
    .ew-verdict-banner.caution {
        background: linear-gradient(135deg, #e65100, #FFC107);
        color: white;
    }
    .ew-verdict-banner.wait {
        background: linear-gradient(135deg, #1a237e, #42A5F5);
        color: white;
    }
    .ew-verdict-banner.bearish {
        background: linear-gradient(135deg, #b71c1c, #FF5252);
        color: white;
    }
    .ew-verdict-banner.no-signal {
        background: linear-gradient(135deg, #37474f, #78909C);
        color: white;
    }
    .ew-verdict-banner h2 { margin: 0; font-size: 1.8rem; }
    .ew-verdict-banner .ew-headline { font-size: 1.1rem; margin-top: 6px; opacity: 0.95; }
    .ew-verdict-banner .ew-confidence { font-size: 0.9rem; opacity: 0.85; margin-top: 4px; }
    .ew-verdict-banner .ew-rationale { font-size: 0.85rem; opacity: 0.8; margin-top: 8px; font-style: italic; }
</style>
"""


def inject_css():
    """Inject custom CSS into the Streamlit app."""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

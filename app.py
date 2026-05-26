"""
Data Spine — PCA Builder + Conversation Engine
Run: streamlit run app.py
"""
import streamlit as st
import json, time, tempfile, os
import pandas as pd
from datetime import date

_TMPDIR = tempfile.gettempdir()

st.set_page_config(page_title="Data Spine", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ─── Design tokens ─────────────────────────────────────── */
:root {
  --navy:       #0C0A28;
  --navy-mid:   #1A1755;
  --purple:     #4338CA;
  --purple-lt:  #6D63E8;
  --purple-bg:  #EEEDF8;
  --orange:     #F05C2C;
  --orange-bg:  #FEF0EB;
  --bg:         #F4F5F7;
  --surface:    #FFFFFF;
  --border:     #E3E6ED;
  --border-lt:  #F0F2F6;
  --text-1:     #0F172A;
  --text-2:     #4B5563;
  --text-3:     #94A3B8;
  --green:      #059669;
  --green-bg:   #ECFDF5;
  --red:        #DC2626;
  --red-bg:     #FEF2F2;
  --sh-sm:      0 1px 3px rgba(15,23,42,.06), 0 1px 2px rgba(15,23,42,.04);
  --sh-md:      0 4px 16px rgba(15,23,42,.08), 0 1px 4px rgba(15,23,42,.04);
  --r-sm: 8px; --r-md: 12px; --r-lg: 16px;
}

/* ─── Base ──────────────────────────────────────────────── */
.stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; background: var(--bg); }
html, body { font-size: 14px; -webkit-font-smoothing: antialiased; }
.block-container { padding-top: 1.25rem !important; padding-bottom: 2rem !important; }

/* ─── Sidebar ────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
  background: var(--navy);
  border-right: 1px solid rgba(255,255,255,0.05);
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3,
section[data-testid="stSidebar"] .stMarkdown h4,
section[data-testid="stSidebar"] .stMarkdown h5,
section[data-testid="stSidebar"] .stWidgetLabel,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stRadio label div,
section[data-testid="stSidebar"] .stCheckbox label div {
  color: #B8BDD0 !important; font-size: 13px !important;
}
section[data-testid="stSidebar"] .stMarkdown h5 {
  color: #525980 !important; font-size: 10px !important; font-weight: 700 !important;
  text-transform: uppercase !important; letter-spacing: 1.2px !important; margin-bottom: 4px !important;
}
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] div[data-baseweb="select"] { color: var(--navy) !important; }
section[data-testid="stSidebar"] hr { border: none; border-top: 1px solid rgba(255,255,255,0.07); margin: 10px 0; }
section[data-testid="stSidebar"] .stCaption p { color: #525980 !important; font-size: 11px !important; }

/* Sidebar buttons (example prompts) */
section[data-testid="stSidebar"] .stButton > button {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid rgba(255,255,255,0.09) !important;
  color: #9BA3BF !important; border-radius: 7px !important;
  font-size: 12px !important; text-align: left !important;
  white-space: normal !important; line-height: 1.4 !important;
  padding: 7px 10px !important; transition: all 0.15s !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: rgba(255,255,255,0.09) !important;
  border-color: rgba(255,255,255,0.18) !important;
  color: #D0D5E8 !important;
}

/* Mode radio as nav */
section[data-testid="stSidebar"] .stRadio > div { gap: 1px !important; }
section[data-testid="stSidebar"] .stRadio label {
  border-radius: 7px !important; padding: 9px 12px !important;
  transition: background 0.12s !important; cursor: pointer !important;
}
section[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.06) !important; }

/* ─── Main header ────────────────────────────────────────── */
.main-header {
  background: linear-gradient(135deg, var(--navy) 0%, var(--navy-mid) 50%, #2D24A8 100%);
  padding: 22px 28px 18px; border-radius: var(--r-md); margin-bottom: 20px;
  border-bottom: 2px solid var(--orange); position: relative; overflow: hidden;
}
.main-header::after {
  content: ''; position: absolute; top: -60px; right: -60px;
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(109,99,232,.22) 0%, transparent 65%);
  pointer-events: none;
}
.main-header h1 {
  color: #FFFFFF !important; margin: 0 0 5px 0;
  font-size: 21px; font-weight: 700; letter-spacing: -0.4px; line-height: 1.2;
}
.main-header p { color: rgba(255,255,255,0.5); margin: 0; font-size: 12.5px; line-height: 1.5; }

/* ─── KPI cards ──────────────────────────────────────────── */
.kpi-card {
  background: var(--surface); border-radius: var(--r-md);
  padding: 16px 18px; border: 1px solid var(--border);
  box-shadow: var(--sh-sm); position: relative; overflow: hidden;
}
.kpi-card::before {
  content: ''; position: absolute; top: 0; left: 0;
  width: 3px; height: 100%; background: var(--purple);
}
.kpi-label {
  font-size: 10px; font-weight: 700; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.9px; margin-bottom: 8px;
}
.kpi-value { font-size: 23px; font-weight: 700; color: var(--text-1); line-height: 1; margin-bottom: 4px; }
.kpi-sub   { font-size: 11px; color: var(--text-3); }

/* ─── Slide cards ────────────────────────────────────────── */
.slide-card {
  background: var(--surface); border-radius: var(--r-md);
  padding: 18px 20px; margin-bottom: 8px;
  border: 1px solid var(--border); box-shadow: var(--sh-sm);
  transition: box-shadow 0.2s, border-color 0.2s;
}
.slide-card:hover { box-shadow: var(--sh-md); border-color: #D1CEF5; }
.slide-num {
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--purple); color: white; border-radius: 50%;
  width: 24px; height: 24px; font-size: 11px; font-weight: 700;
  margin-right: 8px; flex-shrink: 0; vertical-align: middle;
}
.slide-card ul { margin: 8px 0 0 4px; padding-left: 18px; }
.slide-card li { color: var(--text-2); line-height: 1.65; font-size: 13.5px; margin-bottom: 5px; }

/* ─── Storyline / type badges ────────────────────────────── */
.storyline-badge {
  display: inline-flex; align-items: center;
  background: var(--purple-bg); color: var(--purple);
  border-radius: 20px; padding: 2px 10px;
  font-size: 10.5px; font-weight: 600; margin-right: 4px;
}

/* ─── So-what callout ────────────────────────────────────── */
.so-what {
  background: linear-gradient(135deg, #EEEDF8, #F2F0FB);
  border-left: 3px solid var(--purple); border-radius: 0 8px 8px 0;
  padding: 9px 13px; font-size: 13px; font-weight: 500;
  color: var(--navy-mid); margin: 10px 0 6px;
  line-height: 1.5;
}

/* ─── Narrative role label ───────────────────────────────── */
.narrative-role { font-size: 11px; color: var(--text-3); font-style: italic; margin-top: 6px; line-height: 1.4; }

/* ─── Chat messages ──────────────────────────────────────── */
.chat-msg { margin-bottom: 12px; }
.chat-user {
  background: var(--purple-bg); border-radius: 12px 12px 4px 12px;
  padding: 12px 16px; font-size: 13.5px; line-height: 1.65;
  color: var(--text-1); max-width: 88%; margin-left: auto;
  border: 1px solid #DDD9F5;
}
.chat-ai {
  background: var(--surface); border: 1px solid var(--border);
  border-left: 3px solid var(--orange); border-radius: 4px 12px 12px 12px;
  padding: 14px 16px; font-size: 13.5px; line-height: 1.7;
  color: var(--text-1); max-width: 94%;
}
.chat-ai strong { color: var(--navy); }
.chat-ai ul, .chat-ai ol { margin: 6px 0; padding-left: 20px; }
.chat-ai li { margin-bottom: 4px; }

/* ─── Buttons ────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
  background: var(--purple) !important; border-color: var(--purple) !important;
  border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important;
  transition: background 0.15s !important;
}
.stButton > button[kind="primary"]:hover { background: #3730A3 !important; border-color: #3730A3 !important; }
.stButton > button:not([kind="primary"]) { border-radius: 8px !important; font-size: 13px !important; }
.stDownloadButton > button {
  border-color: var(--purple) !important; color: var(--purple) !important;
  border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important;
}
.stDownloadButton > button:hover { background: var(--purple-bg) !important; }

/* ─── Tabs ───────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  border-bottom: 1px solid var(--border) !important; gap: 0 !important; background: transparent !important;
}
.stTabs [data-baseweb="tab-list"] button {
  font-size: 13px !important; font-weight: 500 !important;
  padding: 10px 18px !important; color: var(--text-2) !important;
}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
  color: var(--purple) !important; border-bottom-color: var(--purple) !important;
  font-weight: 700 !important;
}

/* ─── DataFrames ─────────────────────────────────────────── */
.stDataFrame { border-radius: var(--r-sm) !important; border: 1px solid var(--border) !important; overflow: hidden; }

/* ─── st.metric ──────────────────────────────────────────── */
[data-testid="metric-container"] {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--r-md); padding: 14px 18px !important; box-shadow: var(--sh-sm);
}
[data-testid="stMetricLabel"] > div {
  font-size: 10px !important; font-weight: 700 !important; color: var(--text-3) !important;
  text-transform: uppercase !important; letter-spacing: 0.8px !important;
}
[data-testid="stMetricValue"] > div { font-size: 22px !important; font-weight: 700 !important; color: var(--text-1) !important; }
[data-testid="stMetricDelta"] > div { font-size: 12px !important; }

/* ─── Alerts / status ────────────────────────────────────── */
.stSuccess > div, .stInfo > div, .stWarning > div, .stError > div {
  border-radius: var(--r-sm) !important; font-size: 13px !important;
}

/* ─── Expanders ──────────────────────────────────────────── */
.streamlit-expanderHeader { font-weight: 600 !important; font-size: 13px !important; }

/* ─── Horizontal rule ────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 16px 0 !important; }

/* ─── Spinner ────────────────────────────────────────────── */
.stSpinner > div { border-top-color: var(--purple) !important; }

/* ─── Responsive ─────────────────────────────────────────── */
@media (max-width: 768px) {
  .main-header { padding: 16px 18px; }
  .main-header h1 { font-size: 17px; }
  .kpi-value { font-size: 19px; }
  .slide-card { padding: 14px 16px; }
  .chat-user, .chat-ai { max-width: 100%; }
}
</style>
""", unsafe_allow_html=True)

from data_layer import get_clients_in_date_range, get_campaigns_for_client, assemble_pca_data, get_portfolio_actuals
from llm_engine import generate_narrative, answer_question_with_llm, generate_quick_slides, answer_benchmark_question, generate_weekly_meet
from excel_builder import build_pca_workbook
from pptx_builder import build_pptx_from_template, build_quick_slides_pptx

# ─── Module-level cached helpers (must be at module scope for st.cache_data to work) ──

def _overview_to_plat_metrics(overview, channel_filter="all"):
    out = {}
    for row in overview:
        plat = row.get("platform", "")
        ch   = row.get("channel_type", "digital")
        if channel_filter != "all" and ch != channel_filter:
            continue
        out[plat] = {
            "channel": ch,
            "spend":   row.get("total_spend", 0),
            "cpm":     row.get("cpm"),
            "ctr":     row.get("ctr"),
            "cpc":     row.get("cpc"),
            "cpcv":    row.get("cpcv"),
        }
    return out

@st.cache_data(show_spinner="Loading campaign data…")
def _load_camp_plats(client_id, camp_id, camp_start, camp_end, ch):
    d = assemble_pca_data(client_id, camp_id, camp_start, camp_end, ch)
    return _overview_to_plat_metrics(d.get("overview", []), ch)

@st.cache_data(show_spinner="Loading client history…")
def _load_all_client_plats(client_id, start, end, ch):
    camps = get_campaigns_for_client(client_id, start, end)
    per_camp = {}
    for c in camps:
        d = assemble_pca_data(client_id, c["campaign_id"],
                              max(start, c["start"]), min(end, c["end"]), ch)
        per_camp[c["campaign_name"]] = _overview_to_plat_metrics(d.get("overview", []), ch)
    return per_camp

@st.cache_data(show_spinner="Computing portfolio actuals…")
def _load_actuals(start, end, ch):
    return get_portfolio_actuals(start, end, ch)

@st.cache_data(show_spinner="Loading dashboard data…")
def _load_dashboard_data(client_id, camp_id, camp_start, camp_end, ch):
    return assemble_pca_data(client_id, camp_id, camp_start, camp_end, ch)

# ═══════════════════════════════════════
# SETTINGS (initialise defaults + hardcode API key)
# ═══════════════════════════════════════
DEFAULT_SETTINGS = {
    # Data is always live BigQuery — no toggle needed
    "settings_llm_enabled": True,
    "settings_use_vertex": True,          # default: Vertex AI via gcloud ADC
    "settings_llm_provider": "Vertex AI (Gemini)",
    "settings_llm_model": "gemini-2.5-flash-preview-05-20",   # fallback for API key path
    "settings_llm_project": "res-apac-dev-skynet-au",
    "settings_llm_location": "us-central1",
    "settings_channel_filter": "All Channels (Online + Offline)"
}

for k, v in DEFAULT_SETTINGS.items():
    if k not in st.session_state: 
        st.session_state[k] = v

# ═══════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════
with st.sidebar:
    st.markdown("""<div style="padding:16px 4px 12px;">
  <div style="font-size:18px;font-weight:800;color:#FFFFFF;letter-spacing:-0.5px;line-height:1.1;">Data Spine</div>
  <div style="font-size:11px;color:#525980;font-weight:500;margin-top:3px;letter-spacing:0.3px;">Post-Campaign Intelligence</div>
</div>""", unsafe_allow_html=True)

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "📈 Dashboard"

    def _set_mode(m): st.session_state.app_mode = m
    def nav_btn(label):
        active = (st.session_state.app_mode == label)
        st.button(label, on_click=_set_mode, args=(label,), type="primary" if active else "secondary", use_container_width=True)

    st.markdown("##### 📈 Reporting & Benchmarks")
    nav_btn("📈 Dashboard")
    nav_btn("🏆 Benchmarks")
    nav_btn("📅 Weekly Meet")

    st.markdown("##### 📊 PCA & Insights")
    nav_btn("💬 Ask a Question")
    nav_btn("📊 Build PCA")
    nav_btn("⚡ Slide Generator")

    mode = st.session_state.app_mode

    # Always use all channels; always use live LLM + Vertex
    ch_val    = "all"
    ch_filter = "All Channels"

    _data_status = "🟢 BigQuery"
    _llm_status  = "🟢 Vertex AI"
    st.caption(f"{_data_status}  •  {_llm_status}")
    st.markdown("---")

# ═══════════════════════════════════════
# MODE 1: CONVERSATION ENGINE
# ═══════════════════════════════════════
if mode == "💬 Ask a Question":

    # ── Extra CSS for chat ──────────────────────────────────────────────────
    st.markdown("""
    <style>
    .qa-header { padding: 28px 0 8px; }
    .qa-header h1 { font-size: 2rem; font-weight: 800; color: var(--navy); margin: 0; }
    .qa-header p  { color: var(--text-2); margin: 4px 0 0; font-size: 0.92rem; }

    .msg-wrap { display: flex; margin-bottom: 16px; align-items: flex-start; gap: 12px; }
    .msg-wrap.user  { flex-direction: row-reverse; }
    .msg-avatar {
        width: 34px; height: 34px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 1rem; flex-shrink: 0; margin-top: 2px;
    }
    .msg-avatar.user-av  { background: var(--purple); color: #fff; }
    .msg-avatar.ai-av    { background: var(--navy);   color: #fff; }
    .msg-bubble {
        max-width: 82%; padding: 14px 18px; border-radius: 16px;
        font-size: 0.93rem; line-height: 1.65; word-break: break-word;
    }
    .msg-bubble.user-bub {
        background: var(--purple); color: #fff;
        border-bottom-right-radius: 4px;
    }
    .msg-bubble.ai-bub {
        background: var(--surface); color: var(--text-1);
        border: 1px solid var(--border); border-bottom-left-radius: 4px;
        box-shadow: var(--sh-sm);
    }
    .msg-meta { font-size: 0.72rem; color: var(--text-3); margin-top: 5px; padding: 0 4px; }
    .msg-meta.user-meta { text-align: right; }

    .qa-input-row {
        position: sticky; bottom: 0; background: var(--bg);
        padding: 12px 0 4px; border-top: 1px solid var(--border-lt);
        margin-top: 8px;
    }
    .suggestion-chip {
        display: inline-block; padding: 5px 12px; margin: 4px;
        background: var(--purple-bg); color: var(--purple);
        border-radius: 20px; font-size: 0.8rem; cursor: pointer;
        border: 1px solid #d4d0f5; font-weight: 500;
        white-space: nowrap;
    }
    .data-badge {
        display: inline-block; padding: 3px 10px;
        background: var(--green-bg); color: var(--green);
        border-radius: 12px; font-size: 0.72rem; font-weight: 600;
        border: 1px solid #a7f3d0; margin-right: 6px;
    }
    .period-badge {
        display: inline-block; padding: 3px 10px;
        background: var(--orange-bg); color: var(--orange);
        border-radius: 12px; font-size: 0.72rem; font-weight: 600;
        border: 1px solid #fed7aa;
    }
    .empty-state {
        text-align: center; padding: 60px 20px; color: var(--text-3);
    }
    .empty-state h3 { color: var(--text-2); font-size: 1.1rem; font-weight: 600; margin-bottom: 8px; }
    .chip-grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 6px; max-width: 640px; margin: 20px auto 0; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(f"""<div class="qa-header">
        <h1>💬 Ask the Data Spine</h1>
        <p>Live BigQuery · Natural language · All clients &amp; campaigns</p>
    </div>""", unsafe_allow_html=True)

    # ── Session state ──────────────────────────────────────────────────────
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "qa_pending"   not in st.session_state: st.session_state.qa_pending   = None

    # ── Sidebar: dynamic suggestions ──────────────────────────────────────
    with st.sidebar:
        st.markdown("##### 💡 Try asking…")
        # Pull actual client list for dynamic chips
        try:
            from bigquery_data_layer import _run, TABLE_ID as _TID
            _cli_df = _run(f"SELECT DISTINCT client FROM {_TID} ORDER BY client LIMIT 10")
            _clients = _cli_df["client"].dropna().tolist()
        except Exception:
            _clients = ["Mazda", "Simplot", "Coles"]

        _suggestions = []
        if _clients:
            c0 = _clients[0]
            _suggestions += [
                f"How much did {c0} spend last week?",
                f"What was {c0}'s top platform this month?",
                f"Break down {c0} spend by objective in Q1",
            ]
        if len(_clients) > 1:
            _suggestions.append(f"Compare {_clients[0]} vs {_clients[1]} for 2025")
        _suggestions += [
            "Which client had the highest CPM last month?",
            "Show me weekly spend trends for all clients",
            "What platforms drove the most impressions this year?",
            "Which campaigns are running right now?",
        ]

        for sug in _suggestions[:8]:
            if st.button(sug, use_container_width=True, key=f"sug_{hash(sug)}"):
                st.session_state.qa_pending = sug
                st.rerun()

        st.markdown("---")
        if st.button("🗑️ Clear conversation", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
        st.caption(f"🟢 **BigQuery** · {len(_clients)} clients in dataset")

    # ── Trigger from sidebar chip ──────────────────────────────────────────
    if st.session_state.qa_pending:
        pending = st.session_state.qa_pending
        st.session_state.qa_pending = None
        with st.spinner(f"Querying BigQuery for \"{pending}\"…"):
            r = answer_question_with_llm(pending, st.session_state.chat_history)
        st.session_state.chat_history.append({"role": "user",      "content": pending})
        st.session_state.chat_history.append({"role": "assistant",  "content": r["answer"],
                                               "qe": r.get("query_explanation",""),
                                               "cost": r.get("cost", 0.0),
                                               "period": r.get("period","")})
        st.rerun()

    # ── Chat history — use st.chat_message for proper markdown rendering ──────
    if not st.session_state.chat_history:
        st.markdown(f"""<div class="empty-state">
            <div style="font-size:2.5rem;margin-bottom:12px;">🗄️</div>
            <h3>Ask anything about your media data</h3>
            <p style="font-size:0.85rem;">Connected to live BigQuery · {len(_clients)} clients · Powered by gemini-2.5-pro via Vertex AI</p>
            <p style="font-size:0.82rem;color:#94A3B8;">Use natural language dates: <em>last week</em>, <em>Q1 2025</em>, <em>January</em>, <em>this month</em></p>
            <div class="chip-grid">
        """, unsafe_allow_html=True)
        _inline_chips = [
            f"How much did {_clients[0]} spend last week?" if _clients else "Show total spend last week",
            "Which platform had the lowest CPM this month?",
            "Compare all clients for 2025",
            "What was the weekly spend trend in Q1?",
        ]
        chips_html = "".join(f'<span class="suggestion-chip">{c}</span>' for c in _inline_chips)
        st.markdown(chips_html + "</div></div>", unsafe_allow_html=True)
    else:
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])
                    # Meta row below the bubble
                    cost_txt  = f"💰 ${msg.get('cost', 0):.4f}" if msg.get("cost") else ""
                    model_txt = msg.get("qe", "")
                    meta_parts = []
                    meta_parts.append("🗄️ BigQuery · Vertex AI · gemini-2.5-pro")
                    if model_txt and "gemini" in model_txt.lower():
                        meta_parts.append(model_txt)
                    if cost_txt:
                        meta_parts.append(cost_txt)
                    st.caption("  ·  ".join(meta_parts))

    # ── Input bar ──────────────────────────────────────────────────────────
    inp_col, btn_col = st.columns([6, 1])
    with inp_col:
        dv  = st.session_state.pop("chat_input", "")
        ui  = st.chat_input(
            "Ask anything… e.g. 'How much did Mazda spend last week?' or 'Compare platforms for Q1 2025'",
        )
    with btn_col:
        pass  # chat_input handles its own submission

    # Also handle sidebar chip clicks (set via qa_pending)
    if ui:
        with st.chat_message("user"):
            st.markdown(ui)
        with st.chat_message("assistant"):
            with st.spinner("Querying BigQuery + Gemini…"):
                r = answer_question_with_llm(ui, st.session_state.chat_history)
            st.markdown(r["answer"])
            cost_txt = f"💰 ${r.get('cost', 0):.4f}" if r.get("cost") else ""
            st.caption(f"🗄️ BigQuery · Vertex AI · gemini-2.5-pro  ·  {cost_txt}")
        st.session_state.chat_history.append({"role": "user",      "content": ui})
        st.session_state.chat_history.append({"role": "assistant",  "content": r["answer"],
                                               "qe": r.get("query_explanation", ""),
                                               "cost": r.get("cost", 0.0)})

# ═══════════════════════════════════════
# MODE 2: PCA BUILDER
# ═══════════════════════════════════════
elif mode == "📊 Build PCA":
    with st.sidebar:
        st.markdown("##### 1. Date Range")
        c1, c2 = st.columns(2)
        with c1: sd = st.date_input("Start", value=date(2025, 7, 1), min_value=date(2025, 1, 1))
        with c2: ed = st.date_input("End", value=date(2026, 5, 24), min_value=sd)
        ss, es = sd.strftime("%Y-%m-%d"), ed.strftime("%Y-%m-%d")

        st.markdown("##### 2. Client")
        clients = get_clients_in_date_range(ss, es)
        co = {c["client_name"]: c["client_id"] for c in clients}
        if not co: st.warning("No clients."); st.stop()
        scn = st.selectbox("Client", list(co.keys()), label_visibility="collapsed")
        sci = co[scn]

        st.markdown("##### 3. Campaign")
        camps = get_campaigns_for_client(sci, ss, es)
        cop = {f"{c['campaign_name']}  ({c['start']} → {c['end']})": c for c in camps}
        if not cop: st.warning("No campaigns."); st.stop()
        scl = st.selectbox("Campaign", list(cop.keys()), label_visibility="collapsed")
        sc = cop[scl]

        st.markdown("##### 4. Options")
        focus = st.text_input("Focus area", placeholder="e.g. efficiency, creative, offline")
        st.markdown("---")
        gen = st.button("🚀 Generate PCA", type="primary", use_container_width=True)

    st.markdown(f"""<div class="main-header"><h1>📊 PCA Builder</h1>
    <p>{scn}  •  {sc['campaign_name']}  •  {sc['start']} → {sc['end']}</p></div>""", unsafe_allow_html=True)

    if not gen and "pca_result" not in st.session_state:
        # ── Campaign preview (live BQ) ────────────────────────────────────────
        @st.cache_data(show_spinner=False, ttl=300)
        def _pca_preview_bq(client_id, start, end):
            from bigquery_data_layer import _run as _pr, TABLE_ID as _PT
            try:
                row = _pr(f"""
                    SELECT SUM(spend) AS total_spend, SUM(impressions) AS impressions,
                           SUM(clicks) AS clicks, COUNT(DISTINCT platform) AS n_platforms,
                           MIN(date) AS date_min, MAX(date) AS date_max
                    FROM {_PT}
                    WHERE client = '{client_id}' AND date BETWEEN '{start}' AND '{end}'
                      AND spend > 0
                """).iloc[0]
                plat_df = _pr(f"""
                    SELECT ARRAY_AGG(DISTINCT platform IGNORE NULLS) AS plats
                    FROM {_PT}
                    WHERE client = '{client_id}' AND date BETWEEN '{start}' AND '{end}'
                      AND spend > 0
                """).iloc[0]
                return {
                    "spend":     float(row.total_spend or 0),
                    "imps":      int(row.impressions or 0),
                    "clicks":    int(row.clicks or 0),
                    "n_platforms": int(row.n_platforms or 0),
                    "date_min":  str(row.date_min)[:10] if row.date_min else start,
                    "date_max":  str(row.date_max)[:10] if row.date_max else end,
                    "platforms": list(plat_df.plats) if plat_df.plats else [],
                }
            except Exception:
                return {}

        with st.spinner("Loading campaign preview…"):
            _prev = _pca_preview_bq(sci, sc["start"], sc["end"])

        _spend    = _prev.get("spend", 0)
        _imps     = _prev.get("imps", 0)
        _n_plats  = _prev.get("n_platforms", 0)
        _plats    = _prev.get("platforms", [])
        _cpm      = _spend / max(_imps, 1) * 1000

        _start_dt = date.fromisoformat(sc["start"])
        _end_dt   = date.fromisoformat(sc["end"])
        _months   = max((_end_dt.year - _start_dt.year) * 12 + (_end_dt.month - _start_dt.month), 1)

        pr1, pr2, pr3, pr4 = st.columns(4)
        for col, (lbl, val, sub) in zip([pr1, pr2, pr3, pr4], [
            ("Total Spend",  f"${_spend:,.0f}",   f"{_months} month flight"),
            ("Impressions",  f"{_imps:,.0f}",      f"CPM ${_cpm:.2f}"),
            ("Platforms",    str(_n_plats),         f"{', '.join(_plats[:4])}{'…' if len(_plats) > 4 else ''}"),
            ("Flight",       f"{sc['start']} → {sc['end']}", sc["campaign_name"][:40]),
        ]):
            with col:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

        # Platform chips
        if _plats:
            chip_html = " ".join(
                f'<span style="display:inline-block;background:#EEF2FF;color:#4F46E5;'
                f'font-size:11px;font-weight:600;padding:3px 10px;border-radius:12px;margin:2px;">'
                f'{p.replace("_"," ").title()}</span>'
                for p in _plats
            )
            st.markdown(chip_html, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        st.stop()

    _cache_key = (sci, sc["campaign_id"], ss, es, ch_val, focus or "")

    if gen:
        if st.session_state.get("_pca_cache_key") == _cache_key and "pca_result" in st.session_state:
            st.toast("Same parameters — showing cached result. Change a setting to regenerate.", icon="💾")
        else:
            st.session_state.pop("pca_result", None)

            # ── Progress bar ──────────────────────────────────────────────
            _prog    = st.progress(0, text="Initialising…")
            _step_ph = st.empty()   # current step label beneath the bar

            _EXPECTED_LLM_CHARS = 22_000   # typical full PCA JSON response size

            t0 = time.time()

            # Step 1 — Data pull  (0 → 6%)
            _prog.progress(2, text="📦 Pulling campaign data…")
            sdata = assemble_pca_data(sci, sc["campaign_id"], sc["start"], sc["end"], ch_val)
            t1 = time.time()
            n_plats = len(sdata['overview'])
            _prog.progress(6, text=f"✅ {n_plats} platforms pulled  ({t1-t0:.1f}s)")

            # Step 2 — LLM narrative  (6 → 88%)
            _prog.progress(7, text="🧠 Generating narrative…  0 chars")
            _t_llm_start = time.time()

            def _llm_cb(n_chars):
                ratio   = min(n_chars / _EXPECTED_LLM_CHARS, 1.0)
                pct     = int(7 + ratio * 81)      # 7 → 88
                elapsed = time.time() - _t_llm_start
                if elapsed > 3 and n_chars > 800:
                    rate      = n_chars / elapsed
                    remaining = max(0, (_EXPECTED_LLM_CHARS - n_chars) / rate)
                    eta       = f"  •  ~{remaining:.0f}s remaining"
                else:
                    eta = ""
                _prog.progress(pct, text=f"🧠 Generating narrative…  {n_chars:,} chars  •  {elapsed:.0f}s elapsed{eta}")

            pc = generate_narrative(sdata, focus or None, _progress_ph=_llm_cb)
            t2 = time.time()
            _prog.progress(88, text=f"✅ Narrative done — {len(pc.get('slides',[]))} slides  ({t2-t1:.1f}s)")

            # Step 3 — Excel  (88 → 93%)
            _prog.progress(89, text="📗 Building data workbook…")
            xp = os.path.join(_TMPDIR, "pca_data.xlsx")
            build_pca_workbook(sdata, xp)
            t3 = time.time()
            _prog.progress(93, text=f"✅ Excel done  ({t3-t2:.1f}s)")

            # Step 4 — PPTX  (93 → 100%)
            _prog.progress(94, text="📙 Building branded presentation…")
            pptx_path = os.path.join(_TMPDIR, "pca_presentation.pptx")
            build_pptx_from_template(pc, pptx_path, scn, f"{sc['start']} → {sc['end']}")
            t4 = time.time()
            _prog.progress(100, text=f"✅ Complete — {t4-t0:.1f}s total")
            time.sleep(0.6)
            _prog.empty()
            _step_ph.empty()
            # ─────────────────────────────────────────────────────────────

            st.session_state["pca_result"]    = {"sd": sdata, "pc": pc, "xp": xp, "pptx": pptx_path, "t": {"total": round(t4-t0, 1)}}
            st.session_state["_pca_cache_key"] = _cache_key

    if "pca_result" in st.session_state:
        r=st.session_state["pca_result"]; sdata=r["sd"]; pc=r["pc"]

        if pc.get("_error"):
            st.error(f"LLM generation failed — showing placeholder data. **{pc.get('_error_msg', '')}**")

        ov=sdata["overview"]; ts=sum(o["total_spend"] for o in ov); ti=sum(o["total_impressions"] for o in ov); tc=sum(o["total_clicks"] for o in ov)

        ch_spend = {}
        for o in ov:
            ct = o.get("channel_type", "digital")
            ch_spend[ct] = ch_spend.get(ct, 0) + o["total_spend"]

        llm_cost  = pc.get("_metadata", {}).get("cost", 0.0)

        # Estimate BQ cost from data volume (mock or real)
        _n_rows_total  = (len(sdata.get('raw_data', []))
                          + len(sdata.get('weekly_trends', []))
                          + sum(len(v) for v in sdata.get('breakdowns', {}).values()))
        _bytes_scanned = _n_rows_total * 512
        bq_cost        = _bytes_scanned / 1e12 * 5.0  # $5 per TB

        # Time taken
        _total_secs = r["t"]["total"]
        _time_str   = f"{_total_secs:.1f}s" if _total_secs < 60 else f"{int(_total_secs//60)}m {int(_total_secs%60)}s"

        cols=st.columns(6)
        kpis=[("Total Spend",     f"${ts:,.0f}",          f"{len(ov)} platforms"),
              ("Channel Mix",     " | ".join(f"{k}: {v/max(ts,1)*100:.0f}%" for k,v in sorted(ch_spend.items(),key=lambda x:-x[1])), ""),
              ("Impressions",     f"{ti:,.0f}",            f"CPM ${ts/max(ti,1)*1000:.2f}"),
              ("Slides",          f"{len(pc.get('slides',[]))}","Pick & choose"),
              ("Time Taken",      _time_str,               f"LLM: {pc.get('_metadata',{}).get('tokens',0):,} tokens"),
              ("Generation Cost", f"${llm_cost+bq_cost:.4f}", f"LLM: ${llm_cost:.4f}  |  BQ est: ${bq_cost:.5f}")]
        for col,(l,v,s) in zip(cols,kpis):
            with col: st.markdown(f'<div class="kpi-card"><div class="kpi-label">{l}</div><div class="kpi-value">{v}</div><div class="kpi-sub">{s}</div></div>',unsafe_allow_html=True)

        st.markdown("---")
        dc=st.columns(4)
        with dc[0]:
            with open(r["pptx"],"rb") as f: st.download_button("📙 Presentation (.pptx)",f.read(),file_name=f"PCA_{scn}_{sc['campaign_name']}.pptx",mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",use_container_width=True)
        with dc[1]:
            with open(r["xp"],"rb") as f: st.download_button("📗 Data (.xlsx)",f.read(),file_name=f"PCA_{scn}_{sc['campaign_name']}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
        with dc[2]: st.download_button("📊 Slide JSON",json.dumps(pc,indent=2).encode(),file_name="pca_slides.json",mime="application/json",use_container_width=True)
        with dc[3]: st.download_button("📋 Source JSON",json.dumps(sdata,indent=2,default=str).encode(),file_name="pca_source.json",mime="application/json",use_container_width=True)

        st.markdown("---")
        _all_slides = pc.get("slides", [])
        with st.expander(f"📋 Slide outline  ({len(_all_slides)} slides)", expanded=False):
            _prev = [{"#": s.get("slide_number"), "Title": s.get("title",""), "Type": s.get("slide_type",""),
                      "Chart": s.get("chart_type") or "—", "Takeaway": s.get("so_what","")}
                     for s in _all_slides]
            st.dataframe(pd.DataFrame(_prev), use_container_width=True, hide_index=True,
                         column_config={"Title": st.column_config.TextColumn(width="large"),
                                        "Takeaway": st.column_config.TextColumn(width="large")})

        t1,t2,t3,t4=st.tabs(["📑 Slides","📊 Data","📖 Narrative","🔧 Debug"])
        with t1:
            st.caption("Over-generated deliberately. Pick the slides you want.")

            # Slide type colour coding
            type_colours = {"intro": "#1E1A5C", "data": "#3B2FBF", "recommendation": "#FF6B35"}
            type_labels  = {"intro": "INTRO", "data": "DATA", "recommendation": "REC"}

            for sl in pc.get("slides", []):
                stype      = sl.get("slide_type", "data")
                colour     = type_colours.get(stype, "#3B2FBF")
                type_label = type_labels.get(stype, stype.upper())
                chart_type = sl.get("chart_type", "")
                callback   = sl.get("callback_to")
                role       = sl.get("narrative_role", "")
                so_what    = sl.get("so_what", "")

                # Badges row
                chart_badge    = f'<span class="storyline-badge">📊 {chart_type}</span>' if chart_type else ""
                callback_badge = f'<span class="storyline-badge">↩ resolves slide {callback}</span>' if callback else ""
                type_badge     = f'<span style="display:inline-block;background:{colour};color:white;border-radius:20px;padding:3px 10px;font-size:10px;font-weight:700;margin-right:4px;">{type_label}</span>'

                bullets = sl.get("bullet_points", []) or ([sl.get("body")] if sl.get("body") else [])
                bullets_html = "<ul style='margin-top:10px;'>" + "".join(f"<li style='margin-bottom:6px;color:#374151;line-height:1.65;font-size:14px;'>{b}</li>" for b in bullets) + "</ul>"

                role_html    = f'<div class="narrative-role">🎭 {role}</div>' if role else ""
                sowhat_html  = f'<div class="so-what">💡 {so_what}</div>' if so_what else ""

                st.markdown(
                    f'<div class="slide-card">'
                    f'<span class="slide-num" style="background:{colour};">{sl.get("slide_number","")}</span>'
                    f'<strong style="font-size:15px;color:#0D0A2E;">{sl.get("title","")}</strong> '
                    f'{type_badge}{chart_badge}{callback_badge}'
                    f'{role_html}{sowhat_html}{bullets_html}'
                    f'</div>',
                    unsafe_allow_html=True
                )

        with t2:
            dt1,dt2,dt3,dt4=st.tabs(["Overview","Weekly","Breakdowns","Benchmarks"])
            with dt1:
                df=pd.DataFrame(ov)
                df["platform"]=df["platform"].str.replace("_"," ").str.title()
                st.dataframe(df,use_container_width=True,hide_index=True)
            with dt2: st.dataframe(pd.DataFrame(sdata["weekly_trends"]),use_container_width=True,hide_index=True)
            with dt3:
                for dim,data in sdata["breakdowns"].items():
                    label=dim.replace("by_","").replace("_"," ").title()
                    st.markdown(f"**{label}**"); st.dataframe(pd.DataFrame(data),use_container_width=True,hide_index=True)
            with dt4:
                if sdata["benchmarks"]: st.dataframe(pd.DataFrame(sdata["benchmarks"]),use_container_width=True,hide_index=True)
                else: st.info("No benchmark data for offline channels")
        with t3:
            plan = pc.get("narrative_plan", {})
            if plan:
                st.markdown(f"### {plan.get('verdict', plan.get('headline', ''))}")
                if plan.get("opening_tension"):
                    st.info(f"🪝 **Hook:** {plan['opening_tension']}")
                st.markdown(f"**Arc:** {plan.get('arc', '')}")

                key_tensions = plan.get("key_tensions", [])
                if key_tensions:
                    st.markdown("#### Tensions & Resolutions")
                    for t in key_tensions:
                        raised = t.get("raised_on_slide", "?")
                        resolved = t.get("resolved_on_slide", "?")
                        st.markdown(f"- **{t.get('tension','')}** — raised slide {raised} → resolved slide {resolved}")

                storylines = plan.get("storylines", [])
                if storylines:
                    st.markdown("#### Storylines")
                    for i, s in enumerate(storylines, 1):
                        with st.expander(f"Storyline {i}", expanded=True):
                            if isinstance(s, dict):
                                st.markdown(f"**Finding:** {s.get('finding','')}\n\n**Tension:** {s.get('tension','')}\n\n**Resolution:** {s.get('resolution','')}")
                            else:
                                st.markdown(str(s))
        with t4: st.json(r["t"]); st.json(pc)

# ═══════════════════════════════════════
# MODE 3: DASHBOARD
# ═══════════════════════════════════════
elif mode == "📈 Dashboard":
    from bigquery_data_layer import _run as _bq_run, TABLE_ID as _TABLE_ID

    @st.cache_data(show_spinner="Loading dashboard…", ttl=300)
    def _dash_load(client_id, start, end):
        """Load all dashboard data for a client + date range."""
        base = f"FROM {_TABLE_ID} WHERE client = '{client_id}' AND date BETWEEN '{start}' AND '{end}'"

        # KPI totals
        kpi = _bq_run(f"""
            SELECT SUM(spend) AS spend, SUM(impressions) AS imps,
                   SUM(clicks) AS clicks, SUM(video_completions) AS vcr,
                   SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000 AS cpm,
                   SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100 AS ctr,
                   SAFE_DIVIDE(SUM(spend), SUM(clicks)) AS cpc,
                   SAFE_DIVIDE(SUM(spend), SUM(video_completions)) AS cpcv
            {base}
        """).iloc[0].to_dict()

        def breakdown(field, label):
            try:
                df = _bq_run(f"""
                    SELECT {field} AS dim,
                           SUM(spend) AS spend, SUM(impressions) AS imps,
                           SUM(clicks) AS clicks, SUM(video_completions) AS vcr,
                           SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000 AS cpm,
                           SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100 AS ctr,
                           SAFE_DIVIDE(SUM(spend), SUM(clicks)) AS cpc
                    {base}
                    AND {field} IS NOT NULL AND TRIM({field}) != ''
                    GROUP BY {field} ORDER BY spend DESC LIMIT 30
                """)
                df = df.rename(columns={"dim": label})
                df["spend"] = df["spend"].astype(float)
                df["Spend %"] = (df["spend"] / df["spend"].sum() * 100).round(1)
                return df
            except Exception:
                return pd.DataFrame()

        # Weekly trend
        try:
            weekly = _bq_run(f"""
                SELECT DATE_TRUNC(date, WEEK(MONDAY)) AS week,
                       SUM(spend) AS spend, SUM(impressions) AS imps,
                       SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000 AS cpm
                {base}
                GROUP BY week ORDER BY week
            """)
        except Exception:
            weekly = pd.DataFrame()

        # Monthly trend
        try:
            monthly = _bq_run(f"""
                SELECT FORMAT_DATE('%Y-%m', date) AS month,
                       SUM(spend) AS spend, SUM(impressions) AS imps,
                       SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000 AS cpm
                {base}
                GROUP BY month ORDER BY month
            """)
        except Exception:
            monthly = pd.DataFrame()

        return {
            "kpi": kpi,
            "by_platform": breakdown("platform", "Platform"),
            "by_objective": breakdown("objective", "Objective"),
            "by_format": breakdown("format", "Format"),
            "by_publisher": breakdown("publisher_name", "Publisher"),
            "by_geo": breakdown("geo_target", "Geo"),
            "weekly": weekly,
            "monthly": monthly,
        }

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("##### 📅 Date Range")
        dc1, dc2 = st.columns(2)
        with dc1: dsd = st.date_input("Start", value=date(2025, 7, 1), min_value=date(2025, 1, 1), key="dash_sd")
        with dc2: ded = st.date_input("End", value=date(2026, 5, 24), min_value=dsd, key="dash_ed")
        dss, des = dsd.strftime("%Y-%m-%d"), ded.strftime("%Y-%m-%d")

        st.markdown("##### 👤 Client")
        d_clients = get_clients_in_date_range(dss, des)
        d_co = {c["client_name"]: c["client_id"] for c in d_clients}
        if not d_co:
            st.warning("No clients in range.")
            st.stop()
        _dash_prefill = st.session_state.pop("dash_prefill_client", None)
        _dash_client_list = list(d_co.keys())
        _dash_default_idx = _dash_client_list.index(_dash_prefill) if _dash_prefill and _dash_prefill in _dash_client_list else 0
        d_cn = st.selectbox("Client", _dash_client_list, index=_dash_default_idx, label_visibility="collapsed", key="dash_client")
        d_ci = d_co[d_cn]

        st.markdown("---")
        if st.button("🏆 View in Benchmarks", use_container_width=True, key="dash_to_bench"):
            st.session_state.app_mode = "🏆 Benchmarks"
            st.session_state.bench_prefill_client = d_cn
            st.rerun()
    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(f"""<div class="main-header">
        <h1>📈 Performance Dashboard</h1>
        <p>{d_cn}  •  {dss} → {des}</p>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Pulling live data…"):
        dash = _dash_load(d_ci, dss, des)

    kpi = dash["kpi"]
    spend = float(kpi.get("spend") or 0)
    imps  = float(kpi.get("imps") or 0)
    clicks = float(kpi.get("clicks") or 0)
    vcr   = float(kpi.get("vcr") or 0)
    cpm   = float(kpi.get("cpm") or 0)
    ctr   = float(kpi.get("ctr") or 0)
    cpc   = float(kpi.get("cpc") or 0)

    # ── KPI row ──────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    with k1: st.metric("💰 Total Spend",    f"${spend:,.0f}")
    with k2: st.metric("👁️ Impressions",     f"{imps:,.0f}")
    with k3: st.metric("🖱️ Clicks",          f"{clicks:,.0f}")
    with k4: st.metric("📺 Completed Views", f"{vcr:,.0f}")
    with k5: st.metric("📊 Avg CPM",         f"${cpm:.2f}")
    with k6: st.metric("📈 CTR",             f"{ctr:.3f}%" if ctr else "N/A")

    st.markdown("---")

    # ── Trend charts ─────────────────────────────────────────────────────────
    import plotly.express as px
    import plotly.graph_objects as go

    trend_tab, breakdown_tabs_container = st.columns([2, 3])

    with trend_tab:
        st.markdown("##### 📅 Spend Trend")
        monthly_df = dash["monthly"]
        if not monthly_df.empty:
            fig_trend = px.bar(
                monthly_df, x="month", y="spend",
                color_discrete_sequence=["#4338CA"],
                labels={"month": "", "spend": "Spend ($)"},
            )
            fig_trend.update_layout(
                height=220, margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white", paper_bgcolor="white",
                yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                showlegend=False,
            )
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No monthly data.")

    with breakdown_tabs_container:
        st.markdown("##### 🏢 Spend by Platform")
        plat_df = dash["by_platform"]
        if not plat_df.empty:
            fig_plat = px.bar(
                plat_df.head(10), x="spend", y="Platform", orientation="h",
                color="cpm", color_continuous_scale="Blues",
                labels={"spend": "Spend ($)", "cpm": "CPM ($)"},
                hover_data=["cpm", "ctr", "Spend %"],
            )
            fig_plat.update_layout(
                height=220, margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="white", paper_bgcolor="white",
                xaxis_tickprefix="$", xaxis_tickformat=",.0f",
                yaxis=dict(autorange="reversed"), showlegend=False,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig_plat, use_container_width=True)
        else:
            st.info("No platform data.")

    st.markdown("---")

    # ── Taxonomy tabs ─────────────────────────────────────────────────────────
    st.markdown("##### 🏷️ Taxonomy Breakdown")
    TAX_TABS = [
        ("🎯 Objective",   "by_objective",  "Objective"),
        ("📐 Format",      "by_format",     "Format"),
        ("🌐 Publisher",   "by_publisher",  "Publisher"),
        ("📍 Geography",   "by_geo",        "Geo"),
        ("📺 Platform",    "by_platform",   "Platform"),
    ]
    tab_objs = st.tabs([t[0] for t in TAX_TABS])

    for tab, (tab_label, data_key, dim_col) in zip(tab_objs, TAX_TABS):
        with tab:
            df_tax = dash[data_key]
            if df_tax.empty:
                st.info(f"No {tab_label.split(' ', 1)[1]} data for this period.")
                continue

            # Format columns
            df_show = df_tax[[dim_col, "spend", "Spend %", "imps", "cpm", "ctr", "cpc"]].copy()
            df_show.columns = [dim_col, "Spend ($)", "Spend %", "Impressions", "CPM ($)", "CTR (%)", "CPC ($)"]
            df_show["Spend ($)"]   = df_show["Spend ($)"].round(0)
            df_show["CPM ($)"]     = df_show["CPM ($)"].round(2)
            df_show["CTR (%)"]     = df_show["CTR (%)"].apply(lambda x: round(x, 3) if x else None)
            df_show["CPC ($)"]     = df_show["CPC ($)"].apply(lambda x: round(x, 2) if x else None)
            df_show["Impressions"] = df_show["Impressions"].astype("Int64")

            col_a, col_b = st.columns([2, 3])
            with col_a:
                fig = px.pie(
                    df_tax.head(8), values="spend", names=dim_col,
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.4,
                )
                fig.update_layout(height=280, margin=dict(l=0, r=0, t=10, b=0),
                                  showlegend=True, legend=dict(font=dict(size=11)))
                fig.update_traces(textposition="inside", textinfo="percent")
                st.plotly_chart(fig, use_container_width=True)

            with col_b:
                st.dataframe(
                    df_show,
                    use_container_width=True,
                    hide_index=True,
                    height=280,
                    column_config={
                        "Spend ($)":   st.column_config.NumberColumn(format="$%,.0f"),
                        "Spend %":     st.column_config.ProgressColumn("Spend %", min_value=0, max_value=100, format="%.1f%%"),
                        "Impressions": st.column_config.NumberColumn(format="%,.0f"),
                        "CPM ($)":     st.column_config.NumberColumn(format="$%.2f"),
                        "CTR (%)":     st.column_config.NumberColumn(format="%.3f"),
                        "CPC ($)":     st.column_config.NumberColumn(format="$%.2f"),
                    },
                )

    # ── Platform detail table ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("##### 📊 Platform Performance Detail")
    plat_detail = dash["by_platform"]
    if not plat_detail.empty:
        pd_show = plat_detail[["Platform", "spend", "Spend %", "imps", "cpm", "ctr", "cpc", "vcr"]].copy()
        pd_show.columns = ["Platform", "Spend ($)", "Spend %", "Impressions", "CPM ($)", "CTR (%)", "CPC ($)", "Completed Views"]
        pd_show["Spend ($)"]      = pd_show["Spend ($)"].round(0)
        pd_show["CPM ($)"]        = pd_show["CPM ($)"].round(2)
        pd_show["CTR (%)"]        = pd_show["CTR (%)"].apply(lambda x: round(x, 3) if x else None)
        pd_show["CPC ($)"]        = pd_show["CPC ($)"].apply(lambda x: round(x, 2) if x else None)
        pd_show["Impressions"]    = pd_show["Impressions"].astype("Int64")
        pd_show["Completed Views"]= pd_show["Completed Views"].astype("Int64")
        st.dataframe(
            pd_show, use_container_width=True, hide_index=True,
            column_config={
                "Spend ($)":       st.column_config.NumberColumn(format="$%,.0f"),
                "Spend %":         st.column_config.ProgressColumn("Spend %", min_value=0, max_value=100, format="%.1f%%"),
                "Impressions":     st.column_config.NumberColumn(format="%,.0f"),
                "Completed Views": st.column_config.NumberColumn(format="%,.0f"),
                "CPM ($)":         st.column_config.NumberColumn(format="$%.2f"),
                "CTR (%)":         st.column_config.NumberColumn(format="%.3f"),
                "CPC ($)":         st.column_config.NumberColumn(format="$%.2f"),
            },
        )

# ═══════════════════════════════════════
# MODE 4: SLIDE GENERATOR
# ═══════════════════════════════════════
elif mode == "⚡ Slide Generator":

    with st.sidebar:
        st.markdown("##### Try these:")
        sg_examples = [
            "3 slides on Meta performance for Coles",
            "5 slides on Mazda campaign efficiency",
            "RACV spend by platform for Q3 2025",
            "Weekly trend slides for Simplot",
            "Creative format breakdown for Hanes",
        ]
        for ex in sg_examples:
            if st.button(ex, use_container_width=True, key=f"sg_{hash(ex)}"):
                st.session_state["sg_prompt"] = ex

    st.markdown("""<div class="main-header">
        <h1>⚡ Slide Generator</h1>
        <p>Describe what you want — get slides in seconds. Quick analysis, no full PCA needed.</p>
    </div>""", unsafe_allow_html=True)

    sg_dv = st.session_state.pop("sg_prompt", "")
    sg_c1, sg_c2 = st.columns([5, 1])
    with sg_c1:
        sg_input = st.text_input(
            "What slides do you want?", value=sg_dv,
            placeholder='e.g. "3 slides on Coles performance in Q3 2025"',
            label_visibility="collapsed", key="sg_input"
        )
    with sg_c2:
        sg_go = st.button("Generate", type="primary", use_container_width=True)

    if sg_go and sg_input:
        with st.spinner("Generating…"):
            sg_result = generate_quick_slides(sg_input)
        st.session_state["sg_result"] = sg_result
        st.session_state["sg_query"]  = sg_input

    if "sg_result" not in st.session_state:
        @st.cache_data(show_spinner=False, ttl=600)
        def _sg_bq_stats():
            from bigquery_data_layer import _run as _sr, TABLE_ID as _ST
            try:
                row = _sr(f"""
                    SELECT COUNT(DISTINCT client) AS clients,
                           COUNT(DISTINCT platform) AS platforms,
                           SUM(spend) AS total_spend,
                           COUNT(DISTINCT COALESCE(NULLIF(TRIM(campaign_description),''), campaign_name)) AS campaigns
                    FROM {_ST} WHERE spend > 0
                """).iloc[0]
                return {
                    "clients":   int(row.clients or 0),
                    "platforms": int(row.platforms or 0),
                    "spend":     float(row.total_spend or 0),
                    "campaigns": int(row.campaigns or 0),
                }
            except Exception:
                return {"clients": 5, "platforms": 12, "spend": 0, "campaigns": 0}

        _sg_stats = _sg_bq_stats()

        sg1, sg2, sg3, sg4 = st.columns(4)
        for col, (lbl, val, sub) in zip([sg1, sg2, sg3, sg4], [
            ("Clients",           str(_sg_stats["clients"]),                    "Coles, Mazda, RACV, Simplot, Hanes"),
            ("Campaigns",         str(_sg_stats["campaigns"]),                  "across all clients"),
            ("Total Spend",       f"${_sg_stats['spend']/1e6:.1f}M",           "live from BigQuery"),
            ("Platforms Tracked", str(_sg_stats["platforms"]),                  "Meta, DV360, TikTok + more"),
        ]):
            with col:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

    if "sg_result" in st.session_state:
        sg_res    = st.session_state["sg_result"]
        sg_slides = sg_res.get("slides", [])
        sg_cost   = sg_res.get("_metadata", {}).get("cost", 0.0)
        sg_ctx    = sg_res.get("_resolved", {})

        # Show what data was resolved
        if sg_ctx.get("resolved"):
            camp_names = [c.get("_campaign_name", "") for c in sg_ctx.get("campaigns", [])]
            st.success(
                f"📡 **Live data resolved** — {sg_ctx['client_name']}  •  {sg_ctx['date_range']}  •  "
                + ", ".join(camp_names)
            )
        elif sg_ctx.get("client_name"):
            st.warning(f"⚠️ Matched **{sg_ctx['client_name']}** but no campaigns found in {sg_ctx.get('date_range','that period')}. Using campaign metadata only.")
        else:
            st.info("ℹ️ No specific client detected — using full dataset. Try including a client name (e.g. 'Coles', 'Mazda', 'RACV') for richer data.")

        hcol1, hcol2 = st.columns([4, 1])
        with hcol1:
            st.caption(f"**{len(sg_slides)} slides** for: *{st.session_state.get('sg_query','')}*  |  💰 ${sg_cost:.4f}")
        with hcol2:
            if sg_slides:
                sg_pptx_path = os.path.join(_TMPDIR, "quick_slides.pptx")
                build_quick_slides_pptx(sg_res, sg_pptx_path)
                with open(sg_pptx_path, "rb") as f:
                    st.download_button(
                        "📙 PPTX", f.read(),
                        file_name="quick_slides.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )

        type_colours = {"intro": "#1E1A5C", "data": "#3B2FBF", "recommendation": "#FF6B35"}

        for sl in sg_slides:
            stype   = sl.get("slide_type", "data")
            colour  = type_colours.get(stype, "#3B2FBF")
            ct      = sl.get("chart_type", "")
            so_what = sl.get("so_what", "")

            chart_badge  = f'<span class="storyline-badge">📊 {ct}</span>' if ct else ""
            sowhat_html  = f'<div class="so-what">💡 {so_what}</div>' if so_what else ""
            bullets      = sl.get("bullet_points", [])
            bullets_html = ("<ul style='margin-top:10px;'>"
                            + "".join(f"<li style='margin-bottom:6px;color:#374151;line-height:1.65;font-size:14px;'>{b}</li>" for b in bullets)
                            + "</ul>")

            st.markdown(
                f'<div class="slide-card">'
                f'<span class="slide-num" style="background:{colour};">{sl.get("slide_number","")}</span>'
                f'<strong style="font-size:15px;color:#0D0A2E;">{sl.get("title","")}</strong> {chart_badge}'
                f'{sowhat_html}{bullets_html}'
                f'</div>',
                unsafe_allow_html=True
            )

# ═══════════════════════════════════════
# MODE 5: BENCHMARKS
# ═══════════════════════════════════════
elif mode == "🏆 Benchmarks":
    import plotly.express as _bpx
    import plotly.graph_objects as _bgo
    from datetime import timedelta as _td
    from bigquery_data_layer import _run as _bq, TABLE_ID as _BT

    # ── helpers ───────────────────────────────────────────────────────────────
    @st.cache_data(show_spinner=False, ttl=300)
    def _bm_plat(client, start, end):
        """Per-platform metrics for one client in one period."""
        try:
            return _bq(f"""
                SELECT platform,
                  SUM(spend) AS spend, SUM(impressions) AS imps,
                  SUM(clicks) AS clicks, SUM(video_completions) AS vcr,
                  SAFE_DIVIDE(SUM(spend),SUM(impressions))*1000 AS cpm,
                  SAFE_DIVIDE(SUM(clicks),SUM(impressions))*100  AS ctr,
                  SAFE_DIVIDE(SUM(spend),SUM(clicks))            AS cpc,
                  SAFE_DIVIDE(SUM(spend),SUM(video_completions)) AS cpcv
                FROM {_BT}
                WHERE client='{client}' AND date BETWEEN '{start}' AND '{end}'
                  AND spend > 0
                GROUP BY platform ORDER BY spend DESC
            """)
        except Exception:
            return pd.DataFrame()

    @st.cache_data(show_spinner=False, ttl=300)
    def _bm_monthly(client, start, end):
        try:
            return _bq(f"""
                SELECT FORMAT_DATE('%Y-%m', date) AS month,
                  SUM(spend) AS spend, SUM(impressions) AS imps,
                  SUM(clicks) AS clicks,
                  SAFE_DIVIDE(SUM(spend),SUM(impressions))*1000 AS cpm,
                  SAFE_DIVIDE(SUM(clicks),SUM(impressions))*100  AS ctr,
                  SAFE_DIVIDE(SUM(spend),SUM(clicks))            AS cpc
                FROM {_BT}
                WHERE client='{client}' AND date BETWEEN '{start}' AND '{end}'
                GROUP BY month ORDER BY month
            """)
        except Exception:
            return pd.DataFrame()

    @st.cache_data(show_spinner=False, ttl=300)
    def _bm_pool(exclude_client, start, end):
        """Per-client, per-platform metrics for the pool (excluding one client)."""
        try:
            return _bq(f"""
                SELECT client, platform,
                  SUM(spend) AS spend, SUM(impressions) AS imps,
                  SUM(clicks) AS clicks, SUM(video_completions) AS vcr,
                  SAFE_DIVIDE(SUM(spend),SUM(impressions))*1000 AS cpm,
                  SAFE_DIVIDE(SUM(clicks),SUM(impressions))*100  AS ctr,
                  SAFE_DIVIDE(SUM(spend),SUM(clicks))            AS cpc,
                  SAFE_DIVIDE(SUM(spend),SUM(video_completions)) AS cpcv
                FROM {_BT}
                WHERE client != '{exclude_client}'
                  AND date BETWEEN '{start}' AND '{end}'
                  AND spend > 0
                GROUP BY client, platform ORDER BY spend DESC
            """)
        except Exception:
            return pd.DataFrame()

    @st.cache_data(show_spinner=False, ttl=300)
    def _bm_clients():
        try:
            df = _bq(f"SELECT DISTINCT client FROM {_BT} WHERE spend > 0 ORDER BY client")
            return df["client"].tolist()
        except Exception:
            return []

    def _variance_icon(var, lower_better):
        if var is None:
            return "—"
        if (lower_better and var < -5) or (not lower_better and var > 5):
            return "✅"
        if (lower_better and var > 5) or (not lower_better and var < -5):
            return "❌"
        return "➖"

    def _fmt_metric(val, met_key):
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        if met_key == "ctr":
            return round(float(val), 3)
        return round(float(val), 2)

    def _build_comparison_table(focal_df, comp_df, met_key, lower_better,
                                focal_label, comp_label):
        """
        Build a comparison dataframe: focal period vs comparison period, by platform.
        focal_df / comp_df: DataFrames with columns [platform, spend, cpm, ctr, cpc, cpcv, ...]
        Returns a display DataFrame.
        """
        rows = []
        for _, r in focal_df.sort_values("spend", ascending=False).iterrows():
            plat = r["platform"]
            fval = _fmt_metric(r.get(met_key), met_key)
            comp_row = comp_df[comp_df["platform"] == plat]
            cval = _fmt_metric(comp_row.iloc[0].get(met_key), met_key) if not comp_row.empty else None
            var = round((fval - cval) / max(abs(cval), 0.001) * 100, 1) if fval and cval else None
            rows.append({
                "Platform":    plat,
                "Spend ($)":   round(float(r["spend"]), 0),
                focal_label:   fval,
                comp_label:    cval,
                "Δ %":         var,
                "":            _variance_icon(var, lower_better),
            })
        return pd.DataFrame(rows)

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("##### 📅 Date Range")
        bm_c1, bm_c2 = st.columns(2)
        with bm_c1: bm_sd = st.date_input("Start", value=date(2025, 7, 1),  min_value=date(2025,1,1), key="bm_sd")
        with bm_c2: bm_ed = st.date_input("End",   value=date(2026, 5, 24), min_value=bm_sd,          key="bm_ed")
        bm_start, bm_end = bm_sd.strftime("%Y-%m-%d"), bm_ed.strftime("%Y-%m-%d")

        st.markdown("##### 👤 Client")
        _bm_all_clients = _bm_clients()
        if not _bm_all_clients:
            st.warning("No clients found.")
            st.stop()
        _bm_prefill = st.session_state.pop("bench_prefill_client", None)
        _bm_def_idx = _bm_all_clients.index(_bm_prefill) if _bm_prefill and _bm_prefill in _bm_all_clients else 0
        bm_client = st.selectbox("Client", _bm_all_clients, index=_bm_def_idx,
                                 label_visibility="collapsed", key="bm_client")

        st.markdown("##### 📊 Metric")
        bm_metric = st.selectbox("Metric", ["CPM ($)", "CTR (%)", "CPC ($)", "CPCV ($)"],
                                 label_visibility="collapsed", key="bm_metric")

        st.markdown("---")
        if st.button("📈 View in Dashboard", use_container_width=True, key="bm_to_dash"):
            st.session_state.app_mode = "📈 Dashboard"
            st.session_state.dash_prefill_client = bm_client
            st.rerun()

    METRIC_CFG = {
        "CPM ($)":  {"key": "cpm",  "lower_better": True,  "dollar": True},
        "CTR (%)":  {"key": "ctr",  "lower_better": False, "dollar": False},
        "CPC ($)":  {"key": "cpc",  "lower_better": True,  "dollar": True},
        "CPCV ($)": {"key": "cpcv", "lower_better": True,  "dollar": True},
    }
    mcfg         = METRIC_CFG[bm_metric]
    met_key      = mcfg["key"]
    lower_better = mcfg["lower_better"]
    met_fmt      = "$%.2f" if mcfg["dollar"] else "%.3f"
    met_fmt_col  = st.column_config.NumberColumn(format=met_fmt)

    # ── 3-month prior window ──────────────────────────────────────────────────
    prior_end   = bm_sd - _td(days=1)
    prior_start = (bm_sd.replace(day=1) - _td(days=1)).replace(day=1)
    prior_start = (prior_start.replace(day=1) - _td(days=1)).replace(day=1)
    prior_start = (prior_start.replace(day=1) - _td(days=1)).replace(day=1)
    prior_s, prior_e = prior_start.strftime("%Y-%m-%d"), prior_end.strftime("%Y-%m-%d")

    st.markdown(f"""<div class="main-header">
        <h1>🏆 Benchmarks</h1>
        <p>{bm_client}  •  {bm_metric}  •  {bm_start} → {bm_end}</p>
    </div>""", unsafe_allow_html=True)

    # ── Load data (all three periods in parallel via cache) ───────────────────
    with st.spinner("Loading benchmark data…"):
        df_focal   = _bm_plat(bm_client, bm_start, bm_end)
        df_prior3  = _bm_plat(bm_client, prior_s, prior_e)
        df_alltime = _bm_plat(bm_client, "2020-01-01", bm_end)
        df_pool    = _bm_pool(bm_client, bm_start, bm_end)
        df_monthly = _bm_monthly(bm_client, "2020-01-01", bm_end)

    if df_focal.empty:
        st.warning(f"No data for {bm_client} in {bm_start} → {bm_end}.")
        st.stop()

    # ── Summary KPI row ───────────────────────────────────────────────────────
    tot_spend = float(df_focal["spend"].sum())
    tot_imps  = float(df_focal["imps"].sum())
    tot_clk   = float(df_focal["clicks"].sum())
    avg_cpm   = tot_spend / max(tot_imps, 1) * 1000
    avg_ctr   = tot_clk  / max(tot_imps, 1) * 100
    avg_cpc   = tot_spend / max(tot_clk, 1)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.metric("💰 Total Spend",  f"${tot_spend:,.0f}")
    with k2: st.metric("👁️ Impressions",   f"{tot_imps:,.0f}")
    with k3: st.metric("📊 Avg CPM",       f"${avg_cpm:.2f}")
    with k4: st.metric("🖱️ CTR",           f"{avg_ctr:.3f}%")
    with k5: st.metric("💡 Avg CPC",       f"${avg_cpc:.2f}")

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_own, tab_3mo, tab_pool = st.tabs([
        "📊 vs Own Activity",
        "📅 vs Last 3 Months",
        "🌐 vs Portfolio Pool",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — vs OWN ACTIVITY (all-time client average, excl. selected period)
    # ══════════════════════════════════════════════════════════════════════════
    with tab_own:
        st.caption(f"Comparing **{bm_start} → {bm_end}** against {bm_client}'s own all-time performance (excluding this period)")

        # All-time excluding selected window
        df_excl = df_alltime[
            ~((df_alltime["platform"].isin(df_focal["platform"])) & False)  # keep all rows
        ].copy()
        # Recompute "all-time excl. selected period" via BQ
        @st.cache_data(show_spinner=False, ttl=300)
        def _excl_period(client, sel_start, sel_end):
            try:
                return _bq(f"""
                    SELECT platform,
                      SUM(spend) AS spend, SUM(impressions) AS imps,
                      SUM(clicks) AS clicks, SUM(video_completions) AS vcr,
                      SAFE_DIVIDE(SUM(spend),SUM(impressions))*1000 AS cpm,
                      SAFE_DIVIDE(SUM(clicks),SUM(impressions))*100  AS ctr,
                      SAFE_DIVIDE(SUM(spend),SUM(clicks))            AS cpc,
                      SAFE_DIVIDE(SUM(spend),SUM(video_completions)) AS cpcv
                    FROM {_BT}
                    WHERE client='{client}'
                      AND (date < '{sel_start}' OR date > '{sel_end}')
                      AND spend > 0
                    GROUP BY platform ORDER BY spend DESC
                """)
            except Exception:
                return pd.DataFrame()

        df_own_hist = _excl_period(bm_client, bm_start, bm_end)

        cmp_own = _build_comparison_table(
            df_focal, df_own_hist, met_key, lower_better,
            focal_label=f"Selected ({bm_start[:7]}→{bm_end[:7]})",
            comp_label="Own All-time Avg",
        )

        if not cmp_own.empty:
            # KPIs
            has_both = cmp_own.dropna(subset=[f"Selected ({bm_start[:7]}→{bm_end[:7]})", "Own All-time Avg"])
            n_beat = (has_both[""] == "✅").sum()
            n_miss = (has_both[""] == "❌").sum()
            ka, kb, kc = st.columns(3)
            with ka: st.metric("Platforms Compared", len(has_both))
            with kb: st.metric("Outperforming Own Avg", f"{n_beat} platforms")
            with kc: st.metric("Underperforming Own Avg", f"{n_miss} platforms")

            st.markdown("---")

            # Chart
            focal_col = f"Selected ({bm_start[:7]}→{bm_end[:7]})"
            chart_data = cmp_own.dropna(subset=[focal_col, "Own All-time Avg"]).set_index("Platform")[[focal_col, "Own All-time Avg"]]
            if not chart_data.empty:
                fig = _bgo.Figure()
                fig.add_bar(name=focal_col,       x=chart_data.index, y=chart_data[focal_col],       marker_color="#4338CA")
                fig.add_bar(name="Own All-time Avg", x=chart_data.index, y=chart_data["Own All-time Avg"], marker_color="#A5B4FC")
                fig.update_layout(
                    barmode="group", height=320,
                    margin=dict(l=0, r=0, t=10, b=0),
                    plot_bgcolor="white", paper_bgcolor="white",
                    legend=dict(orientation="h", y=1.08),
                    yaxis_title=bm_metric,
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.markdown("##### Platform Detail")
            st.dataframe(cmp_own, use_container_width=True, hide_index=True,
                column_config={
                    "Spend ($)": st.column_config.NumberColumn(format="$%,.0f"),
                    focal_col:   met_fmt_col,
                    "Own All-time Avg": met_fmt_col,
                    "Δ %":       st.column_config.NumberColumn(format="%.1f%%"),
                    "":          st.column_config.TextColumn(width="small"),
                })
        else:
            st.info("Not enough historical data outside the selected period.")

        # Monthly trend
        if not df_monthly.empty and met_key in df_monthly.columns:
            st.markdown("---")
            st.markdown(f"##### 📅 Monthly {bm_metric} Trend (all time)")
            mo_agg = df_monthly.groupby("month").apply(
                lambda g: pd.Series({
                    "spend": g["spend"].sum(),
                    "imps":  g["imps"].sum(),
                    "clicks": g["clicks"].sum(),
                })
            ).reset_index()
            mo_agg["cpm"] = mo_agg["spend"] / mo_agg["imps"].clip(lower=1) * 1000
            mo_agg["ctr"] = mo_agg["clicks"] / mo_agg["imps"].clip(lower=1) * 100
            mo_agg["cpc"] = mo_agg["spend"] / mo_agg["clicks"].clip(lower=1)
            fig_mo = _bpx.bar(mo_agg, x="month", y=met_key,
                              color_discrete_sequence=["#4338CA"],
                              labels={"month": "", met_key: bm_metric})
            fig_mo.update_layout(height=240, margin=dict(l=0,r=0,t=10,b=0),
                                 plot_bgcolor="white", paper_bgcolor="white")
            # shade the selected window
            fig_mo.add_vrect(
                x0=bm_start[:7], x1=bm_end[:7],
                fillcolor="#F05C2C", opacity=0.12,
                annotation_text="Selected", annotation_position="top left",
                line_width=0,
            )
            st.plotly_chart(fig_mo, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — vs LAST 3 MONTHS
    # ══════════════════════════════════════════════════════════════════════════
    with tab_3mo:
        st.caption(f"Comparing **{bm_start} → {bm_end}** against **{prior_s} → {prior_e}** (3 months prior)")

        cmp_3mo = _build_comparison_table(
            df_focal, df_prior3, met_key, lower_better,
            focal_label=f"Selected period",
            comp_label=f"Prior 3 months",
        )

        if df_prior3.empty:
            st.info(f"No data for {bm_client} in the prior 3-month window ({prior_s} → {prior_e}).")
        elif not cmp_3mo.empty:
            has_both = cmp_3mo.dropna(subset=["Selected period", "Prior 3 months"])
            n_beat = (has_both[""] == "✅").sum()
            n_miss = (has_both[""] == "❌").sum()
            ka, kb, kc, kd = st.columns(4)
            with ka: st.metric("Selected period",      f"{bm_start} → {bm_end}")
            with kb: st.metric("Prior 3-month window", f"{prior_s} → {prior_e}")
            with kc: st.metric("Platforms improving",  f"{n_beat}")
            with kd: st.metric("Platforms declining",  f"{n_miss}")

            st.markdown("---")

            chart_data = cmp_3mo.dropna(subset=["Selected period", "Prior 3 months"]).set_index("Platform")[["Selected period", "Prior 3 months"]]
            if not chart_data.empty:
                fig = _bgo.Figure()
                fig.add_bar(name="Selected period",  x=chart_data.index, y=chart_data["Selected period"],  marker_color="#4338CA")
                fig.add_bar(name="Prior 3 months",   x=chart_data.index, y=chart_data["Prior 3 months"],   marker_color="#A5B4FC")
                fig.update_layout(
                    barmode="group", height=320,
                    margin=dict(l=0, r=0, t=10, b=0),
                    plot_bgcolor="white", paper_bgcolor="white",
                    legend=dict(orientation="h", y=1.08),
                    yaxis_title=bm_metric,
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.markdown("##### Platform Detail")
            st.dataframe(cmp_3mo, use_container_width=True, hide_index=True,
                column_config={
                    "Spend ($)":       st.column_config.NumberColumn(format="$%,.0f"),
                    "Selected period": met_fmt_col,
                    "Prior 3 months":  met_fmt_col,
                    "Δ %":             st.column_config.NumberColumn(format="%.1f%%"),
                    "":                st.column_config.TextColumn(width="small"),
                })

            # Monthly side-by-side trend
            if not df_monthly.empty:
                st.markdown("---")
                st.markdown(f"##### 📅 Monthly {bm_metric} — Selected vs Prior 3 Months")
                @st.cache_data(show_spinner=False, ttl=300)
                def _mo_prior(client, ps, pe):
                    try:
                        return _bq(f"""
                            SELECT FORMAT_DATE('%Y-%m', date) AS month,
                              SAFE_DIVIDE(SUM(spend),SUM(impressions))*1000 AS cpm,
                              SAFE_DIVIDE(SUM(clicks),SUM(impressions))*100  AS ctr,
                              SAFE_DIVIDE(SUM(spend),SUM(clicks))            AS cpc
                            FROM {_BT}
                            WHERE client='{client}' AND date BETWEEN '{ps}' AND '{pe}'
                            GROUP BY month ORDER BY month
                        """)
                    except Exception:
                        return pd.DataFrame()

                df_mo_prior = _mo_prior(bm_client, prior_s, prior_e)
                df_mo_focal_only = df_monthly[
                    (df_monthly["month"] >= bm_start[:7]) & (df_monthly["month"] <= bm_end[:7])
                ].groupby("month").apply(
                    lambda g: pd.Series({"spend": g["spend"].sum(), "imps": g["imps"].sum(), "clicks": g["clicks"].sum()})
                ).reset_index()
                df_mo_focal_only["cpm"] = df_mo_focal_only["spend"] / df_mo_focal_only["imps"].clip(lower=1) * 1000
                df_mo_focal_only["ctr"] = df_mo_focal_only["clicks"] / df_mo_focal_only["imps"].clip(lower=1) * 100
                df_mo_focal_only["cpc"] = df_mo_focal_only["spend"] / df_mo_focal_only["clicks"].clip(lower=1)

                fig_cmp = _bgo.Figure()
                if not df_mo_focal_only.empty and met_key in df_mo_focal_only.columns:
                    fig_cmp.add_scatter(x=df_mo_focal_only["month"], y=df_mo_focal_only[met_key],
                                        mode="lines+markers", name="Selected period", line_color="#4338CA")
                if not df_mo_prior.empty and met_key in df_mo_prior.columns:
                    fig_cmp.add_scatter(x=df_mo_prior["month"], y=df_mo_prior[met_key],
                                        mode="lines+markers", name="Prior 3 months", line_color="#A5B4FC",
                                        line=dict(dash="dot"))
                fig_cmp.update_layout(height=240, margin=dict(l=0,r=0,t=10,b=0),
                                      plot_bgcolor="white", paper_bgcolor="white",
                                      legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_cmp, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — vs PORTFOLIO POOL
    # ══════════════════════════════════════════════════════════════════════════
    with tab_pool:
        st.caption(f"Comparing **{bm_client}** against all other clients in the portfolio — same period {bm_start} → {bm_end}")

        if df_pool.empty:
            st.info("No pool data available for this period.")
        else:
            pool_clients = df_pool["client"].nunique()

            # Pool average by platform (spend-weighted)
            pool_by_plat = df_pool.groupby("platform").apply(
                lambda g: pd.Series({
                    "spend": g["spend"].sum(),
                    "imps":  g["imps"].sum(),
                    "clicks": g["clicks"].sum(),
                    "vcr":   g["vcr"].sum(),
                    "cpm":   g["spend"].sum() / max(g["imps"].sum(), 1) * 1000,
                    "ctr":   g["clicks"].sum() / max(g["imps"].sum(), 1) * 100,
                    "cpc":   g["spend"].sum() / max(g["clicks"].sum(), 1),
                    "cpcv":  g["spend"].sum() / max(g["vcr"].sum(), 1),
                    "n_clients": g["client"].nunique(),
                })
            ).reset_index()

            cmp_pool = _build_comparison_table(
                df_focal, pool_by_plat, met_key, lower_better,
                focal_label=bm_client,
                comp_label="Pool Avg",
            )

            has_both = cmp_pool.dropna(subset=[bm_client, "Pool Avg"])
            n_beat = (has_both[""] == "✅").sum()
            n_miss = (has_both[""] == "❌").sum()

            ka, kb, kc, kd = st.columns(4)
            with ka: st.metric("Pool size",           f"{pool_clients} clients")
            with kb: st.metric("Platforms compared",  len(has_both))
            with kc: st.metric("Beating pool avg",    f"{n_beat} platforms")
            with kd: st.metric("Behind pool avg",     f"{n_miss} platforms")

            st.markdown("---")

            chart_data = has_both.set_index("Platform")[[bm_client, "Pool Avg"]]
            if not chart_data.empty:
                fig = _bgo.Figure()
                fig.add_bar(name=bm_client,   x=chart_data.index, y=chart_data[bm_client],  marker_color="#4338CA")
                fig.add_bar(name="Pool Avg",  x=chart_data.index, y=chart_data["Pool Avg"],  marker_color="#D1D5DB")
                fig.update_layout(
                    barmode="group", height=320,
                    margin=dict(l=0, r=0, t=10, b=0),
                    plot_bgcolor="white", paper_bgcolor="white",
                    legend=dict(orientation="h", y=1.08),
                    yaxis_title=bm_metric,
                )
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.markdown("##### Platform Detail")
            st.dataframe(cmp_pool, use_container_width=True, hide_index=True,
                column_config={
                    "Spend ($)":  st.column_config.NumberColumn(format="$%,.0f"),
                    bm_client:    met_fmt_col,
                    "Pool Avg":   met_fmt_col,
                    "Δ %":        st.column_config.NumberColumn(format="%.1f%%"),
                    "":           st.column_config.TextColumn(width="small"),
                })

            # Per-client breakdown expander
            with st.expander("🔍 Individual client breakdown", expanded=False):
                st.caption("Each client's performance on platforms they share with " + bm_client)
                focal_plats_set = set(df_focal["platform"].tolist())
                pool_detail = df_pool[df_pool["platform"].isin(focal_plats_set)].copy()
                pool_detail = pool_detail[["client", "platform", "spend", met_key]].copy()
                pool_detail.columns = ["Client", "Platform", "Spend ($)", bm_metric]
                pool_detail["Spend ($)"] = pool_detail["Spend ($)"].round(0)
                if met_key == "ctr":
                    pool_detail[bm_metric] = pool_detail[bm_metric].round(3)
                else:
                    pool_detail[bm_metric] = pool_detail[bm_metric].round(2)
                st.dataframe(pool_detail.sort_values("Spend ($)", ascending=False),
                             use_container_width=True, hide_index=True,
                             column_config={
                                 "Spend ($)": st.column_config.NumberColumn(format="$%,.0f"),
                                 bm_metric:   met_fmt_col,
                             })

# ═══════════════════════════════════════
# MODE 6: WEEKLY MEET
# ═══════════════════════════════════════
elif mode == "📅 Weekly Meet":
    import plotly.express as _wpx
    import plotly.graph_objects as _wgo
    from datetime import timedelta as _wdelta
    from bigquery_data_layer import _run as _wq, TABLE_ID as _WT, get_weekly_meet_data

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("##### Client")

        @st.cache_data(show_spinner=False, ttl=300)
        def _wm_clients():
            try:
                df = _wq(f"SELECT DISTINCT client FROM {_WT} WHERE spend > 0 ORDER BY client")
                return df["client"].tolist()
            except Exception:
                return []

        _wm_client_list = _wm_clients()
        if not _wm_client_list:
            st.warning("No clients found in BigQuery.")
            st.stop()

        wm_client = st.selectbox("Client", _wm_client_list, label_visibility="collapsed", key="wm_client")

        st.markdown("##### Week ending")
        _today       = date.today()
        _default_end = _today - _wdelta(days=1)   # yesterday by default

        wm_end = st.date_input("Week ending", value=_default_end,
                               label_visibility="collapsed", key="wm_end")

        # Always 7-day window ending on the selected day
        wm_start = wm_end - _wdelta(days=6)
        wm_ss = wm_start.strftime("%Y-%m-%d")
        wm_es = wm_end.strftime("%Y-%m-%d")
        st.caption(f"{wm_ss} → {wm_es}  •  prev: {(wm_start - _wdelta(days=7)).strftime('%m/%d')} → {(wm_start - _wdelta(days=1)).strftime('%m/%d')}")

        st.markdown("---")
        wm_gen = st.button("🗓️ Generate Brief", type="primary", use_container_width=True)
        if st.button("🗑️ Clear", use_container_width=True):
            for k in ["wm_data", "wm_brief", "wm_client_key"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""<div class="main-header">
        <h1>📅 Weekly Meet</h1>
        <p>{wm_client}  •  {wm_ss} → {wm_es}  •  WIP meeting brief</p>
    </div>""", unsafe_allow_html=True)

    _wm_key = (wm_client, wm_ss, wm_es)

    if wm_gen:
        if st.session_state.get("wm_client_key") == _wm_key and "wm_brief" in st.session_state:
            st.toast("Same parameters — showing cached brief.", icon="💾")
        else:
            st.session_state.pop("wm_data",  None)
            st.session_state.pop("wm_brief", None)

            with st.spinner("Pulling weekly data from BigQuery…"):
                _wm_raw = get_weekly_meet_data(wm_client, wm_ss, wm_es)
            st.session_state["wm_data"] = _wm_raw

            with st.spinner("Generating meeting brief with Gemini…"):
                _wm_brief = generate_weekly_meet(_wm_raw, wm_client)
            st.session_state["wm_brief"]      = _wm_brief
            st.session_state["wm_client_key"] = _wm_key

    # ── Empty state ───────────────────────────────────────────────────────────
    if "wm_brief" not in st.session_state:
        wm_e1, wm_e2, wm_e3 = st.columns(3)
        for _col, (_ico, _h, _b) in zip(
            [wm_e1, wm_e2, wm_e3],
            [
                ("📊", "Per-channel summary", "Spend, CPM, CTR, impressions — with WoW commentary for each platform."),
                ("🎯", "Next week actions", "Specific, prioritised recommendations your planner can act on immediately."),
                ("💬", "Client talking points", "The questions your client will ask — answered before they ask them."),
            ]
        ):
            with _col:
                st.markdown(
                    f'<div class="kpi-card" style="text-align:center;">'
                    f'<div style="font-size:28px;margin-bottom:8px;">{_ico}</div>'
                    f'<div class="kpi-label">{_h}</div>'
                    f'<div style="font-size:12px;color:var(--text-2);margin-top:6px;">{_b}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        st.markdown("<div style='margin-top:24px;text-align:center;color:var(--text-3);font-size:13px;'>Select a client and week, then click <strong>Generate Brief</strong></div>", unsafe_allow_html=True)
        st.stop()

    # ── Render brief ──────────────────────────────────────────────────────────
    _wm_d = st.session_state["wm_data"]
    _wm_b = st.session_state["wm_brief"]
    _tot  = _wm_d.get("totals", {})

    if _wm_b.get("_error"):
        st.error(f"LLM error — showing rule-based summary. **{_wm_b.get('_error_msg','')}**")

    # ── Headline banner ───────────────────────────────────────────────────────
    _headline = _wm_b.get("headline", "")
    if _headline:
        st.markdown(
            f'<div style="background:var(--navy);color:#fff;padding:16px 24px;border-radius:var(--r-md);'
            f'font-size:18px;font-weight:700;letter-spacing:-0.3px;margin-bottom:16px;">'
            f'📋 {_headline}</div>',
            unsafe_allow_html=True
        )

    # ── KPI row ───────────────────────────────────────────────────────────────
    _spend     = _tot.get("spend", 0)
    _imps      = _tot.get("impressions", 0)
    _cpm       = _tot.get("cpm")
    _ctr       = _tot.get("ctr")
    _wow_spend = _tot.get("spend_wow_pct")
    _lw_spend  = _tot.get("lw_spend", 0)
    _n_plats   = _tot.get("n_platforms", 0)
    _llm_cost  = _wm_b.get("_metadata", {}).get("cost", 0.0)

    def _wow_badge(val, lower_better=False):
        if val is None: return ""
        good = (val < 0) if lower_better else (val > 0)
        colour = "var(--green)" if good else "var(--red)"
        arrow  = "▲" if val > 0 else "▼"
        return (f'<span style="font-size:10px;font-weight:700;color:{colour};'
                f'background:{"var(--green-bg)" if good else "var(--red-bg)"};'
                f'padding:2px 6px;border-radius:4px;margin-left:4px;">{arrow} {abs(val):.1f}%</span>')

    wm_k1, wm_k2, wm_k3, wm_k4, wm_k5 = st.columns(5)
    for _col, (_lbl, _val, _sub) in zip(
        [wm_k1, wm_k2, wm_k3, wm_k4, wm_k5],
        [
            ("Total Spend",   f"${_spend:,.0f}" + _wow_badge(_wow_spend), f"vs ${_lw_spend:,.0f} last week"),
            ("Impressions",   f"{_imps:,.0f}",     f"CPM ${_cpm:.2f}" if _cpm else ""),
            ("CTR",           f"{_ctr:.3f}%" if _ctr else "—", "click-through rate"),
            ("Platforms",     str(_n_plats), f"{wm_ss} → {wm_es}"),
            ("Generation Cost", f"${_llm_cost:.4f}", "Gemini · Vertex AI"),
        ]
    ):
        with _col:
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{_lbl}</div>'
                f'<div class="kpi-value">{_val}</div>'
                f'<div class="kpi-sub">{_sub}</div></div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    wm_t1, wm_t2, wm_t3, wm_t4, wm_t5 = st.tabs(["📊 Channel Summaries", "📋 Campaign Summary", "🎯 Next Week Actions", "💬 Talking Points", "🔢 Raw Data"])

    # ── TAB 1: Channel Summaries ───────────────────────────────────────────────
    with wm_t1:
        _overall = _wm_b.get("overall_summary", "")
        if _overall:
            st.markdown(
                f'<div style="background:var(--purple-bg);border-left:3px solid var(--purple);'
                f'padding:14px 18px;border-radius:0 var(--r-sm) var(--r-sm) 0;margin-bottom:20px;'
                f'font-size:14px;line-height:1.7;color:var(--text-1);">'
                f'<strong>Overall</strong> — {_overall}</div>',
                unsafe_allow_html=True
            )

        # Build WoW map for badge display
        _wow_map = {w["platform"]: w for w in _wm_d.get("wow", [])}

        _status_cfg = {
            "strong":   ("#ECFDF5", "#059669", "✅ STRONG"),
            "on_track": ("#EEF2FF", "#4338CA", "🟦 ON TRACK"),
            "watch":    ("#FFFBEB", "#D97706", "⚠️ WATCH"),
            "concern":  ("#FEF2F2", "#DC2626", "🔴 CONCERN"),
        }

        channels = _wm_b.get("channels", [])

        # Two-column grid
        _left_cols = channels[::2]
        _right_cols = channels[1::2]

        for _pair in zip(_left_cols, _right_cols + [None]):
            _col_a, _col_b = st.columns(2)
            for _col_widget, _ch in [(_col_a, _pair[0]), (_col_b, _pair[1])]:
                if _ch is None:
                    continue
                with _col_widget:
                    _pl       = _ch.get("platform", "")
                    _status   = _ch.get("status", "on_track")
                    _bg, _clr, _slbl = _status_cfg.get(_status, _status_cfg["on_track"])
                    _summary  = _ch.get("summary", "")
                    _wow_note = _ch.get("wow_note", "")
                    _rec      = _ch.get("recommendation", "")

                    # Find this platform in this_week data for numbers
                    _tw = next((r for r in _wm_d.get("this_week", []) if r["platform"] == _pl), {})
                    _sp   = _tw.get("spend", 0)
                    _cpm_ = _tw.get("cpm")
                    _ctr_ = _tw.get("ctr")
                    _imps_= _tw.get("impressions", 0)

                    _metrics_html = (
                        f'<span style="font-size:11px;color:var(--text-2);margin-right:12px;">💰 ${_sp:,.0f}</span>'
                        f'<span style="font-size:11px;color:var(--text-2);margin-right:12px;">'
                        f'{"CPM $"+str(_cpm_) if _cpm_ else ""}</span>'
                        f'<span style="font-size:11px;color:var(--text-2);">'
                        f'{"CTR "+str(_ctr_)+"%" if _ctr_ else ""}</span>'
                    )

                    _wow_html = (
                        '<div style="font-size:12px;color:var(--text-2);font-style:italic;margin-bottom:8px;">📈 '
                        + _wow_note + '</div>'
                    ) if _wow_note else ""
                    _rec_html = (
                        '<div style="background:var(--navy);color:#fff;border-radius:6px;'
                        'padding:8px 12px;font-size:12px;font-weight:500;">→ '
                        + _rec + '</div>'
                    ) if _rec else ""
                    st.markdown(
                        f'<div style="background:{_bg};border:1px solid {_clr}33;border-radius:var(--r-md);'
                        f'padding:16px;margin-bottom:12px;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                        f'<strong style="font-size:15px;color:var(--text-1);">{_pl}</strong>'
                        f'<span style="font-size:10px;font-weight:700;color:{_clr};background:{_clr}18;'
                        f'padding:3px 8px;border-radius:4px;">{_slbl}</span>'
                        f'</div>'
                        f'<div style="margin-bottom:8px;">{_metrics_html}</div>'
                        f'<div style="font-size:13px;color:var(--text-1);line-height:1.65;margin-bottom:8px;">{_summary}</div>'
                        f'{_wow_html}{_rec_html}'
                        f'</div>',
                        unsafe_allow_html=True
                    )

        # Daily spend trend chart
        _dd = _wm_d.get("daily_trend", [])
        if _dd:
            st.markdown("##### Daily Spend Trend")
            _dd_df = pd.DataFrame(_dd)
            _fig_daily = _wpx.bar(
                _dd_df, x="day", y="spend", color="platform",
                labels={"spend": "Spend ($)", "day": "Day", "platform": "Platform"},
                color_discrete_sequence=["#4338CA","#F05C2C","#059669","#D97706","#6D63E8","#94A3B8","#0C0A28","#FC8181"],
                template="plotly_white",
            )
            _fig_daily.update_layout(
                height=280, margin=dict(l=0, r=0, t=20, b=0),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
                xaxis=dict(gridcolor="#F0F2F6"), yaxis=dict(gridcolor="#F0F2F6"),
            )
            st.plotly_chart(_fig_daily, use_container_width=True)

    # ── TAB 2: Campaign Summary ────────────────────────────────────────────────
    with wm_t2:
        _camps_tw = _wm_d.get("campaigns_this_week", [])
        _camp_llm  = _wm_b.get("campaign_summaries", [])
        _camp_llm_map = {c.get("campaign", ""): c for c in _camp_llm}

        if not _camps_tw:
            st.info("No campaign data found for this week.")
        else:
            # LLM summaries if available
            if _camp_llm:
                st.markdown(
                    '<div style="font-size:13px;color:var(--text-2);margin-bottom:16px;">'
                    'AI-generated one-liner per campaign based on this week\'s performance.</div>',
                    unsafe_allow_html=True
                )
                _cs_status_cfg = {
                    "strong":   ("#ECFDF5", "#059669", "✅"),
                    "on_track": ("#EEF2FF", "#4338CA", "🟦"),
                    "watch":    ("#FFFBEB", "#D97706", "⚠️"),
                    "concern":  ("#FEF2F2", "#DC2626", "🔴"),
                }
                for _cs in _camp_llm:
                    _cn    = _cs.get("campaign", "")
                    _cst   = _cs.get("status", "on_track")
                    _col   = _cs_status_cfg.get(_cst, _cs_status_cfg["on_track"])
                    _liner = _cs.get("one_liner", "")
                    _watch = _cs.get("watch", "")
                    # Find matching data row
                    _cd = next((c for c in _camps_tw if c["campaign"] == _cn), {})
                    _cs_sp  = _cd.get("spend", 0)
                    _cs_wow = _cd.get("spend_wow_pct")
                    _wow_badge_html = ""
                    if _cs_wow is not None:
                        _wgood  = _cs_wow > 0
                        _wclr   = "var(--green)" if _wgood else "var(--red)"
                        _wbg    = "var(--green-bg)" if _wgood else "var(--red-bg)"
                        _warrow = "▲" if _wgood else "▼"
                        _wow_badge_html = (
                            f'<span style="font-size:10px;font-weight:700;color:{_wclr};'
                            f'background:{_wbg};padding:2px 6px;border-radius:4px;margin-left:6px;">'
                            f'{_warrow} {abs(_cs_wow):.1f}% WoW</span>'
                        )
                    st.markdown(
                        f'<div style="background:{_col[0]};border-left:3px solid {_col[1]};'
                        f'border-radius:0 var(--r-sm) var(--r-sm) 0;padding:12px 16px;margin-bottom:8px;">'
                        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">'
                        f'<span style="font-size:11px;">{_col[2]}</span>'
                        f'<strong style="font-size:13px;color:var(--text-1);">{_cn}</strong>'
                        f'<span style="font-size:11px;color:var(--text-2);">· ${_cs_sp:,.0f}</span>'
                        f'{_wow_badge_html}</div>'
                        f'<div style="font-size:13px;color:var(--text-1);line-height:1.6;">{_liner}</div>'
                        + (f'<div style="font-size:12px;color:var(--text-2);font-style:italic;margin-top:4px;">👀 Watch: {_watch}</div>' if _watch else "")
                        + '</div>',
                        unsafe_allow_html=True
                    )
            else:
                st.info("Enable LLM to get AI campaign summaries.")

            # Full campaign data table
            st.markdown("##### All Campaigns This Week")
            _camps_df = pd.DataFrame([
                {
                    "Campaign":      c["campaign"],
                    "Platforms":     c.get("platforms", ""),
                    "Spend (TW)":    c["spend"],
                    "Spend (LW)":    c.get("lw_spend"),
                    "WoW %":         c.get("spend_wow_pct"),
                    "Impressions":   c["impressions"],
                    "CPM ($)":       c.get("cpm"),
                    "CTR (%)":       c.get("ctr"),
                    "CPC ($)":       c.get("cpc"),
                }
                for c in _camps_tw
            ])
            st.dataframe(
                _camps_df, use_container_width=True, hide_index=True,
                column_config={
                    "Campaign":    st.column_config.TextColumn(width="large"),
                    "Spend (TW)":  st.column_config.NumberColumn("Spend TW ($)",  format="$%,.0f"),
                    "Spend (LW)":  st.column_config.NumberColumn("Spend LW ($)",  format="$%,.0f"),
                    "WoW %":       st.column_config.NumberColumn("WoW %",         format="%.1f%%"),
                    "Impressions": st.column_config.NumberColumn("Impressions",   format="%,.0f"),
                    "CPM ($)":     st.column_config.NumberColumn("CPM ($)",       format="$%.2f"),
                    "CTR (%)":     st.column_config.NumberColumn("CTR (%)",       format="%.3f"),
                    "CPC ($)":     st.column_config.NumberColumn("CPC ($)",       format="$%.2f"),
                }
            )

    # ── TAB 3: Next Week Actions ───────────────────────────────────────────────
    with wm_t3:
        _actions = _wm_b.get("next_week_actions", [])
        if not _actions:
            st.info("No actions generated.")
        else:
            _priority_cfg = {
                "HIGH":   ("#FEF2F2", "#DC2626"),
                "MEDIUM": ("#FFFBEB", "#D97706"),
                "LOW":    ("#F0FDF4", "#059669"),
            }
            for _act in _actions:
                _pri = str(_act.get("priority", "MEDIUM")).upper()
                _abg, _aclr = _priority_cfg.get(_pri, _priority_cfg["MEDIUM"])
                _apl  = _act.get("platform", "")
                _atxt = _act.get("action", "")
                _arat = _act.get("rationale", "")
                st.markdown(
                    f'<div style="background:{_abg};border-left:4px solid {_aclr};'
                    f'border-radius:0 var(--r-sm) var(--r-sm) 0;padding:14px 18px;margin-bottom:10px;">'
                    f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
                    f'<span style="font-size:10px;font-weight:800;color:{_aclr};background:{_aclr}22;'
                    f'padding:2px 8px;border-radius:4px;">{_pri}</span>'
                    f'<span style="font-size:13px;font-weight:600;color:var(--text-1);">{_apl}</span>'
                    f'</div>'
                    f'<div style="font-size:14px;color:var(--text-1);font-weight:500;line-height:1.6;margin-bottom:6px;">{_atxt}</div>'
                    + (f'<div style="font-size:12px;color:var(--text-2);font-style:italic;">{_arat}</div>' if _arat else "")
                    + '</div>',
                    unsafe_allow_html=True
                )

    # ── TAB 4: Talking Points ──────────────────────────────────────────────────
    with wm_t4:
        st.markdown(
            '<div style="font-size:13px;color:var(--text-2);margin-bottom:16px;">'
            'Topics your client is likely to raise — with context and a suggested framing for each.</div>',
            unsafe_allow_html=True
        )
        _tps = _wm_b.get("talking_points", [])
        if not _tps:
            st.info("No talking points generated.")
        else:
            for _i, _tp in enumerate(_tps, 1):
                _topic   = _tp.get("topic", "")
                _context = _tp.get("context", "")
                _sq      = _tp.get("suggested_question", "")
                with st.expander(f"**{_i}. {_topic}**", expanded=(_i == 1)):
                    if _context:
                        st.markdown(f"**Context:** {_context}")
                    if _sq:
                        st.markdown(
                            f'<div style="background:#EEF2FF;border-left:3px solid var(--purple);'
                            f'padding:10px 14px;border-radius:0 6px 6px 0;margin-top:8px;'
                            f'font-size:13px;color:var(--text-1);">'
                            f'💬 <em>{_sq}</em></div>',
                            unsafe_allow_html=True
                        )

    # ── TAB 5: Raw Data ────────────────────────────────────────────────────────
    with wm_t5:
        _rd1, _rd2 = st.tabs(["This Week vs Last Week", "Top Campaigns"])

        with _rd1:
            # Merge this_week + last_week + wow into one table
            _tw_map = {r["platform"]: r for r in _wm_d.get("this_week", [])}
            _lw_map = {r["platform"]: r for r in _wm_d.get("last_week", [])}
            _ww_map = {r["platform"]: r for r in _wm_d.get("wow", [])}
            _all_plats = sorted(set(list(_tw_map.keys()) + list(_lw_map.keys())))
            _merge_rows = []
            for _pl in _all_plats:
                _tw_r = _tw_map.get(_pl, {})
                _lw_r = _lw_map.get(_pl, {})
                _ww_r = _ww_map.get(_pl, {})
                _merge_rows.append({
                    "Platform":         _pl,
                    "Spend (TW)":       _tw_r.get("spend"),
                    "Spend (LW)":       _lw_r.get("spend"),
                    "Spend WoW %":      _ww_r.get("spend_var"),
                    "Imps (TW)":        _tw_r.get("impressions"),
                    "CPM (TW)":         _tw_r.get("cpm"),
                    "CPM WoW %":        _ww_r.get("cpm_var"),
                    "CTR (TW)":         _tw_r.get("ctr"),
                    "CTR WoW %":        _ww_r.get("ctr_var"),
                    "CPC (TW)":         _tw_r.get("cpc"),
                })
            _merge_df = pd.DataFrame(_merge_rows)
            st.dataframe(
                _merge_df, use_container_width=True, hide_index=True,
                column_config={
                    "Spend (TW)":  st.column_config.NumberColumn("Spend (TW)",  format="$%,.0f"),
                    "Spend (LW)":  st.column_config.NumberColumn("Spend (LW)",  format="$%,.0f"),
                    "Spend WoW %": st.column_config.NumberColumn("Spend WoW %", format="%.1f%%"),
                    "Imps (TW)":   st.column_config.NumberColumn("Imps (TW)",   format="%,.0f"),
                    "CPM (TW)":    st.column_config.NumberColumn("CPM (TW)",    format="$%.2f"),
                    "CPM WoW %":   st.column_config.NumberColumn("CPM WoW %",   format="%.1f%%"),
                    "CTR (TW)":    st.column_config.NumberColumn("CTR (TW)",    format="%.3f%%"),
                    "CTR WoW %":   st.column_config.NumberColumn("CTR WoW %",   format="%.1f%%"),
                    "CPC (TW)":    st.column_config.NumberColumn("CPC (TW)",    format="$%.2f"),
                }
            )

        with _rd2:
            _tc_df = pd.DataFrame(_wm_d.get("top_campaigns", []))
            if not _tc_df.empty:
                st.dataframe(
                    _tc_df, use_container_width=True, hide_index=True,
                    column_config={
                        "spend":       st.column_config.NumberColumn("Spend ($)",   format="$%,.0f"),
                        "impressions": st.column_config.NumberColumn("Impressions", format="%,.0f"),
                        "cpm":         st.column_config.NumberColumn("CPM ($)",     format="$%.2f"),
                        "ctr":         st.column_config.NumberColumn("CTR (%)",     format="%.3f"),
                    }
                )
            else:
                st.info("No campaign data found for this week.")

    # ── Cost / generation footnote ────────────────────────────────────────────
    _wm_tokens = _wm_b.get("_metadata", {}).get("tokens", 0)
    _wm_cost   = _wm_b.get("_metadata", {}).get("cost",   0.0)
    _wm_model  = st.session_state.get("settings_llm_model", "gemini-2.5-pro")
    st.markdown(
        f'<div style="margin-top:24px;padding:10px 16px;background:var(--border-lt);'
        f'border-radius:var(--r-sm);font-size:11px;color:var(--text-3);text-align:right;">'
        f'💰 Brief generated by <strong>Vertex AI · {_wm_model}</strong> · '
        f'{_wm_tokens:,} tokens · <strong>${_wm_cost:.4f} USD</strong> LLM cost'
        f'</div>',
        unsafe_allow_html=True
    )


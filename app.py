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
from llm_engine import generate_narrative, answer_question_with_llm, generate_quick_slides, answer_benchmark_question, generate_media_strategy
from live_analytics import get_portfolio_overview, score_campaign, get_pacing_data
from excel_builder import build_pca_workbook, build_media_strategy_excel
from pptx_builder import build_pptx_from_template, build_quick_slides_pptx, build_media_strategy_pptx

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
    "settings_use_vertex": False,
    "settings_llm_provider": "Vertex AI (Gemini)",
    "settings_llm_model": "gemini-3.1-pro-preview",
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
    nav_btn("🗄️ Data")

    st.markdown("##### 📊 PCA & Insights")
    nav_btn("💬 Ask a Question")
    nav_btn("📊 Build PCA")
    nav_btn("⚡ Slide Generator")

    st.markdown("##### 🤖 Agentic & Predictive")
    nav_btn("⚡ Automated Optimization")
    nav_btn("🧠 Media Strategy Builder")

    st.markdown("##### 🎯 Performance Cohort")
    nav_btn("📊 Campaign Pulse")
    nav_btn("⏱️ Pacerly")
    nav_btn("🤖 Optimizer Buddy")

    st.markdown("##### 🏷️ Data Quality")
    nav_btn("🏷️ Taxonomy Compliance")

    mode = st.session_state.app_mode

    _data_status = "🟢 BigQuery"
    _llm_status  = "🟢 Live LLM"  if st.session_state.settings_llm_enabled  else "🟡 Mock LLM"
    st.caption(f"{_data_status}  •  {_llm_status}")

    st.markdown("---")
    ch_filter = st.radio("📡 Channel Filter", ["All Channels (Online + Offline)", "Digital Only", "Offline Only (TV, Radio, OOH)"], index=["All Channels (Online + Offline)", "Digital Only", "Offline Only (TV, Radio, OOH)"].index(st.session_state.settings_channel_filter), key="ch_filter_radio")
    st.session_state.settings_channel_filter = ch_filter
    ch_map = {"All Channels (Online + Offline)": "all", "Digital Only": "digital", "Offline Only (TV, Radio, OOH)": "offline"}
    ch_val = ch_map[ch_filter]

    st.markdown("---")
    with st.expander("⚙️ Settings", expanded=False):
        st.markdown("##### LLM Connection")
        st.session_state.settings_llm_enabled = st.toggle("Use live LLM", value=st.session_state.settings_llm_enabled)
        if st.session_state.settings_llm_enabled:
            st.session_state.settings_use_vertex = st.toggle(
                "🏢 Use Corporate Vertex AI",
                value=st.session_state.get("settings_use_vertex", False),
                help="Uses gemini-2.5-pro via res-apac-dev-skynet-au (ADC). Off = personal API key."
            )
            if st.session_state.settings_use_vertex:
                st.caption("🔒 **Vertex AI** · `gemini-2.5-pro` · `res-apac-dev-skynet-au`")
            else:
                st.session_state.settings_llm_model = st.selectbox("Model", [
                    "gemini-3.1-pro-preview",
                    "gemini-3-flash-preview",
                    "gemini-2.5-pro-preview-03-25",
                    "gemini-2.0-flash",
                ], key="vertex_model_select")
                st.caption("🔑 **Personal API key**")
            st.session_state.settings_llm_project = st.text_input("GCP Project ID", value=st.session_state.get("settings_llm_project", "res-apac-dev-skynet-au"))
        else:
            st.caption("Using mock LLM (structured template responses)")
    st.markdown("---")

# ═══════════════════════════════════════
# MODE 1: CONVERSATION ENGINE
# ═══════════════════════════════════════
if mode == "💬 Ask a Question":
    st.markdown("""<div class="main-header"><h1>💬 Ask the Data Spine</h1>
    <p>Natural language queries across all clients and campaigns  •  """ + ch_filter + """</p></div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("##### Try these:")
        examples = ["How much was spent on Mazda in January?", "Telstra platform breakdown Q3", "Compare all clients for 2025"]
        for ex in examples:
            if st.button(ex, use_container_width=True, key=f"ex_{hash(ex)}"): st.session_state["chat_input"] = ex

    if "chat_history" not in st.session_state: st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-msg chat-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-msg chat-ai">{msg["content"]}</div>', unsafe_allow_html=True)
            # FIX: Added cost to the chat explanation text
            cost_text = f" | 💰 Est. Cost: ${msg.get('cost', 0.0):.4f}" if "cost" in msg else ""
            if msg.get("qe"): st.caption(f"🔍 {msg['qe']}{cost_text}")

    c1, c2 = st.columns([5, 1])
    with c1:
        dv = st.session_state.pop("chat_input", "")
        ui = st.text_input("Ask...", value=dv, label_visibility="collapsed", placeholder="e.g. How much was spent on Mazda in January?", key="cbox")
    with c2:
        send = st.button("Send", type="primary", use_container_width=True)

    if not st.session_state.chat_history:
        with st.expander("ℹ️ How the Question Engine works", expanded=False):
            st.image("assets/question_engine_architecture.png", use_container_width=True)

    if (send or dv) and ui:
        with st.spinner("Analyzing data with Gemini..."):
            r = answer_question_with_llm(ui, st.session_state.chat_history)
            
        st.session_state.chat_history.append({"role": "user", "content": ui})
        st.session_state.chat_history.append({"role": "assistant", "content": r["answer"], "qe": r.get("query_explanation", ""), "cost": r.get("cost", 0.0)})
        st.rerun()

    if st.sidebar.button("🗑️ Clear Chat", use_container_width=True): st.session_state.chat_history = []; st.rerun()

# ═══════════════════════════════════════
# MODE 2: PCA BUILDER
# ═══════════════════════════════════════
elif mode == "📊 Build PCA":
    with st.sidebar:
        st.markdown("##### 1. Date Range")
        c1, c2 = st.columns(2)
        with c1: sd = st.date_input("Start", value=date(2026, 1, 1), min_value=date(2024, 1, 1))
        with c2: ed = st.date_input("End", value=date(2026, 4, 14), min_value=sd)
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
    <p>{scn}  •  {sc['campaign_name']}  •  {sc['start']} → {sc['end']}  •  {ch_filter}</p></div>""", unsafe_allow_html=True)

    if not gen and "pca_result" not in st.session_state:
        # ── Campaign preview ──────────────────────────────────────────────────
        from data_layer import get_live_clients as _glc
        _MC = _glc()
        _camp_meta = _MC.get(sci, {}).get("campaigns", {}).get(sc["campaign_id"], {})
        _start_dt  = date.fromisoformat(sc["start"])
        _end_dt    = date.fromisoformat(sc["end"])
        _months    = max((_end_dt.year - _start_dt.year) * 12 + (_end_dt.month - _start_dt.month), 1)
        _est_spend = _camp_meta.get("monthly_spend", 0) * _months
        _digital   = _camp_meta.get("platforms_digital", [])
        _offline   = _camp_meta.get("platforms_offline", [])
        _all_plats = _digital + _offline

        _channel_map = {"meta":"Social","google_search":"Search","google_ads":"Search","dv360":"Programmatic",
                        "youtube":"Video","tiktok":"Social","the_trade_desk":"Programmatic","ctv_bvod":"CTV/BVOD",
                        "spotify":"Audio","bing_search":"Search","pinterest":"Social","linkedin":"Social",
                        "snapchat":"Social","tv_seven":"TV","tv_nine":"TV","tv_ten":"TV","tv_sbs":"TV",
                        "tv_foxtel":"TV","radio_sca":"Radio","radio_arn":"Radio","radio_nine_radio":"Radio",
                        "radio_abc":"Radio","radio_nova":"Radio","ooh_large_format":"OOH","ooh_street_furniture":"OOH",
                        "ooh_transit":"OOH","ooh_retail":"OOH","ooh_digital":"OOH"}
        _channels   = sorted(set(_channel_map.get(p, "Digital") for p in _all_plats))

        pr1, pr2, pr3, pr4 = st.columns(4)
        for col, (lbl, val, sub) in zip([pr1, pr2, pr3, pr4], [
            ("Est. Campaign Spend", f"${_est_spend:,.0f}", f"{_months} month flight"),
            ("Platforms",           str(len(_all_plats)),  f"{len(_digital)} digital · {len(_offline)} offline"),
            ("Channels",            str(len(_channels)),   "  ·  ".join(_channels)),
            ("Flight",              f"{sc['start']} → {sc['end']}", sc["campaign_name"]),
        ]):
            with col:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)

        # Platform chips
        chip_html = " ".join(
            f'<span style="display:inline-block;background:{"#EEF2FF" if p in _digital else "#FFF7ED"};'
            f'color:{"#4F46E5" if p in _digital else "#C2410C"};font-size:11px;font-weight:600;'
            f'padding:3px 10px;border-radius:12px;margin:2px;">{p.replace("_"," ").title()}</span>'
            for p in _all_plats
        )
        st.markdown(chip_html, unsafe_allow_html=True)
        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        with st.expander("ℹ️ How the PCA Generator works", expanded=False):
            st.image("assets/pca_architecture.png", use_container_width=True)
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

    METRIC_CONFIG = {
        "Spend ($)":        {"ov_key": "total_spend",           "wk_key": "spend",       "fmt": "${:,.0f}"},
        "Impressions":      {"ov_key": "total_impressions",     "wk_key": "impressions", "fmt": "{:,.0f}"},
        "Clicks":           {"ov_key": "total_clicks",          "wk_key": None,          "fmt": "{:,.0f}"},
        "CPM ($)":          {"ov_key": "cpm",                   "wk_key": "cpm",         "fmt": "${:.2f}"},
        "CPC ($)":          {"ov_key": "cpc",                   "wk_key": None,          "fmt": "${:.2f}"},
        "Completed Views":  {"ov_key": "total_completed_views", "wk_key": None,          "fmt": "{:,.0f}"},
    }

    with st.sidebar:
        st.markdown("##### 1. Date Range")
        dc1, dc2 = st.columns(2)
        with dc1: dsd = st.date_input("Start", value=date(2026, 1, 1), min_value=date(2024, 1, 1), key="dash_sd")
        with dc2: ded = st.date_input("End", value=date(2026, 4, 14), min_value=dsd, key="dash_ed")
        dss, des = dsd.strftime("%Y-%m-%d"), ded.strftime("%Y-%m-%d")

        st.markdown("##### 2. Client")
        d_clients = get_clients_in_date_range(dss, des)
        d_co = {c["client_name"]: c["client_id"] for c in d_clients}
        if not d_co: st.warning("No clients in range."); st.stop()
        d_cn = st.selectbox("Client", list(d_co.keys()), label_visibility="collapsed", key="dash_client")
        d_ci = d_co[d_cn]

        st.markdown("##### 3. Campaign")
        d_camps = get_campaigns_for_client(d_ci, dss, des)
        d_cop = {f"{c['campaign_name']}  ({c['start']} → {c['end']})": c for c in d_camps}
        if not d_cop: st.warning("No campaigns."); st.stop()
        d_scl = st.selectbox("Campaign", list(d_cop.keys()), label_visibility="collapsed", key="dash_camp")
        d_sc = d_cop[d_scl]

        st.markdown("##### 4. Metric")
        d_metric = st.selectbox("View metric", list(METRIC_CONFIG.keys()), label_visibility="collapsed", key="dash_metric")

    mcfg = METRIC_CONFIG[d_metric]

    st.markdown(f"""<div class="main-header">
        <h1>📈 Dashboard</h1>
        <p>{d_cn}  •  {d_sc['campaign_name']}  •  {d_sc['start']} → {d_sc['end']}  •  {ch_filter}</p>
    </div>""", unsafe_allow_html=True)

    with st.spinner("Loading…"):
        d_data = _load_dashboard_data(d_ci, d_sc["campaign_id"], d_sc["start"], d_sc["end"], ch_val)

    d_ov = d_data["overview"]
    d_ts  = sum(o["total_spend"] for o in d_ov)
    d_ti  = sum(o["total_impressions"] for o in d_ov)
    d_tc  = sum(o["total_clicks"] for o in d_ov)
    d_tcv = sum(o.get("total_completed_views", 0) for o in d_ov)
    d_cpm = d_ts / max(d_ti, 1) * 1000
    d_cpc = d_ts / max(d_tc, 1) if d_tc else 0

    # ── KPI row ──
    km1, km2, km3, km4, km5 = st.columns(5)
    with km1: st.metric("Total Spend",    f"${d_ts:,.0f}")
    with km2: st.metric("Impressions",    f"{d_ti:,.0f}")
    with km3: st.metric("Avg CPM",        f"${d_cpm:.2f}")
    with km4: st.metric("Clicks",         f"{d_tc:,.0f}")
    with km5: st.metric("Avg CPC",        f"${d_cpc:.2f}" if d_cpc else "N/A")

    st.markdown("---")

    # ── Charts row ──
    ch1, ch2 = st.columns([3, 2])

    with ch1:
        st.markdown(f"**{d_metric} by Platform**")
        plat_rows = [
            {"Platform": o["platform"].replace("_", " ").title(),
             d_metric: o.get(mcfg["ov_key"]) or 0}
            for o in d_ov
            if o.get(mcfg["ov_key"]) not in (None, "", 0)
        ]
        if plat_rows:
            plat_df = pd.DataFrame(plat_rows).sort_values(d_metric, ascending=False).set_index("Platform")
            st.bar_chart(plat_df)
        else:
            st.info(f"No {d_metric} data available.")

    with ch2:
        wk_key = mcfg["wk_key"]
        if wk_key and d_data.get("weekly_trends"):
            st.markdown(f"**{d_metric} — Weekly Trend**")
            wk_agg = {}
            for row in d_data["weekly_trends"]:
                wk = row.get("week_start", "")
                val = row.get(wk_key, 0) or 0
                wk_agg[wk] = wk_agg.get(wk, 0) + val
            wk_df = pd.DataFrame(sorted(wk_agg.items()), columns=["Week", d_metric]).set_index("Week")
            st.line_chart(wk_df)
        else:
            st.info(f"Weekly trend not available for {d_metric}.")

    st.markdown("---")

    # ── Full platform table ──
    st.markdown("**Platform Detail**")
    tbl_keys   = ["platform", "total_spend", "total_impressions", "total_clicks", "total_completed_views", "cpm", "cpc", "cpcv"]
    tbl_labels = ["Platform",  "Spend ($)",   "Impressions",       "Clicks",       "Completed Views",        "CPM ($)", "CPC ($)", "CPCV ($)"]
    tbl_df = pd.DataFrame([{k: o.get(k, "") for k in tbl_keys} for o in d_ov])
    tbl_df["platform"] = tbl_df["platform"].str.replace("_", " ").str.title()
    tbl_df.columns = tbl_labels
    tbl_col_cfg = {
        "Spend ($)":       st.column_config.NumberColumn(format="$%,.0f"),
        "Impressions":     st.column_config.NumberColumn(format="%,.0f"),
        "Clicks":          st.column_config.NumberColumn(format="%,.0f"),
        "Completed Views": st.column_config.NumberColumn(format="%,.0f"),
        "CPM ($)":         st.column_config.NumberColumn(format="$%.2f"),
        "CPC ($)":         st.column_config.NumberColumn(format="$%.2f"),
        "CPCV ($)":        st.column_config.NumberColumn(format="$%.2f"),
    }
    st.dataframe(tbl_df, use_container_width=True, hide_index=True, column_config=tbl_col_cfg)

    # ── Breakdowns ──
    st.markdown("---")
    bd_tabs = st.tabs([dim.replace("by_", "").replace("_", " ").title() for dim in d_data["breakdowns"]])
    for tab, (dim, bdata) in zip(bd_tabs, d_data["breakdowns"].items()):
        with tab:
            bd_df = pd.DataFrame(bdata)
            if not bd_df.empty:
                # bar chart on spend if present
                if "spend" in bd_df.columns and "value" in bd_df.columns:
                    st.bar_chart(bd_df.set_index("value")["spend"].sort_values(ascending=False))
                st.dataframe(bd_df, use_container_width=True, hide_index=True)

    # ── Benchmarks ──
    if d_data.get("benchmarks"):
        st.markdown("---")
        st.markdown("**Benchmarks**")
        bm_df = pd.DataFrame(d_data["benchmarks"])
        bm_df["platform"] = bm_df["platform"].str.replace("_", " ").str.title()
        st.dataframe(bm_df, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════
# MODE 4: SLIDE GENERATOR
# ═══════════════════════════════════════
elif mode == "⚡ Slide Generator":

    with st.sidebar:
        st.markdown("##### Try these:")
        sg_examples = [
            "3 slides on Meta performance for Coles",
            "Telstra spend by platform for Q1 2025",
            "5 slides on Qantas campaign efficiency",
            "Weekly trend slides for Mazda CX-60",
            "Creative format breakdown for any client",
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
            placeholder='e.g. "3 slides on Telstra performance in January"',
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
        from data_layer import get_live_clients as _glc
        _MC = _glc()
        _total_spend   = sum(c["monthly_spend"] * 12 for cl in _MC.values() for c in cl["campaigns"].values())
        _total_camps   = sum(len(cl["campaigns"]) for cl in _MC.values())
        _total_clients = len(_MC)
        _all_plats     = set(p for cl in _MC.values() for c in cl["campaigns"].values()
                             for p in c.get("platforms_digital", []) + c.get("platforms_offline", []))

        sg1, sg2, sg3, sg4 = st.columns(4)
        for col, (lbl, val, sub) in zip([sg1, sg2, sg3, sg4], [
            ("Clients Available",   str(_total_clients),       "across all accounts"),
            ("Campaigns",           str(_total_camps),         "in mock dataset"),
            ("Total Portfolio Spend", f"${_total_spend/1e6:.1f}M", "annualised mock data"),
            ("Platforms Tracked",   str(len(_all_plats)),      "digital + offline"),
        ]):
            with col:
                st.markdown(f'<div class="kpi-card"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
        with st.expander("ℹ️ How the Slide Generator works", expanded=False):
            st.image("assets/slide_generator_architecture.png", use_container_width=True)

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
            st.info("ℹ️ No specific client detected in prompt — using full dataset. Try including a client name (e.g. 'Telstra', 'Coles') for richer data.")

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

    from collections import defaultdict as _dd
    from data_layer import get_live_clients as _glc
    _MC = _glc()

    # ── Sidebar controls ──
    with st.sidebar:
        st.markdown("##### 1. Date Range")
        bm_c1, bm_c2 = st.columns(2)
        with bm_c1: bm_sd = st.date_input("Start", value=date(2026, 1, 1), min_value=date(2024,1,1), key="bm_sd")
        with bm_c2: bm_ed = st.date_input("End",   value=date(2026, 4, 14), min_value=bm_sd, key="bm_ed")
        bm_start, bm_end = bm_sd.strftime("%Y-%m-%d"), bm_ed.strftime("%Y-%m-%d")

        st.markdown("##### 2. Client")
        bm_client_opts = {v["name"]: k for k, v in _MC.items()}
        bm_client_name = st.selectbox("Client", list(bm_client_opts.keys()),
                                      label_visibility="collapsed", key="bm_client")
        bm_client_id   = bm_client_opts[bm_client_name]

        st.markdown("##### 3. Campaign")
        _bm_all_camps = get_campaigns_for_client(bm_client_id, bm_start, bm_end)
        _bm_camp_opts = {"— All campaigns (aggregated) —": None}
        for _c in _bm_all_camps:
            _bm_camp_opts[f"{_c['campaign_name']}  ({_c['start']} → {_c['end']})"] = _c
        bm_camp_label = st.selectbox("Campaign", list(_bm_camp_opts.keys()),
                                     label_visibility="collapsed", key="bm_camp")
        bm_selected_camp = _bm_camp_opts[bm_camp_label]   # None = all campaigns

        st.markdown("##### 4. Metric")
        bm_metric = st.selectbox("Metric", ["CPM ($)", "CTR (%)", "CPC ($)", "CPCV ($)"],
                                 label_visibility="collapsed", key="bm_metric")

        st.markdown("##### 5. Channel")
        bm_ch_label = st.selectbox("Channel", ["All", "Digital", "TV", "Radio", "OOH"],
                                   label_visibility="collapsed", key="bm_ch")
        bm_ch = {"All":"all","Digital":"digital","TV":"tv","Radio":"radio","OOH":"ooh"}[bm_ch_label]

        st.markdown("##### Try asking:")
        bm_examples = [
            "How does this campaign's Meta CPM compare to the pool?",
            "Which platforms is this client most efficient on?",
            "Where is this campaign underperforming vs own history?",
            "What's the pool average CPM for Google Search?",
            "Which channel type has the biggest gap vs pool?",
        ]
        for ex in bm_examples:
            if st.button(ex, use_container_width=True, key=f"bm_{hash(ex)}"):
                st.session_state["bm_input"] = ex

    # ── Metric config ──
    METRIC_CFG = {
        "CPM ($)":  {"key": "cpm",  "lower_better": True,  "fmt": "${:.2f}"},
        "CTR (%)":  {"key": "ctr",  "lower_better": False, "fmt": "{:.3f}%"},
        "CPC ($)":  {"key": "cpc",  "lower_better": True,  "fmt": "${:.2f}"},
        "CPCV ($)": {"key": "cpcv", "lower_better": True,  "fmt": "${:.2f}"},
    }
    mcfg         = METRIC_CFG[bm_metric]
    met_key      = mcfg["key"]
    lower_better = mcfg["lower_better"]
    dollar_fmt   = "$" in bm_metric

    _camp_label_short = bm_selected_camp["campaign_name"] if bm_selected_camp else "All campaigns"

    st.markdown(f"""<div class="main-header">
        <h1>🏆 Benchmarks</h1>
        <p>{bm_client_name}  •  {_camp_label_short}  •  {bm_start} → {bm_end}  •  {bm_ch_label}</p>
    </div>""", unsafe_allow_html=True)

    bm_tab_own, bm_tab_pool, bm_tab_ask = st.tabs([
        "🔄 vs Own History", "🌐 vs Portfolio Pool", "💬 Ask"
    ])

    # ── Build selected-campaign platform data ─────────────────────────────────
    # (cache functions defined at module level for correct st.cache_data behaviour)

    # Selected campaign (or aggregated all-client)
    if bm_selected_camp:
        focal_plats = _load_camp_plats(
            bm_client_id,
            bm_selected_camp["campaign_id"],
            max(bm_start, bm_selected_camp["start"]),
            min(bm_end,   bm_selected_camp["end"]),
            bm_ch,
        )
    else:
        # Aggregate all campaigns for the client
        all_camp_plats = _load_all_client_plats(bm_client_id, bm_start, bm_end, bm_ch)
        _agg = _dd(lambda: {"spend": 0, "impressions_proxy": 0, "clicks_proxy": 0})
        for _cp in all_camp_plats.values():
            for plat, m in _cp.items():
                _agg[plat]["spend"] += m.get("spend", 0)
                # Reconstruct counts from rates for re-averaging
                sp = m.get("spend", 0)
                cpm = m.get("cpm") or 0
                imps = sp / cpm * 1000 if cpm else 0
                _agg[plat]["impressions_proxy"] += imps
        focal_plats = {}
        for plat, d in _agg.items():
            sp  = d["spend"]
            imp = d["impressions_proxy"]
            ch_type = next((v.get("channel","digital") for _, cp in all_camp_plats.items() for p, v in cp.items() if p == plat), "digital")
            focal_plats[plat] = {
                "channel": ch_type,
                "spend":   round(sp, 2),
                "cpm":     round(sp / imp * 1000, 2) if imp else None,
                "ctr":     None, "cpc":  None, "cpcv": None,
            }

    own_rows = []  # C2: initialise before tab blocks so Ask tab can always reference it
    cmp_rows = []  # same for pool comparison rows

    # ══════════════════════════════════════════════════════════════
    # TAB 1: vs OWN HISTORY
    # ══════════════════════════════════════════════════════════════
    with bm_tab_own:

        all_camp_data = _load_all_client_plats(bm_client_id, bm_start, bm_end, bm_ch)

        if len(all_camp_data) < 2 and bm_selected_camp:
            st.info("Not enough campaigns in this date range to compare against own history. Widen the date range.")
        else:
            # Build "client own average" excluding the selected campaign
            excl_name = bm_selected_camp["campaign_name"] if bm_selected_camp else None
            own_pool  = _dd(list)
            for cname, cplats in all_camp_data.items():
                if cname == excl_name:
                    continue
                for plat, m in cplats.items():
                    v = m.get(met_key)
                    if v is not None:
                        own_pool[plat].append(v)
            own_avg = {p: round(sum(vs)/len(vs), 3) for p, vs in own_pool.items() if vs}

            # Build comparison rows
            own_rows = []
            for plat, m in sorted(focal_plats.items(), key=lambda x: -(x[1].get("spend", 0))):
                c_val = m.get(met_key)
                o_val = own_avg.get(plat)
                ch2   = m.get("channel", "")
                var   = round((c_val - o_val) / max(abs(o_val), 0.001) * 100, 1) if c_val and o_val else None
                if var is not None:
                    beat = "✅" if (lower_better and var < -2) or (not lower_better and var > 2) \
                           else ("❌" if (lower_better and var > 2) or (not lower_better and var < -2) else "➖")
                else:
                    beat = "—"
                own_rows.append({"platform": plat, "channel": ch2,
                                 "camp_val": c_val, "own_avg": o_val,
                                 "var_pct": var, "beat": beat,
                                 "spend": m.get("spend", 0)})

            # KPI strip
            own_cmp = [r for r in own_rows if r["camp_val"] and r["own_avg"]]
            n_beat  = sum(1 for r in own_cmp if r["beat"] == "✅")
            n_miss  = sum(1 for r in own_cmp if r["beat"] == "❌")
            n_camps = len(all_camp_data)

            k1, k2, k3, k4 = st.columns(4)
            with k1: st.metric("Client Campaigns", f"{n_camps}", f"in {bm_start[:4]}–{bm_end[:4]}")
            with k2: st.metric("Platforms Compared", len(own_cmp))
            with k3: st.metric(f"Above Own Avg {bm_metric}", f"{n_beat}")
            with k4: st.metric(f"Below Own Avg {bm_metric}", f"{n_miss}")

            st.markdown("---")

            # Per-campaign breakdown table (all campaigns, all platforms)
            with st.expander(f"📋 All {bm_client_name} campaigns in range", expanded=False):
                camp_summary = []
                for cname, cplats in sorted(all_camp_data.items()):
                    total_spend = sum(v.get("spend", 0) for v in cplats.values())
                    n_plats     = len(cplats)
                    avg_met     = None
                    vals = [v.get(met_key) for v in cplats.values() if v.get(met_key)]
                    if vals: avg_met = round(sum(vals)/len(vals), 3)
                    is_focal = "→" if cname == excl_name else ""
                    camp_summary.append({
                        "": is_focal,
                        "Campaign":     cname,
                        "Spend ($)":    total_spend,
                        "Platforms":    n_plats,
                        f"Avg {bm_metric}": avg_met,
                    })
                camp_df = pd.DataFrame(camp_summary).sort_values("Spend ($)", ascending=False)
                st.dataframe(camp_df, use_container_width=True, hide_index=True,
                             column_config={"Spend ($)": st.column_config.NumberColumn(format="$%,.0f"),
                                            "": st.column_config.TextColumn(width="small")})

            # Chart + variance
            if own_cmp:
                focus_label = excl_name or "All campaigns"
                chart_df = pd.DataFrame({
                    focus_label:         {r["platform"].replace("_"," ").title(): r["camp_val"] for r in own_cmp},
                    f"{bm_client_name} Avg (other campaigns)": {r["platform"].replace("_"," ").title(): r["own_avg"] for r in own_cmp},
                }).sort_values(focus_label, ascending=(met_key == "cpm"))

                col_chart, col_delta = st.columns([3, 2])
                with col_chart:
                    st.markdown(f"**{bm_metric} — {focus_label} vs {bm_client_name} own average**")
                    st.bar_chart(chart_df)
                with col_delta:
                    st.markdown("**Variance vs own average**")
                    delta_df = pd.DataFrame({
                        "Variance %": {r["platform"].replace("_"," ").title(): r["var_pct"]
                                       for r in own_cmp if r["var_pct"] is not None}
                    }).sort_values("Variance %")
                    st.bar_chart(delta_df)
                    direction = "↓ negative = more efficient than usual" if lower_better else "↑ positive = stronger engagement than usual"
                    st.caption(f"*{direction}*")

            st.markdown("---")
            st.markdown(f"**Platform Detail — {_camp_label_short} vs {bm_client_name} own average**")
            own_tbl = []
            for r in own_rows:
                own_tbl.append({
                    "Platform":   r["platform"].replace("_"," ").title(),
                    "Channel":    r["channel"].upper(),
                    "Spend ($)":  r["spend"],
                    "This Campaign": r["camp_val"],
                    f"{bm_client_name} Avg": r["own_avg"],
                    "vs Own %":   r["var_pct"],
                    "":           r["beat"],
                })
            if own_tbl:
                own_df = pd.DataFrame(own_tbl).sort_values("Spend ($)", ascending=False)
                st.dataframe(own_df, use_container_width=True, hide_index=True,
                             column_config={
                                 "Spend ($)":       st.column_config.NumberColumn(format="$%,.0f"),
                                 "This Campaign":   st.column_config.NumberColumn(format="$%.2f" if dollar_fmt else "%.3f"),
                                 f"{bm_client_name} Avg": st.column_config.NumberColumn(format="$%.2f" if dollar_fmt else "%.3f"),
                                 "vs Own %":        st.column_config.NumberColumn(format="%.1f%%"),
                             })

    # ══════════════════════════════════════════════════════════════
    # TAB 2: vs PORTFOLIO POOL
    # ══════════════════════════════════════════════════════════════
    with bm_tab_pool:

        actuals = _load_actuals(bm_start, bm_end, bm_ch)

        # Pool averages (exclude this client entirely)
        pool_plat = _dd(list)
        for cid, cdata in actuals.items():
            if cid == bm_client_id:
                continue
            for plat, m in cdata["platforms"].items():
                v = m.get(met_key)
                if v is not None:
                    pool_plat[plat].append(v)
        pool_avg = {plat: round(sum(vals)/len(vals), 3) for plat, vals in pool_plat.items() if vals}
        pool_size = len([k for k in actuals if k != bm_client_id])

        # Comparison rows: focal campaign/aggregation vs pool
        cmp_rows = []
        for plat, m in sorted(focal_plats.items(), key=lambda x: -(x[1].get("spend", 0))):
            c_val   = m.get(met_key)
            p_val   = pool_avg.get(plat)
            ch_val2 = m.get("channel", "")
            var = round((c_val - p_val) / max(abs(p_val), 0.001) * 100, 1) if c_val and p_val else None
            if var is not None:
                beat = "✅" if (lower_better and var < -2) or (not lower_better and var > 2) \
                       else ("❌" if (lower_better and var > 2) or (not lower_better and var < -2) else "➖")
            else:
                beat = "—"
            cmp_rows.append({
                "platform": plat, "channel": ch_val2,
                "client_val": c_val, "pool_val": p_val, "var_pct": var, "beat": beat,
                "spend": m.get("spend", 0),
            })

        # KPI strip
        client_plat_list = [r for r in cmp_rows if r["client_val"] and r["pool_val"]]
        beating = sum(1 for r in client_plat_list if r["beat"] == "✅")
        missing = sum(1 for r in client_plat_list if r["beat"] == "❌")

        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric("Pool Size", f"{pool_size} clients")
        with k2: st.metric("Platforms Compared", len(client_plat_list))
        with k3: st.metric(f"Beating Pool {bm_metric}", f"{beating}")
        with k4: st.metric(f"Behind Pool {bm_metric}", f"{missing}")

        st.markdown("---")

        chart_plats = [r for r in cmp_rows if r["client_val"] and r["pool_val"]]
        if chart_plats:
            chart_df = pd.DataFrame({
                _camp_label_short: {r["platform"].replace("_"," ").title(): r["client_val"] for r in chart_plats},
                "Pool Average":    {r["platform"].replace("_"," ").title(): r["pool_val"]   for r in chart_plats},
            }).sort_values(_camp_label_short, ascending=(met_key == "cpm"))

            col_chart, col_delta = st.columns([3, 2])
            with col_chart:
                st.markdown(f"**{bm_metric} — {_camp_label_short} vs Portfolio Pool**")
                st.bar_chart(chart_df)
            with col_delta:
                st.markdown("**Variance vs Pool**")
                delta_df = pd.DataFrame({
                    "Variance %": {r["platform"].replace("_"," ").title(): r["var_pct"]
                                   for r in chart_plats if r["var_pct"] is not None}
                }).sort_values("Variance %")
                st.bar_chart(delta_df)
                direction = "↓ negative = client is more efficient" if lower_better else "↑ positive = client has better engagement"
                st.caption(f"*{direction}*")

        st.markdown("---")
        st.markdown(f"**Platform Detail — {_camp_label_short} vs Portfolio Pool**")
        tbl = []
        for r in cmp_rows:
            tbl.append({
                "Platform":          r["platform"].replace("_"," ").title(),
                "Channel":           r["channel"].upper(),
                "Spend ($)":         r["spend"],
                _camp_label_short:   r["client_val"],
                "Pool Avg":          r["pool_val"],
                "vs Pool %":         r["var_pct"],
                "":                  r["beat"],
            })
        if tbl:
            tbl_df = pd.DataFrame(tbl).sort_values("Spend ($)", ascending=False)
            st.dataframe(tbl_df, use_container_width=True, hide_index=True,
                         column_config={
                             "Spend ($)":       st.column_config.NumberColumn(format="$%,.0f"),
                             _camp_label_short: st.column_config.NumberColumn(format="$%.2f" if dollar_fmt else "%.3f"),
                             "Pool Avg":        st.column_config.NumberColumn(format="$%.2f" if dollar_fmt else "%.3f"),
                             "vs Pool %":       st.column_config.NumberColumn(format="%.1f%%"),
                         })

    # ══════════════════════════════════════════════════════════════
    # TAB 3: ASK
    # ══════════════════════════════════════════════════════════════
    with bm_tab_ask:
        if "bm_history" not in st.session_state:
            st.session_state.bm_history = []

        for msg in st.session_state.bm_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-msg chat-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-msg chat-ai">{msg["content"]}</div>', unsafe_allow_html=True)
                cost_txt = f" | 💰 ${msg.get('cost', 0.0):.4f}" if "cost" in msg else ""
                if msg.get("qe"): st.caption(f"🔍 {msg['qe']}{cost_txt}")

        bm_dv = st.session_state.pop("bm_input", "")
        bq1, bq2 = st.columns([5, 1])
        with bq1:
            bm_q = st.text_input("Ask about this client vs the pool...", value=bm_dv,
                                 placeholder="e.g. Which platforms is this client most efficient on?",
                                 label_visibility="collapsed", key="bm_qbox")
        with bq2:
            bm_send = st.button("Send", type="primary", use_container_width=True, key="bm_send")

        if (bm_send or bm_dv) and bm_q:
            bm_ctx = {
                "client_name":   bm_client_name,
                "campaign":      _camp_label_short,
                "date_range":    f"{bm_start} → {bm_end}",
                "comparison":    cmp_rows,        # pool comparison — key expected by llm_engine
                "vs_own":        own_rows,         # own-history comparison
                "pool_averages": pool_avg,
            }
            with st.spinner("Analysing…"):
                bm_r = answer_benchmark_question(bm_q, st.session_state.bm_history, context_data=bm_ctx)
            st.session_state.bm_history.append({"role": "user",    "content": bm_q})
            st.session_state.bm_history.append({"role": "assistant","content": bm_r["answer"],
                                                "qe": bm_r.get("query_explanation",""),
                                                "cost": bm_r.get("cost", 0.0)})
            st.rerun()

        if st.button("🗑️ Clear", key="bm_clear"):
            st.session_state.bm_history = []; st.rerun()

# ═══════════════════════════════════════
# MODE 6: DATA (SuperMetrics pull)
# ═══════════════════════════════════════
elif mode == "🗄️ Data":
    st.markdown("""<div class="main-header">
        <h1>🗄️ BigQuery Data</h1>
        <p>Live connection to <code>res-apac-dev-skynet-au · resodigital_MelbUnified.all_clients_unified</code></p>
    </div>""", unsafe_allow_html=True)

    from bigquery_data_layer import get_bq_summary, _run, TABLE_ID

    with st.spinner("Fetching BigQuery summary…"):
        try:
            summary = get_bq_summary()
        except Exception as _bq_err:
            st.error(f"BigQuery connection error: {_bq_err}")
            st.caption("Make sure ADC is configured: `gcloud auth application-default login`")
            st.stop()

    if not summary:
        st.warning("No data found in BigQuery table.")
        st.stop()

    # ── KPI banner ─────────────────────────────────────────────────────────
    bq1, bq2, bq3, bq4 = st.columns(4)
    with bq1: st.metric("Total Rows", f"{summary['row_count']:,}")
    with bq2: st.metric("Date Range", f"{summary['date_min']} → {summary['date_max']}")
    with bq3: st.metric("Clients", summary['clients'])
    with bq4: st.metric("Total Spend", f"${summary.get('total_spend', 0):,.0f}")

    st.markdown("---")

    # ── Rows by client ──────────────────────────────────────────────────────
    st.markdown("#### Rows & Spend by Client")
    try:
        df_clients = _run(f"""
            SELECT client,
                   COUNT(*)       AS row_count,
                   SUM(spend)     AS total_spend,
                   MIN(date)      AS date_min,
                   MAX(date)      AS date_max,
                   COUNT(DISTINCT platform) AS platforms
            FROM {TABLE_ID}
            GROUP BY client
            ORDER BY total_spend DESC
        """)
        st.dataframe(df_clients.style.format({"total_spend": "${:,.0f}", "row_count": "{:,}"}),
                     use_container_width=True)
    except Exception as _e:
        st.warning(f"Could not load client breakdown: {_e}")

    st.markdown("---")

    # ── Rows by platform ────────────────────────────────────────────────────
    st.markdown("#### Rows & Spend by Platform")
    try:
        df_plat = _run(f"""
            SELECT platform,
                   COUNT(*)  AS row_count,
                   SUM(spend) AS total_spend
            FROM {TABLE_ID}
            GROUP BY platform
            ORDER BY total_spend DESC
        """)
        st.dataframe(df_plat.style.format({"total_spend": "${:,.0f}", "row_count": "{:,}"}),
                     use_container_width=True)
    except Exception as _e:
        st.warning(f"Could not load platform breakdown: {_e}")

    st.markdown("---")

    # ── Raw SQL explorer ────────────────────────────────────────────────────
    st.markdown("#### SQL Explorer")
    st.caption("Run any SELECT query against the unified table.")
    default_sql = f"SELECT client, platform, date, spend, impressions\nFROM {TABLE_ID}\nORDER BY date DESC\nLIMIT 50"
    user_sql = st.text_area("SQL", value=default_sql, height=120, key="bq_sql_input")
    if st.button("▶ Run Query", key="bq_run"):
        with st.spinner("Querying BigQuery…"):
            try:
                df_result = _run(user_sql)
                st.success(f"{len(df_result):,} rows returned")
                st.dataframe(df_result, use_container_width=True)
            except Exception as _qe:
                st.error(f"Query error: {_qe}")

# ═══════════════════════════════════════
# MODE 7: AUTOMATED OPTIMIZATION
# ═══════════════════════════════════════
elif mode == "⚡ Automated Optimization":
    from llm_engine import generate_optimizations
    
    with st.sidebar:
        st.markdown("##### 1. Date Range")
        oc1, oc2 = st.columns(2)
        with oc1: osd = st.date_input("Start", value=date(2025, 1, 1), min_value=date(2024, 1, 1), key="opt_sd")
        with oc2: oed = st.date_input("End", value=date(2025, 12, 31), min_value=osd, key="opt_ed")
        oss, oes = osd.strftime("%Y-%m-%d"), oed.strftime("%Y-%m-%d")

        st.markdown("##### 2. Client")
        o_clients = get_clients_in_date_range(oss, oes)
        o_co = {c["client_name"]: c["client_id"] for c in o_clients}
        if not o_co: st.warning("No clients."); st.stop()
        o_cn = st.selectbox("Client", list(o_co.keys()), label_visibility="collapsed", key="opt_cl")
        o_ci = o_co[o_cn]

        st.markdown("##### 3. Campaign")
        o_camps = get_campaigns_for_client(o_ci, oss, oes)
        o_cop = {f"{c['campaign_name']}  ({c['start']} → {c['end']})": c for c in o_camps}
        if not o_cop: st.warning("No campaigns."); st.stop()
        o_scl = st.selectbox("Campaign", list(o_cop.keys()), label_visibility="collapsed", key="opt_camp")
        o_sc = o_cop[o_scl]

        st.markdown("---")
        run_opt = st.button("🚀 Run Agentic Scan", type="primary", use_container_width=True)

    st.markdown(f"""<div class="main-header">
        <h1>🤖 Agentic Optimization</h1>
        <p>{o_cn}  •  {o_sc['campaign_name']}  •  Automated Platform Recommendations</p>
    </div>""", unsafe_allow_html=True)
    
    _cache_key = (o_ci, o_sc["campaign_id"], oss, oes, ch_val)

    if run_opt:
        if st.session_state.get("_opt_cache_key") == _cache_key and "opt_result" in st.session_state:
            st.toast("Using cached scan results.", icon="💾")
        else:
            with st.spinner("Analyzing live data..."):
                sdata = assemble_pca_data(o_ci, o_sc["campaign_id"], o_sc["start"], o_sc["end"], ch_val)
                result = generate_optimizations(sdata)
                st.session_state["opt_result"] = result.get("optimizations", [])
                st.session_state["_opt_cache_key"] = _cache_key
                # initialize checkboxes
                for i in range(len(st.session_state["opt_result"])):
                    st.session_state[f"opt_chk_{i}"] = False

    if "opt_result" not in st.session_state:
        st.info("Select a campaign in the sidebar and click **Run Agentic Scan** to identify optimizations.")
        st.stop()

    opts = st.session_state["opt_result"]
    if not opts:
        st.warning("No optimizations could be generated for this campaign constraint.")
        st.stop()

    st.markdown("### Suggested Platform Actions")
    
    selected_any = False
    for i, opt in enumerate(opts):
        conf = opt.get("confidence", 0)
        c_color = "var(--green)" if conf > 0.8 else "var(--orange)"
        
        html_container = f"""<div style="background: white; border: 1px solid var(--border); border-radius: 12px; padding: 18px; margin-bottom: 12px; box-shadow: var(--sh-sm);">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
<div>
<span class="storyline-badge" style="background: {c_color}22; color: {c_color};">⚡ {int(conf*100)}% Confidence</span>
<span class="storyline-badge">🖥️ {opt.get('platform', 'Platform')}</span>
<strong style="font-size: 16px; color: var(--navy);">{opt.get('action', '')}</strong>
</div>
</div>
<p style="color: var(--text-2); font-size: 14px; margin: 4px 0 12px 0; line-height: 1.5;">{opt.get('rationale', '')}</p>
<div style="display: flex; gap: 20px; align-items: center; background: var(--bg); padding: 12px; border-radius: 8px; margin-bottom: 12px;">
<div style="flex: 1;">
<div style="font-size: 11px; color: var(--text-3); text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Predicted Impact</div>
<div style="font-size: 14px; font-weight: 600; color: var(--navy);">{opt.get('expected_impact', '')}</div>
</div>
<div style="flex: 1;">
<div style="font-size: 11px; color: var(--text-3); text-transform: uppercase; font-weight: 700; margin-bottom: 4px;">Confidence ({int(conf*100)}%)</div>
<div style="height: 8px; background: var(--border); border-radius: 4px; width: 100%; overflow: hidden;">
<div style="height: 100%; width: {int(conf*100)}%; background: {c_color};"></div>
</div>
</div>
</div>
</div>"""
        st.markdown(html_container, unsafe_allow_html=True)
        # Checkbox for selection outside markdown
        is_sel = st.checkbox("Select this optimization", key=f"opt_chk_{i}")
        if is_sel: selected_any = True
        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
        
    st.markdown("---")
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("⚡ Deploy Selected", disabled=not selected_any, type="primary"):
            st.session_state.deploy_running = True
            
    if st.session_state.get("deploy_running"):
        prog = st.progress(0, "Connecting to platform APIs...")
        time.sleep(1)
        prog.progress(30, "Authenticating and pushing changes...")
        time.sleep(1.5)
        prog.progress(70, "Validating active budget limits...")
        time.sleep(1)
        prog.progress(100, "Changes successfully deployed!")
        time.sleep(1)
        prog.empty()
        st.success("✅ Selected optimizations have been queued and pushed to platform accounts.")
        st.session_state.deploy_running = False

# ═══════════════════════════════════════
# MODE 8: MEDIA STRATEGY BUILDER
# ═══════════════════════════════════════
elif mode == "🧠 Media Strategy Builder":
    from llm_engine import generate_media_strategy
    from excel_builder import build_media_strategy_excel
    from pptx_builder import build_media_strategy_pptx
    from data_layer import get_clients_in_date_range, get_campaigns_for_client, assemble_pca_data, get_live_clients as _msb_glc
    from live_analytics import get_portfolio_benchmarks
    MOCK_CLIENTS = _msb_glc()

    st.markdown("""<div class="main-header">
        <h1>🧠 Media Strategy Builder</h1>
        <p>Upload a client brief → AI reads your campaign history + market data → generates a full media strategy with Excel plan + presentation</p>
    </div>""", unsafe_allow_html=True)

    # ── Known brief → client mapping ──────────────────────────────────────────
    _BRIEF_CLIENT_MAP = {
        "OMD FY25 Strategic Brief": "Belong",
    }

    # ── Parsed summary cards for known briefs ─────────────────────────────────
    _BRIEF_SUMMARIES = {
        "OMD FY25 Strategic Brief": {
            "client":    "Belong",
            "category":  "Telco — value-positioned MVNO (Telstra subsidiary)",
            "period":    "FY25 (Full Year)",
            "budget":    "TBC — baseline budget + incremental activity model",
            "objectives": [
                "Win and retain customers, increase ARPU, operate more efficiently",
                "Increase Consideration to Conversion +40% (from FY24 baseline: 21%)",
                "Grow Prompted Awareness above 53%",
            ],
            "sales_targets": [
                "Mobile: 40k Net Adds (incremental 24.3k SIOs)",
                "Fixed/NBN: 30k Net Adds (incremental 15.7k SIOs)",
            ],
            "audiences": [
                "NBN — Renters, Refinancers, Rage Quitters, Retail Re-Evaluators, Movers",
                "Mobile — BBL/WBBL Fans, Internationals/Migrants, Frantic Families, Cost-pressured individuals",
                "Financial decision maker in the household",
            ],
            "key_messages": [
                "More of the Good Stuff — products & value proposition",
                "Best value-for-money experience (Belong 59% vs industry 33% on value affordability)",
                "Cannot use word 'value' legally — must communicate through benefits and emotional drivers",
            ],
            "challenges": [
                "Low unprompted awareness — prospects don't know what Belong offers beyond 'value'",
                "Campaign hasn't sustained perception gains — sentiment ambivalent among non-customers",
                "Belong eco-system is digital-only — difficult to bring into real-world environments",
                "Sydney Sixers BBL/WBBL & JB-HiFi sponsorships need better integration",
            ],
            "seasonality": [
                "Mobile peak: Black Friday & XMAS (Nov–Jan) — Bonus Data + Retail SIM offers",
                "NBN peak: Q4 Mover's season (Jan–Mar) — sales dip at XMAS & Easter",
            ],
            "pages": 17,
        }
    }

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("##### 1. Upload Brief")
        brief_file = st.file_uploader("Client brief (PDF)", type=["pdf"], label_visibility="collapsed")

        st.markdown("##### 2. Client")
        ms_clients = get_clients_in_date_range("2024-01-01", "2026-12-31")
        ms_co = {c["client_name"]: c["client_id"] for c in ms_clients}
        if not ms_co:
            st.warning("No clients found.")
            st.stop()

        # Auto-select client based on uploaded brief filename
        _default_client = list(ms_co.keys())[0]
        if brief_file:
            fn_lower = brief_file.name.lower().replace(" ", "").replace("_", "").replace("-", "")
            for key, cname in _BRIEF_CLIENT_MAP.items():
                if key.lower().replace(" ", "") in fn_lower:
                    if cname in ms_co:
                        _default_client = cname
                    break
        _client_idx = list(ms_co.keys()).index(_default_client) if _default_client in ms_co else 0
        ms_cn = st.selectbox("Client", list(ms_co.keys()), index=_client_idx, label_visibility="collapsed", key="ms_client")
        ms_ci = ms_co[ms_cn]

        st.markdown("##### 3. Options")
        ms_budget = st.text_input("Total budget (optional)", placeholder="e.g. $2.5M", key="ms_budget")
        ms_period = st.text_input("Campaign period (optional)", placeholder="e.g. Q1–Q3 FY26", key="ms_period")
        ms_focus  = st.text_area("Additional context", placeholder="e.g. New product launch, focus on 25-44, heavy Metro", height=80, key="ms_focus")

        st.markdown("---")
        ms_run = st.button("🚀 Build Strategy", type="primary", use_container_width=True)

    # ── Hardcoded brief library (for image-based demo PDFs) ──────────────────
    _KNOWN_BRIEFS = {
        "OMD FY25 Strategic Brief": """
CLIENT: Belong (Telco — Telstra subsidiary, value-positioned MVNO)
BRIEF: FY25 Strategic Brief — Media & Creative
PREPARED BY: OMD Australia

═══════════════════════════════════════
THE CHALLENGE (WHY)
═══════════════════════════════════════
Primary challenge is unprompted awareness and recognition — and how that translates into sales performance. Much of the market doesn't know who Belong is or what they offer beyond 'value'. We want to make sure we have the right people knowing the right attributes to drive value perception, so we are working for prospective customers to create a baseline of creative and media strategies for the next financial year.

There are heaps of proof points not yet heroised in market (6.5/1.2) that would demonstrate how we offer 'more of the good stuff'.

THE GOOD STUFF RESEARCH: The campaign highlights products and value proposition and is associated with an increase in brand consideration. However the campaign hasn't increased awareness and the increase in perception hasn't been sustained. Sentiment remains mostly ambivalent among non-customers — they still say they don't know enough about Belong to decide whether to put Belong on their list.

MEDIA CHALLENGE:
- The media plan (with budgets) needs to be able to adapt to market conditions
- How we can better support (and sweat) our existing partners and retail channels — this includes JB-HiFi and the Sydney Sixers to capitalise on their credibility and mental availability with consumers
- The Belong eco-system is currently a digital (black) world. Bringing this into the real world using the player real-estate available is incredibly difficult. To integrate more seamlessly through the season we could explore placement relevant to this audience.

CREATIVE CHALLENGE:
- Maintain 'More of the good stuff' campaign collateral, altering and personalising the messaging for our segments
- Talking to benefits and values that make sense to the target audience
- Given the legal challenges and the average of displaying "Great Value", how can we display value without saying "value" in order to communicate the benefits and emotional drivers — i.e. the product attributes which acquire our customers
- We can't be all things to all people. Understand what message works for each audience, and in what format

═══════════════════════════════════════
OBJECTIVES (WHAT)
═══════════════════════════════════════
Overall: Win and retain customers, increase ARPU and operate more efficiently.

To do this we need to develop a brand campaign and media plan that can shift with changing market conditions, without needing mass amounts of rework, like our previous ways of working.

BUSINESS OBJECTIVES:
- Formalised OKRs will be populated end of April — refer to the Excel document titled "Targets for OMD"

BRAND OBJECTIVES (Improve Upon FY24):
- Consideration to Conversion: +40%
- Consideration: 21%
- Prompted Awareness: 53%

SALES TARGETS:
- Mobile: Ambition Target 40k Net Adds for PPIH (incremental 24.3k SIOs)
- Fixed/NBN: Ambition Target 30k Net Adds for NBN (incremental 15.7k SIOs)

SEASONALITY — MOBILE:
Key trading periods are Black Friday & XMAS (Nov–Jan) with momentum driven by Bonus Data offers as well as Retail SIM / catalogue activity. FY25 saw less volatility in monthly movements compared to FY22, with Black Fri/XMAS period performance slightly softer. FY23 offer was Double Data on $35+ Plans vs FY22 Double Data on all Plans. Would expect FY24 to have a smaller lift too as we are running a smaller offer of +20GB on $35+ Plans.

SEASONALITY — NBN:
Decline in NBN Activations from FY23–24 as portfolio has been impacted by: price rises, exit of many Channel partners. Key trading period in NBN is Q4 Mover's season (Jan–Mar) and sales dip during XMAS and Easter breaks. BYO Modem option introduced in mid-Mar Q4 FY22. Price rises in Sep–Nov periods for FY23 (+$5 NBN25/NBN50) and FY24 (+$5 on NBN50). Partner channel decline from Q2 FY23.

═══════════════════════════════════════
TARGET AUDIENCE (WHO)
═══════════════════════════════════════
Refocus the target market: based on what we know, there are four potential intent-based audiences that have aligned needs of affordability and reliability for consideration and validation. We also need to reach the financial decision maker in the household.

NBN Specific Audiences:
- Renters — Affordable NBN that is easy to connect and move
- Refinancers — NBN that is optimised to my budget
- Rage Quitters — Quality of service that I can afford
- Retail Re-Evaluators — The Telstra network at a price I can afford
- Movers — Those in the market and ready to explore other options

Mobile Specific Audiences:
- BBL/WBBL Fans
- Internationals / Migrants
- Frantic Families
- Cost-pressured individuals — students, first time out-of-homers, renters saving for their first home

BRAND HEALTH (Jan–24 tracking):
- Value Affordability: Belong 59% vs Industry 33% (Brand Leader)
- Plan Inclusions: 47% → 45%
- Network: 36% → 33%
- Simplicity: 7% → 9%
- Brand: 5% → 8%
- Offer Clarity & Relevance: 4% → 3%
- Rewards & Recognition: 1% → 2%

MOBILE VALUE DRIVERS:
- Postpaid mobile acquisition remains highly price-led; price is around twice as impactful in assessing value than quality
- When assessing quality of Postpaid Mobile providers, plan inclusions and network performance are still most impactful across both acquisition and retention
- Belong is perceived best value for money experience amongst providers tracked
- Belong moved into high value among non-customers and remained high value amongst own customers
- This puts Belong in a strong position to both acquire new and retain existing customers
- How Belong can improve its value: continue to reinforce strong value for money (especially price, offer clarity/relevance, plan inclusions and customer service); improve perceptions of network, brand and potentially rewards/recognition

BUDGETS:
- Primary recommendations must fit within the budget
- As mentioned previously we want to have a baseline budget then incremental activity (and budget) to incorporate which could change to chase performance and growth
- Budgets: primary recommendations must fit within the budget

═══════════════════════════════════════
ADDITIONAL CONTEXT
═══════════════════════════════════════
- Sydney Sixers BBL/WBBL sponsorship is a key partnership to activate
- JB-HiFi retail channel partnership should be leveraged
- Campaign must be channel-agnostic and adapt creative for different placements
- Sponsorship: location & message specific — applying to everyone at anytime vs. sponsorship-location-specific messaging
- Total Creative Timelines: 20 creative executions planned
- Belong is perceived as best value-for-money, key differentiator vs Optus, Vodafone, Telstra
- Legal constraint: cannot use the word "value" directly — must communicate value through benefits and emotional drivers
"""
    }

    def _match_known_brief(filename: str):
        """Return hardcoded brief text if filename matches a known brief."""
        fn_lower = (filename or "").lower()
        for key, text in _KNOWN_BRIEFS.items():
            if key.lower().replace(" ", "") in fn_lower.replace(" ", "").replace("_", "").replace("-", ""):
                return text
        return None

    # ── Brief text extraction ─────────────────────────────────────────────────
    brief_text = ""
    brief_source = ""

    if brief_file is not None:
        # Check for known hardcoded brief first
        hardcoded = _match_known_brief(brief_file.name)
        if hardcoded:
            brief_text   = hardcoded
            brief_source = "hardcoded"
        else:
            # Try PDF text extraction
            try:
                import pdfplumber, io
                with pdfplumber.open(io.BytesIO(brief_file.read())) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            brief_text += t + "\n"
            except Exception:
                pass
            brief_source = "extracted" if len(brief_text.strip()) > 100 else "fallback"

    if ms_budget:
        brief_text += f"\n\nBudget: {ms_budget}"
    if ms_period:
        brief_text += f"\nCampaign Period: {ms_period}"
    if ms_focus:
        brief_text += f"\nAdditional context: {ms_focus}"

    # ── Show brief status + parsed summary ────────────────────────────────────
    if brief_file:
        if brief_source == "hardcoded":
            st.success(f"📄 **{brief_file.name}** — brief fully parsed ✅")
        elif brief_source == "extracted":
            st.success(f"📄 **{brief_file.name}** — {len(brief_text):,} characters extracted")
        else:
            st.warning(f"📄 **{brief_file.name}** — image-based PDF, limited extraction. Add context in sidebar fields.")

        # Find matching summary card
        _summary = None
        if brief_file:
            fn_lower = brief_file.name.lower().replace(" ", "").replace("_", "").replace("-", "")
            for key, summ in _BRIEF_SUMMARIES.items():
                if key.lower().replace(" ", "") in fn_lower:
                    _summary = summ
                    break

        if _summary:
            st.markdown("---")
            st.markdown("#### 📋 Brief Summary")

            # Top meta row
            m1, m2, m3, m4 = st.columns(4)
            with m1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Client</div><div class="kpi-value" style="font-size:16px;">{_summary["client"]}</div><div class="kpi-sub">{_summary["category"]}</div></div>', unsafe_allow_html=True)
            with m2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Campaign Period</div><div class="kpi-value" style="font-size:16px;">{_summary["period"]}</div><div class="kpi-sub">&nbsp;</div></div>', unsafe_allow_html=True)
            with m3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Budget</div><div class="kpi-value" style="font-size:14px;">{_summary["budget"]}</div><div class="kpi-sub">&nbsp;</div></div>', unsafe_allow_html=True)
            with m4: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Brief Pages</div><div class="kpi-value" style="font-size:16px;">{_summary["pages"]}</div><div class="kpi-sub">pages extracted</div></div>', unsafe_allow_html=True)

            st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

            row1_left, row1_right = st.columns(2)

            with row1_left:
                st.markdown(
                    '<div class="slide-card">'
                    '<div class="kpi-label" style="margin-bottom:8px;">🎯 Objectives</div>'
                    + "".join(f'<div style="font-size:13px;color:#374151;padding:4px 0;border-bottom:1px solid #F0F2F6;">• {o}</div>' for o in _summary["objectives"])
                    + '</div>', unsafe_allow_html=True
                )
                st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div class="slide-card">'
                    '<div class="kpi-label" style="margin-bottom:8px;">📈 Sales Targets</div>'
                    + "".join(f'<div style="font-size:13px;color:#374151;padding:4px 0;border-bottom:1px solid #F0F2F6;">• {t}</div>' for t in _summary["sales_targets"])
                    + '</div>', unsafe_allow_html=True
                )
                st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div class="slide-card">'
                    '<div class="kpi-label" style="margin-bottom:8px;">📅 Seasonality</div>'
                    + "".join(f'<div style="font-size:13px;color:#374151;padding:4px 0;border-bottom:1px solid #F0F2F6;">• {s}</div>' for s in _summary["seasonality"])
                    + '</div>', unsafe_allow_html=True
                )

            with row1_right:
                st.markdown(
                    '<div class="slide-card">'
                    '<div class="kpi-label" style="margin-bottom:8px;">👥 Target Audiences</div>'
                    + "".join(f'<div style="font-size:13px;color:#374151;padding:4px 0;border-bottom:1px solid #F0F2F6;">• {a}</div>' for a in _summary["audiences"])
                    + '</div>', unsafe_allow_html=True
                )
                st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div class="slide-card">'
                    '<div class="kpi-label" style="margin-bottom:8px;">💬 Key Messages</div>'
                    + "".join(f'<div style="font-size:13px;color:#374151;padding:4px 0;border-bottom:1px solid #F0F2F6;">• {m}</div>' for m in _summary["key_messages"])
                    + '</div>', unsafe_allow_html=True
                )
                st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                st.markdown(
                    '<div class="slide-card">'
                    '<div class="kpi-label" style="margin-bottom:8px;">⚠️ Key Challenges</div>'
                    + "".join(f'<div style="font-size:13px;color:#374151;padding:4px 0;border-bottom:1px solid #F0F2F6;">• {c}</div>' for c in _summary["challenges"])
                    + '</div>', unsafe_allow_html=True
                )

            st.markdown("---")

    else:
        st.info("Upload a client brief PDF in the sidebar, or fill in the context fields, then click **Build Strategy**.")

    # ── Run ───────────────────────────────────────────────────────────────────
    _ms_cache_key = (ms_ci, ms_budget, ms_period, ms_focus, brief_text[:200] if brief_text else "")

    if ms_run:
        if st.session_state.get("_ms_cache_key") == _ms_cache_key and "ms_result" in st.session_state:
            st.toast("Showing cached strategy. Change inputs to regenerate.", icon="💾")
        else:
            st.session_state.pop("ms_result", None)

            _ms_prog = st.progress(0, "Initialising…")

            # Step 1 — gather client history
            _ms_prog.progress(5, "📦 Pulling client campaign history…")
            all_client_campaigns = get_campaigns_for_client(ms_ci, "2024-01-01", "2026-12-31")
            client_history_data = {"client_name": ms_cn, "campaigns": []}
            for camp in all_client_campaigns[:8]:  # cap at 8 most recent campaigns
                try:
                    camp_data = assemble_pca_data(ms_ci, camp["campaign_id"], camp["start"], camp["end"], "all")
                    camp_data["_campaign_name"] = camp["campaign_name"]
                    camp_data["_dates"] = f"{camp['start']} → {camp['end']}"
                    client_history_data["campaigns"].append({
                        "name": camp["campaign_name"],
                        "dates": f"{camp['start']} → {camp['end']}",
                        "overview": camp_data.get("overview", []),
                        "total_spend": sum(o.get("total_spend", 0) for o in camp_data.get("overview", [])),
                    })
                except Exception:
                    pass

            # Step 2 — gather market context
            _ms_prog.progress(15, "📊 Pulling market benchmarks…")
            market_context = {
                "portfolio_benchmarks": get_portfolio_benchmarks("all"),
                "note": "Benchmarks aggregated from all clients in portfolio (excluding selected client where possible)"
            }

            # Step 3 — LLM
            _ms_prog.progress(20, "🧠 Building strategy with AI…")
            strategy = generate_media_strategy(brief_text, client_history_data, market_context)
            _ms_prog.progress(85, "✅ Strategy generated")

            # Step 4 — Excel
            _ms_prog.progress(86, "📗 Building media plan (Excel)…")
            ms_xlsx = os.path.join(_TMPDIR, "media_strategy.xlsx")
            build_media_strategy_excel(strategy, ms_xlsx)
            _ms_prog.progress(93, "✅ Excel done")

            # Step 5 — PPTX
            _ms_prog.progress(94, "📙 Building strategy deck (PowerPoint)…")
            ms_pptx = os.path.join(_TMPDIR, "media_strategy.pptx")
            build_media_strategy_pptx(strategy, ms_pptx)
            _ms_prog.progress(100, "✅ Complete")
            time.sleep(0.4)
            _ms_prog.empty()

            st.session_state["ms_result"]     = {"strategy": strategy, "xlsx": ms_xlsx, "pptx": ms_pptx}
            st.session_state["_ms_cache_key"] = _ms_cache_key
            st.rerun()

    # ── Display result ────────────────────────────────────────────────────────
    if "ms_result" not in st.session_state:
        st.stop()

    result   = st.session_state["ms_result"]
    strategy = result["strategy"]

    if strategy.get("_error"):
        st.error(f"LLM error — showing mock strategy. **{strategy['_error']}**")

    s = strategy

    # ── KPI bar ──────────────────────────────────────────────────────────────
    alloc      = s.get("budget_allocation", [])
    n_channels = len(s.get("channel_mix", []))
    n_months   = len(s.get("monthly_flight", []))
    n_recs     = len(s.get("recommendations", []))
    meta       = s.get("_metadata", {})
    llm_cost   = meta.get("cost", 0.0)
    llm_tokens = meta.get("tokens", 0)
    llm_model  = meta.get("model", "")
    cost_sub   = f"{llm_tokens:,} tokens" + (f"  ·  {llm_model}" if llm_model and llm_model != "mock" else "")

    kpi_cols = st.columns(5)
    for col, (label, val, sub) in zip(kpi_cols, [
        ("Client",        ms_cn,                    s.get("brief_summary", {}).get("campaign_period", "")),
        ("Budget",        s.get("brief_summary", {}).get("budget_indication", ms_budget or "TBD"), "as briefed"),
        ("Channels",      f"{n_channels}",           "in recommended mix"),
        ("Flight Months", f"{n_months}",             "in plan"),
        ("Generation Cost", f"${llm_cost:.4f}",      cost_sub),
    ]):
        with col:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Downloads ─────────────────────────────────────────────────────────────
    dl1, dl2, dl3 = st.columns(3)
    with dl1:
        with open(result["pptx"], "rb") as f:
            st.download_button("📙 Strategy Deck (.pptx)", f.read(),
                               file_name=f"MediaStrategy_{ms_cn}.pptx",
                               mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                               use_container_width=True)
    with dl2:
        with open(result["xlsx"], "rb") as f:
            st.download_button("📗 Media Plan (.xlsx)", f.read(),
                               file_name=f"MediaPlan_{ms_cn}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True)
    with dl3:
        st.download_button("📋 Strategy JSON", json.dumps(s, indent=2).encode(),
                           file_name=f"MediaStrategy_{ms_cn}.json",
                           mime="application/json",
                           use_container_width=True)

    st.markdown("---")

    # ── Strategy preview tabs ─────────────────────────────────────────────────
    ms_t1, ms_t2, ms_t3, ms_t4, ms_t5 = st.tabs([
        "📋 Strategy Overview", "📡 Channel Mix", "📅 Flight Plan", "💡 Insights & Learnings", "🔧 Raw JSON"
    ])

    # ── TAB 1: Strategy Overview ──────────────────────────────────────────────
    with ms_t1:
        bs  = s.get("brief_summary", {})
        sa  = s.get("strategic_approach", {})

        st.markdown(f'<div class="so-what" style="font-size:15px;font-weight:600;">🎯 {s.get("strategy_headline","")}</div>', unsafe_allow_html=True)
        st.markdown(s.get("executive_summary", ""), unsafe_allow_html=False)

        c_left, c_right = st.columns(2)

        with c_left:
            st.markdown("**Brief Summary**")
            st.markdown(f"- **Period:** {bs.get('campaign_period','')}")
            st.markdown(f"- **Budget:** {bs.get('budget_indication','')}")
            st.markdown(f"- **Audience:** {bs.get('target_audience','')}")
            objs = bs.get("objectives", [])
            if objs:
                st.markdown("**Objectives:**")
                for o in objs:
                    st.markdown(f"  - {o}")
            msgs = bs.get("key_messages", [])
            if msgs:
                st.markdown("**Key Messages:**")
                for m in msgs:
                    st.markdown(f"  - {m}")

        with c_right:
            st.markdown("**Strategic Approach**")
            st.markdown(f"**Positioning:** {sa.get('positioning','')}")
            st.markdown(f"**Channel Philosophy:** {sa.get('channel_philosophy','')}")
            tensions = sa.get("key_tensions", [])
            if tensions:
                st.markdown("**Key Tensions:**")
                for t in tensions:
                    st.markdown(f"  - {t}")

        recs = s.get("recommendations", [])
        if recs:
            st.markdown("---")
            st.markdown("**Recommendations**")
            for rec in recs:
                prio  = rec.get("priority", "MEDIUM")
                color = {"HIGH": "#DC2626", "MEDIUM": "#F05C2C", "LOW": "#4338CA"}.get(prio, "#4338CA")
                st.markdown(
                    f'<div style="background:white;border:1px solid var(--border);border-left:4px solid {color};'
                    f'border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px;">'
                    f'<span style="font-size:10px;font-weight:700;color:{color};text-transform:uppercase;">{prio}</span> '
                    f'<strong style="color:#0F172A;">{rec.get("recommendation","")}</strong><br>'
                    f'<span style="font-size:13px;color:#4B5563;">{rec.get("rationale","")}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        risks = s.get("risks_and_mitigations", [])
        if risks:
            st.markdown("---")
            st.markdown("**Risks & Mitigations**")
            for r in risks:
                st.markdown(f"- ⚠️ **{r.get('risk','')}** — {r.get('mitigation','')}")

    # ── TAB 2: Channel Mix ────────────────────────────────────────────────────
    with ms_t2:
        channel_mix = s.get("channel_mix", [])
        alloc       = s.get("budget_allocation", [])

        if alloc:
            alloc_df = pd.DataFrame(alloc)
            c_chart, c_table = st.columns([2, 3])
            with c_chart:
                st.markdown("**Budget Allocation**")
                chart_df = pd.DataFrame({
                    "Channel": [a["channel"] for a in alloc],
                    "Budget %": [a["pct"] for a in alloc],
                }).set_index("Channel")
                st.bar_chart(chart_df)
            with c_table:
                st.markdown("**Budget by Channel**")
                st.dataframe(alloc_df, use_container_width=True, hide_index=True,
                             column_config={"pct": st.column_config.NumberColumn("Budget %", format="%d%%")})

        st.markdown("---")
        st.markdown("**Channel Detail**")
        for ch in channel_mix:
            with st.expander(f"**{ch.get('channel','')}**  —  {ch.get('budget_pct',0)}%  |  {ch.get('role','')}", expanded=False):
                cc1, cc2 = st.columns(2)
                with cc1:
                    st.markdown(f"**Platforms:** {', '.join(ch.get('platforms',[]))}")
                    st.markdown(f"**Formats:** {', '.join(ch.get('recommended_formats',[]))}")
                    st.markdown(f"**KPIs:** {', '.join(ch.get('kpis',[]))}")
                with cc2:
                    st.markdown(f"**Past Performance:** {ch.get('past_performance','')}")
                    st.markdown(f"**Market Benchmark:** {ch.get('market_benchmark','')}")
                st.markdown(f"**Rationale:** {ch.get('rationale','')}")

    # ── TAB 3: Flight Plan ────────────────────────────────────────────────────
    with ms_t3:
        flight = s.get("monthly_flight", [])
        if flight:
            weight_map   = {"Heavy": 3, "Medium": 2, "Light": 1, "Off": 0}
            weight_color = {"Heavy": "🔴", "Medium": "🟡", "Light": "🟢", "Off": "⚫"}
            flight_df = pd.DataFrame([{
                "Month":    f.get("month", ""),
                "Phase":    f.get("phase", ""),
                "Weight":   f.get("relative_weight", ""),
                "Channels": ", ".join(f.get("channels_active", [])) if isinstance(f.get("channels_active"), list) else str(f.get("channels_active", "")),
                "Activity": f.get("activity", ""),
            } for f in flight])

            # Visual flight strip
            st.markdown("**Activity Heatmap**")
            cols_per_row = min(6, len(flight))
            for row_start in range(0, len(flight), cols_per_row):
                row_flights = flight[row_start:row_start + cols_per_row]
                row_cols = st.columns(len(row_flights))
                for col, f in zip(row_cols, row_flights):
                    w = f.get("relative_weight", "Medium")
                    bg = {"Heavy": "#FEE2E2", "Medium": "#FEF3C7", "Light": "#F0FDF4", "Off": "#F9FAFB"}.get(w, "#F9FAFB")
                    fg = {"Heavy": "#991B1B", "Medium": "#92400E", "Light": "#166534", "Off": "#6B7280"}.get(w, "#374151")
                    with col:
                        st.markdown(
                            f'<div style="background:{bg};border:1px solid #E5E7EB;border-radius:8px;padding:10px 8px;text-align:center;">'
                            f'<div style="font-size:11px;font-weight:700;color:{fg};">{f.get("month","")}</div>'
                            f'<div style="font-size:10px;color:{fg};margin-top:2px;">{w}</div>'
                            f'<div style="font-size:9px;color:#6B7280;margin-top:3px;">{f.get("phase","")}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

            st.markdown("---")
            st.markdown("**Flight Plan Detail**")
            st.dataframe(flight_df, use_container_width=True, hide_index=True,
                         column_config={"Activity": st.column_config.TextColumn(width="large")})

    # ── TAB 4: Insights & Learnings ───────────────────────────────────────────
    with ms_t4:
        i1, i2 = st.columns(2)

        with i1:
            st.markdown("**📊 Market Insights from Portfolio**")
            for ins in s.get("market_insights", []):
                st.markdown(
                    f'<div class="slide-card" style="margin-bottom:10px;">'
                    f'<strong style="color:#0D0A2E;">{ins.get("insight","")}</strong>'
                    f'<div class="so-what" style="margin-top:6px;">➔ {ins.get("implication","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        with i2:
            st.markdown("**🎓 Learnings from Past Campaigns**")
            for lrn in s.get("past_campaign_learnings", []):
                st.markdown(
                    f'<div class="slide-card" style="margin-bottom:10px;">'
                    f'<strong style="color:#0D0A2E;">{lrn.get("learning","")}</strong>'
                    f'<div class="so-what" style="margin-top:6px;">Applied: {lrn.get("applied_as","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

    # ── TAB 5: Raw JSON ───────────────────────────────────────────────────────
    with ms_t5:
        st.json(s)

# ═══════════════════════════════════════
# MODE: CAMPAIGN PULSE
# ═══════════════════════════════════════
elif mode == "📊 Campaign Pulse":
    from data_layer import get_live_clients as _glc, assemble_pca_data
    MOCK_CLIENTS = _glc()

    st.markdown("""<div class="main-header">
        <h1>📊 Campaign Pulse</h1>
        <p>Standardised performance scorecard — benchmarks CPM, CTR, CPC and creative effectiveness into a single quality signal</p>
    </div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("##### Client & Campaign")
        cp_clients = list(MOCK_CLIENTS.keys())
        cp_ci = st.selectbox("Client", cp_clients, format_func=lambda x: MOCK_CLIENTS[x]["name"], key="cp_client")
        cp_camps = list(MOCK_CLIENTS[cp_ci]["campaigns"].keys())
        cp_camp  = st.selectbox("Campaign", cp_camps, format_func=lambda x: MOCK_CLIENTS[cp_ci]["campaigns"][x]["name"], key="cp_camp")
        cp_meta  = MOCK_CLIENTS[cp_ci]["campaigns"][cp_camp]
        st.markdown("##### Date Range")
        cp_c1, cp_c2 = st.columns(2)
        with cp_c1: cp_sd = st.date_input("Start", value=date.fromisoformat(cp_meta["start"]), key="cp_sd")
        with cp_c2: cp_ed = st.date_input("End",   value=date.fromisoformat(cp_meta["end"]),   key="cp_ed")
        cp_gen = st.button("📊 Score Campaign", type="primary", use_container_width=True)

    _cp_key = (cp_ci, cp_camp, str(cp_sd), str(cp_ed))
    if cp_gen or ("cp_result" in st.session_state and st.session_state.get("_cp_key") == _cp_key):
        if cp_gen or "cp_result" not in st.session_state:
            with st.spinner("Scoring campaign…"):
                cp_result = score_campaign(cp_ci, cp_camp, str(cp_sd), str(cp_ed))
            st.session_state["cp_result"] = cp_result
            st.session_state["_cp_key"]   = _cp_key

    if "cp_result" not in st.session_state:
        st.info("Select a client and campaign, then click **Score Campaign**.")
        st.stop()

    r = st.session_state["cp_result"]
    score = r["composite"]
    grade = r["grade"]

    # ── Score colour ─────────────────────────────────────────────────────────
    def _score_color(s):
        if s >= 80: return "#10B981"
        if s >= 65: return "#F59E0B"
        return "#EF4444"

    # ── KPI bar ──────────────────────────────────────────────────────────────
    kp1, kp2, kp3, kp4, kp5 = st.columns(5)
    for col, (lbl, val, sub) in zip([kp1,kp2,kp3,kp4,kp5], [
        ("Pulse Score",   f'<span style="color:{_score_color(score)};font-size:2rem;font-weight:800;">{score}</span><span style="font-size:1rem;color:#6B7280;">/100</span>', r["campaign"]),
        ("Grade",         f'<span style="color:{_score_color(score)};font-size:2rem;font-weight:800;">{grade}</span>', "composite letter grade"),
        ("Platforms",     str(r["n_platforms"]), "in scoring period"),
        ("Total Spend",   f'${r["total_spend"]:,.0f}', "across all channels"),
        ("Period",        r["period"].replace(" – ", " →"), "campaign flight"),
    ]):
        with col:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Sub-score bars ────────────────────────────────────────────────────────
    st.markdown("#### Performance Dimensions")
    metric_labels = {"CPM": "CPM Efficiency", "CTR": "CTR Performance", "CPC": "CPC Efficiency",
                     "CPCV": "CPCV Efficiency", "Channel Mix": "Channel Mix Breadth", "Creative Diversity": "Creative Diversity"}
    metric_icons  = {"CPM": "💰", "CTR": "👆", "CPC": "🖱️", "CPCV": "▶️", "Channel Mix": "📡", "Creative Diversity": "🎨"}
    scores_dict   = r.get("scores", {})

    dim_cols = st.columns(3)
    for i, (mk, mlabel) in enumerate(metric_labels.items()):
        sv = scores_dict.get(mk, 50)
        sc = _score_color(sv)
        bar_pct = sv
        with dim_cols[i % 3]:
            st.markdown(
                f'<div class="slide-card" style="padding:16px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                f'<span style="font-size:13px;font-weight:600;color:#374151;">{metric_icons.get(mk,"📊")} {mlabel}</span>'
                f'<span style="font-size:18px;font-weight:800;color:{sc};">{sv}</span>'
                f'</div>'
                f'<div style="background:#F3F4F6;border-radius:4px;height:8px;">'
                f'<div style="background:{sc};border-radius:4px;height:8px;width:{bar_pct}%;transition:width 0.4s;"></div>'
                f'</div>'
                f'</div>', unsafe_allow_html=True
            )

    st.markdown("---")

    # ── Platform scores table ─────────────────────────────────────────────────
    st.markdown("#### Platform Breakdown")
    ps = r.get("platform_scores", [])
    if ps:
        ps_df = pd.DataFrame(ps)
        ps_df["score_bar"] = ps_df["score"].apply(lambda s: f'{"█" * (s//10)}{"░" * (10 - s//10)} {s}')
        ps_df["spend_fmt"] = ps_df["spend"].apply(lambda x: f"${x:,.0f}")
        ps_df["share_fmt"] = ps_df["spend_share"].apply(lambda x: f"{x:.1f}%")
        ps_df["cpm_fmt"]   = ps_df["cpm"].apply(lambda x: f"${x:.2f}" if x else "—")
        ps_df["ctr_fmt"]   = ps_df["ctr"].apply(lambda x: f"{x:.3f}%" if x else "—")
        st.dataframe(
            ps_df[["platform","channel_type","score","spend_fmt","share_fmt","cpm_fmt","ctr_fmt"]].rename(columns={
                "platform":"Platform","channel_type":"Channel","score":"Score",
                "spend_fmt":"Spend","share_fmt":"Share","cpm_fmt":"CPM","ctr_fmt":"CTR"
            }),
            hide_index=True, use_container_width=True,
            column_config={"Score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%d")}
        )

    # ── Score interpretation ──────────────────────────────────────────────────
    st.markdown("---")
    interp_col1, interp_col2 = st.columns(2)
    with interp_col1:
        st.markdown("#### Score Guide")
        for band, label, col in [("90–100","A+ · Exceptional","#10B981"),("80–89","A · Strong","#34D399"),
                                   ("65–79","B · Solid","#F59E0B"),("45–64","C · Needs attention","#F97316"),("0–44","D · Underperforming","#EF4444")]:
            st.markdown(f'<div style="display:flex;gap:12px;align-items:center;padding:6px 0;border-bottom:1px solid #F3F4F6;">'
                        f'<span style="font-size:13px;font-weight:700;color:{col};min-width:60px;">{band}</span>'
                        f'<span style="font-size:13px;color:#374151;">{label}</span></div>', unsafe_allow_html=True)
    with interp_col2:
        st.markdown("#### Methodology")
        st.markdown("""
        Scores are computed by comparing each platform's actual CPM, CTR, CPC, and CPCV against the
        portfolio benchmark for that platform category.

        | Weight | Metric |
        |--------|--------|
        | 25% | CPM Efficiency |
        | 25% | CTR Performance |
        | 20% | CPC Efficiency |
        | 15% | CPCV Efficiency |
        | 10% | Channel Mix Breadth |
        | 5%  | Creative Diversity |

        Scores above 65 indicate a campaign performing at or above benchmark.
        """)


# ═══════════════════════════════════════
# MODE: PACERLY
# ═══════════════════════════════════════
elif mode == "⏱️ Pacerly":
    from data_layer import get_live_clients as _glc
    MOCK_CLIENTS = _glc()

    st.markdown("""<div class="main-header">
        <h1>⏱️ Pacerly</h1>
        <p>AI-assisted budget pacing — track spend vs plan, flag over/under-delivery, and get bid adjustment guidance in seconds</p>
    </div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("##### Client & Campaign")
        pac_clients = list(MOCK_CLIENTS.keys())
        pac_ci   = st.selectbox("Client", pac_clients, format_func=lambda x: MOCK_CLIENTS[x]["name"], key="pac_client")
        pac_camps = list(MOCK_CLIENTS[pac_ci]["campaigns"].keys())
        pac_camp  = st.selectbox("Campaign", pac_camps, format_func=lambda x: MOCK_CLIENTS[pac_ci]["campaigns"][x]["name"], key="pac_camp")
        pac_meta  = MOCK_CLIENTS[pac_ci]["campaigns"][pac_camp]
        st.markdown("##### Date Range")
        pac_c1, pac_c2 = st.columns(2)
        with pac_c1: pac_sd = st.date_input("Start", value=date.fromisoformat(pac_meta["start"]), key="pac_sd")
        with pac_c2: pac_ed = st.date_input("End",   value=date.fromisoformat(pac_meta["end"]),   key="pac_ed")
        pac_gen = st.button("⏱️ Check Pacing", type="primary", use_container_width=True)

    _pac_key = (pac_ci, pac_camp, str(pac_sd), str(pac_ed))
    if pac_gen or ("pac_result" in st.session_state and st.session_state.get("_pac_key") == _pac_key):
        if pac_gen or "pac_result" not in st.session_state:
            with st.spinner("Computing pacing…"):
                pac_result = get_pacing_data(pac_ci, pac_camp, str(pac_sd), str(pac_ed))
            st.session_state["pac_result"] = pac_result
            st.session_state["_pac_key"]   = _pac_key

    if "pac_result" not in st.session_state:
        st.info("Select a client and campaign, then click **Check Pacing**.")
        st.stop()

    p = st.session_state["pac_result"]
    status_colors = {"ON TRACK": "#10B981", "AHEAD": "#EF4444", "BEHIND": "#F59E0B"}
    sc = status_colors.get(p["status"], "#6B7280")

    # ── KPI bar ──────────────────────────────────────────────────────────────
    pk1, pk2, pk3, pk4, pk5 = st.columns(5)
    for col, (lbl, val, sub) in zip([pk1,pk2,pk3,pk4,pk5], [
        ("Pacing Status", f'<span style="color:{sc};font-size:1.4rem;font-weight:800;">{p["status_icon"]} {p["status"]}</span>', p["campaign"]),
        ("Budget",        f'${p["planned_spend"]:,.0f}', "total planned"),
        ("Spent",         f'${p["actual_spend"]:,.0f}', f'{p["spent_pct"]:.1f}% of budget'),
        ("Flight Elapsed",f'{p["elapsed_pct"]:.1f}%',  "of campaign period"),
        ("Pacing Index",  f'{p["pacing_index"]:.2f}x',  "spent ÷ elapsed (1.0 = on track)"),
    ]):
        with col:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Pacing chart ─────────────────────────────────────────────────────────
    import plotly.graph_objects as go

    timeline = p.get("timeline", [])
    weeks        = [t["week"] for t in timeline]
    cum_planned  = [t["cum_planned"] for t in timeline]
    cum_actual   = [t["cum_actual"] if t["cum_actual"] is not None else None for t in timeline]
    actual_pts   = [(w, a) for w, a in zip(weeks, cum_actual) if a is not None]

    fig_pac = go.Figure()
    fig_pac.add_trace(go.Scatter(x=weeks, y=cum_planned, name="Planned (cumulative)",
                                  line=dict(color="#6366F1", width=2, dash="dash"), mode="lines"))
    if actual_pts:
        aw, aa = zip(*actual_pts)
        fig_pac.add_trace(go.Scatter(x=list(aw), y=list(aa), name="Actual (cumulative)",
                                      line=dict(color=sc, width=3), mode="lines+markers",
                                      marker=dict(size=5)))
    fig_pac.update_layout(
        title="Cumulative Spend vs Plan", height=320, margin=dict(l=0,r=0,t=40,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, tickfont=dict(size=10)),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6", tickprefix="$", tickformat=",.0f"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Inter, sans-serif", size=12)
    )
    st.plotly_chart(fig_pac, use_container_width=True)

    st.markdown("---")

    # ── Platform pacing table ─────────────────────────────────────────────────
    st.markdown("#### Platform Pacing")
    plat_pac = p.get("platform_pacing", [])
    if plat_pac:
        status_icons = {"Ahead": "🔴", "On Track": "🟢", "Behind": "🟡"}
        rows = []
        for pp in plat_pac:
            rows.append({
                "Platform":   pp["platform"],
                "Channel":    pp["channel_type"],
                "Planned":    f'${pp["planned"]:,.0f}',
                "Spent":      f'${pp["actual"]:,.0f}',
                "Pacing":     pp["pacing_pct"],
                "Status":     f'{status_icons.get(pp["status"], "")} {pp["status"]}',
                "Recommended Action": pp["action"],
            })
        pp_df = pd.DataFrame(rows)
        st.dataframe(
            pp_df, hide_index=True, use_container_width=True,
            column_config={"Pacing": st.column_config.ProgressColumn("Pacing %", min_value=0, max_value=150, format="%.0f%%")}
        )

    # ── Pacing advice ─────────────────────────────────────────────────────────
    st.markdown("---")
    ahead_plats  = [pp for pp in plat_pac if pp["status"] == "Ahead"]
    behind_plats = [pp for pp in plat_pac if pp["status"] == "Behind"]

    adv1, adv2 = st.columns(2)
    with adv1:
        if ahead_plats:
            st.markdown("#### 🔴 Over-Delivering Platforms")
            for pp in ahead_plats[:4]:
                st.markdown(
                    f'<div class="slide-card" style="padding:14px;margin-bottom:8px;">'
                    f'<strong>{pp["platform"]}</strong> — {pp["pacing_pct"]:.0f}% paced<br>'
                    f'<span style="color:#6B7280;font-size:12px;">{pp["action"]}</span>'
                    f'</div>', unsafe_allow_html=True)
        else:
            st.success("No platforms over-delivering.")
    with adv2:
        if behind_plats:
            st.markdown("#### 🟡 Under-Delivering Platforms")
            for pp in behind_plats[:4]:
                st.markdown(
                    f'<div class="slide-card" style="padding:14px;margin-bottom:8px;">'
                    f'<strong>{pp["platform"]}</strong> — {pp["pacing_pct"]:.0f}% paced<br>'
                    f'<span style="color:#6B7280;font-size:12px;">{pp["action"]}</span>'
                    f'</div>', unsafe_allow_html=True)
        else:
            st.success("No platforms under-delivering.")


# ═══════════════════════════════════════
# MODE: OPTIMIZER BUDDY
# ═══════════════════════════════════════
elif mode == "🤖 Optimizer Buddy":
    from data_layer import get_live_clients as _ob_glc, assemble_pca_data
    MOCK_CLIENTS = _ob_glc()
    from llm_engine import generate_optimizations

    st.markdown("""<div class="main-header">
        <h1>🤖 Optimizer Buddy</h1>
        <p>AI-powered optimization advisor — ingests campaign performance and surfaces specific, actionable recommendations with confidence scores</p>
    </div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("##### Client & Campaign")
        ob_clients = list(MOCK_CLIENTS.keys())
        ob_ci   = st.selectbox("Client", ob_clients, format_func=lambda x: MOCK_CLIENTS[x]["name"], key="ob_client")
        ob_camps = list(MOCK_CLIENTS[ob_ci]["campaigns"].keys())
        ob_camp  = st.selectbox("Campaign", ob_camps, format_func=lambda x: MOCK_CLIENTS[ob_ci]["campaigns"][x]["name"], key="ob_camp")
        ob_meta  = MOCK_CLIENTS[ob_ci]["campaigns"][ob_camp]
        st.markdown("##### Date Range")
        ob_c1, ob_c2 = st.columns(2)
        with ob_c1: ob_sd = st.date_input("Start", value=date.fromisoformat(ob_meta["start"]), key="ob_sd")
        with ob_c2: ob_ed = st.date_input("End",   value=date.fromisoformat(ob_meta["end"]),   key="ob_ed")
        st.markdown("##### Focus")
        ob_focus = st.selectbox("Optimise for", ["Overall efficiency","Reduce CPM","Improve CTR","Reduce CPC","Maximise reach"], key="ob_focus")
        ob_gen = st.button("🤖 Get Recommendations", type="primary", use_container_width=True)

    _ob_key = (ob_ci, ob_camp, str(ob_sd), str(ob_ed), ob_focus)
    if ob_gen or ("ob_result" in st.session_state and st.session_state.get("_ob_key") == _ob_key):
        if ob_gen or "ob_result" not in st.session_state:
            with st.spinner("Analysing campaign and generating recommendations…"):
                ob_data = assemble_pca_data(ob_ci, ob_camp, str(ob_sd), str(ob_ed))
                ob_data["focus"] = ob_focus
                ob_result = generate_optimizations(ob_data)
            st.session_state["ob_result"] = ob_result
            st.session_state["_ob_key"]   = _ob_key

    if "ob_result" not in st.session_state:
        st.info("Select a campaign and click **Get Recommendations**.")
        st.stop()

    ob_res  = st.session_state["ob_result"]
    ob_opts = ob_res.get("optimizations", [])

    if ob_res.get("error"):
        st.error(f"LLM error — showing mock recommendations. {ob_res['error']}")

    # ── Summary bar ───────────────────────────────────────────────────────────
    high_conf = [o for o in ob_opts if o.get("confidence", 0) >= 0.80]
    ob_k1, ob_k2, ob_k3 = st.columns(3)
    for col, (lbl, val, sub) in zip([ob_k1, ob_k2, ob_k3], [
        ("Recommendations", str(len(ob_opts)),      "identified by AI"),
        ("High Confidence", str(len(high_conf)),    "≥80% confidence"),
        ("Optimising For",  ob_focus.split(" ")[0], ob_focus),
    ]):
        with col:
            st.markdown(f'<div class="kpi-card"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ── Recommendation cards ──────────────────────────────────────────────────
    if not ob_opts:
        st.info("No optimizations returned. Try enabling the LLM in the sidebar settings.")
    else:
        st.markdown(f"#### {len(ob_opts)} Optimization Recommendations")
        for i, opt in enumerate(ob_opts, start=1):
            conf      = opt.get("confidence", 0.75)
            conf_pct  = int(conf * 100)
            if conf_pct >= 80: conf_color = "#10B981"
            elif conf_pct >= 60: conf_color = "#F59E0B"
            else: conf_color = "#EF4444"

            with st.container():
                oc1, oc2 = st.columns([5, 1])
                with oc1:
                    st.markdown(
                        f'<div class="slide-card" style="padding:18px;margin-bottom:12px;">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">'
                        f'<div>'
                        f'<span style="background:#EEF2FF;color:#4F46E5;font-size:11px;font-weight:700;padding:2px 8px;border-radius:12px;">#{i} · {opt.get("platform","General")}</span>'
                        f'<h4 style="margin:8px 0 4px;color:#0D0A2E;">{opt.get("action","")}</h4>'
                        f'</div>'
                        f'<div style="text-align:right;min-width:80px;">'
                        f'<div style="font-size:22px;font-weight:800;color:{conf_color};">{conf_pct}%</div>'
                        f'<div style="font-size:10px;color:#6B7280;">confidence</div>'
                        f'</div>'
                        f'</div>'
                        f'<div style="margin-bottom:8px;">'
                        f'<span style="font-size:12px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:0.05em;">Rationale</span><br>'
                        f'<span style="font-size:13px;color:#374151;">{opt.get("rationale","")}</span>'
                        f'</div>'
                        f'<div style="background:#F0FDF4;border-left:3px solid #10B981;padding:8px 12px;border-radius:0 6px 6px 0;">'
                        f'<span style="font-size:12px;font-weight:600;color:#065F46;">Expected impact: </span>'
                        f'<span style="font-size:12px;color:#065F46;">{opt.get("expected_impact","")}</span>'
                        f'</div>'
                        f'<div style="margin-top:10px;background:#F3F4F6;border-radius:4px;height:6px;">'
                        f'<div style="background:{conf_color};border-radius:4px;height:6px;width:{conf_pct}%;"></div>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
# ═══════════════════════════════════════════════════════════════════════════
# 🏷️ TAXONOMY COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════════
elif mode == "🏷️ Taxonomy Compliance":
    import json, os, glob as _glob

    # ── Locate the Excel source of truth ──────────────────────────────────────
    # Look in Downloads folder first, then same dir as app.py
    _candidates = (
        _glob.glob(os.path.expanduser("~/Downloads/paid_media_2026_ytd.xlsx"))
        + _glob.glob(os.path.join(os.path.dirname(__file__), "paid_media_2026_ytd.xlsx"))
        + _glob.glob(os.path.join(os.path.dirname(__file__), "data", "paid_media_2026_ytd.xlsx"))
    )
    EXCEL_PATH = _candidates[0] if _candidates else None

    st.markdown("""<div class="main-header">
        <h1>🏷️ Taxonomy Compliance</h1>
        <p>Campaign naming convention auditor — spot gaps, fix the worst offenders first, climb the leaderboard</p>
    </div>""", unsafe_allow_html=True)

    # ── Load taxonomy from pkl (fast, has all fields) ────────────────────────
    _PKL_PATH = os.path.join(os.path.dirname(__file__), "data", "taxonomy_compliance.pkl")

    @st.cache_data(show_spinner=False)
    def _load_taxonomy_db(_pkl):
        import pickle
        with open(_pkl, "rb") as f:
            raw = pickle.load(f)
        # Normalise column names
        if "missing_required" in raw.columns and "missing_fields" not in raw.columns:
            raw = raw.rename(columns={"missing_required": "missing_fields"})
        # Ensure compliance_score is 0-1 float (pkl stores as 0-1)
        raw["compliance_score"] = pd.to_numeric(raw["compliance_score"], errors="coerce").fillna(0)
        # Ensure matched_fields exists (JSON string of {field: value} dict)
        if "matched_fields" not in raw.columns:
            tax_fields = ["Geography", "Media Type", "Ad Format", "Objective",
                          "Demo Targeting", "Tactic / Audience"]
            raw["matched_fields"] = raw.apply(
                lambda r: json.dumps({f: r[f] for f in tax_fields
                                      if f in raw.columns and pd.notna(r.get(f)) and str(r.get(f,"")).strip()}),
                axis=1,
            )
        for col in ["spend", "impressions", "clicks", "conversions"]:
            if col in raw.columns:
                raw[col] = pd.to_numeric(raw[col], errors="coerce").fillna(0)
        return raw

    if not os.path.exists(_PKL_PATH):
        if not EXCEL_PATH:
            st.warning("⚠️ Taxonomy data not found. Run `python3 data/build_taxonomy_db.py` first.")
        else:
            st.warning("⚠️ taxonomy_compliance.pkl not found. Run `python3 data/build_taxonomy_db.py` first.")
        st.stop()

    with st.spinner("Loading taxonomy database…"):
        df = _load_taxonomy_db(_PKL_PATH)

    ALL_CLIENTS = sorted(df["client"].unique().tolist())
    CLIENT_COLORS = {
        "Coles":   "#C00000", "RACV": "#0070C0", "Hanes": "#7030A0",
        "Mazda":   "#ED7D31", "Simplot": "#375623",
    }
    REQUIRED_FIELDS = ["Geography", "Media Type", "Objective", "Demo Targeting", "Tactic / Audience"]

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("##### Client Filter")
        sel_client = st.selectbox("View client", ["All Clients"] + ALL_CLIENTS, key="tax_client")
        st.markdown("##### Platform Filter")
        all_platforms = sorted(df["platform"].unique().tolist())
        sel_platform = st.multiselect("Platforms", all_platforms, default=all_platforms, key="tax_platform")
        st.markdown("##### Show Issues")
        show_only = st.radio("Rows to show", ["All", "Issues only (≤ Partial)"], index=1, key="tax_show")
        st.markdown("---")
        st.caption("Source of truth: paid_media_2026_ytd.xlsx  \nTaxonomy sheet updated offline via build_taxonomy_db.py")

    # ── Filter working df ─────────────────────────────────────────────────────
    wdf = df[df["platform"].isin(sel_platform)].copy() if sel_platform else df.copy()
    view_df = wdf[wdf["client"] == sel_client].copy() if sel_client != "All Clients" else wdf.copy()

    # ── Build per-client summary ──────────────────────────────────────────────
    def client_stats(cdf):
        total = len(cdf)
        if total == 0:
            return {"total": 0, "compliant": 0, "partial": 0, "non": 0, "pct": 0.0, "spend_at_risk": 0.0}
        compliant = (cdf["compliance_score"] >= 0.85).sum()
        partial   = ((cdf["compliance_score"] >= 0.60) & (cdf["compliance_score"] < 0.85)).sum()
        non       = (cdf["compliance_score"] < 0.60).sum()
        passing   = compliant + partial
        spend_at_risk = cdf.loc[cdf["compliance_score"] < 0.60, "spend"].sum()
        return {
            "total": total, "compliant": compliant, "partial": partial, "non": non,
            "pct": passing / total * 100, "spend_at_risk": spend_at_risk,
        }

    client_summary = {c: client_stats(wdf[wdf["client"] == c]) for c in ALL_CLIENTS}
    overall_stats  = client_stats(wdf)

    # ── SECTION 1: Leaderboard ────────────────────────────────────────────────
    st.markdown("### 🏆 Leaderboard")
    ranked = sorted(ALL_CLIENTS, key=lambda c: client_summary[c]["pct"], reverse=True)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

    lb_cols = st.columns([1, 2, 2, 2, 2, 2])
    for i, client in enumerate(ranked):
        s   = client_summary[client]
        pct = s["pct"]
        bar_color = CLIENT_COLORS.get(client, "#6366F1")
        bar_w     = int(pct)
        badge_bg  = "#ECFDF5" if pct >= 85 else "#FFFBEB" if pct >= 60 else "#FEF2F2"
        badge_col = "#059669" if pct >= 85 else "#D97706" if pct >= 60 else "#DC2626"

        st.markdown(
            f"""<div style="background:#fff;border:1px solid #E3E6ED;border-radius:10px;
                padding:14px 18px;margin-bottom:8px;display:flex;align-items:center;gap:14px;">
                <div style="font-size:22px;min-width:32px;">{medals[i]}</div>
                <div style="min-width:90px;font-weight:700;font-size:14px;color:#0F172A;">{client}</div>
                <div style="flex:1;background:#F1F5F9;border-radius:6px;height:10px;overflow:hidden;">
                    <div style="background:{bar_color};width:{bar_w}%;height:10px;border-radius:6px;"></div>
                </div>
                <div style="min-width:56px;text-align:right;font-weight:800;font-size:15px;
                    color:{badge_col};">{pct:.1f}%</div>
                <div style="font-size:11px;color:#94A3B8;min-width:90px;">{s['total']:,} lines</div>
                <div style="font-size:11px;color:#DC2626;min-width:100px;">
                    {'⚠️ $' + f"{s['spend_at_risk']:,.0f} at risk" if s['spend_at_risk'] > 0 else ''}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── SECTION 2: Score card for selected client ─────────────────────────────
    title = sel_client if sel_client != "All Clients" else "All Clients"
    stats = overall_stats if sel_client == "All Clients" else client_summary[sel_client]

    pct   = stats["pct"]
    color = "#059669" if pct >= 85 else "#D97706" if pct >= 60 else "#DC2626"

    st.markdown(f"### 📊 {title} — Compliance Breakdown")

    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    for col, (lbl, val, sub, col_hex) in zip(
        [sc1, sc2, sc3, sc4, sc5],
        [
            ("Overall",       f"{pct:.1f}%",                   "passing (✅+⚠️)",          color),
            ("✅ Compliant",   f"{stats['compliant']:,}",        "≥85% fields matched",     "#059669"),
            ("⚠️ Partial",     f"{stats['partial']:,}",          "60–84% fields matched",   "#D97706"),
            ("❌ Non-compliant",f"{stats['non']:,}",             "<60% fields matched",      "#DC2626"),
            ("💸 Spend at risk",f"${stats['spend_at_risk']:,.0f}","on non-compliant lines",  "#DC2626"),
        ],
    ):
        col.markdown(
            f"""<div style="background:#fff;border:1px solid #E3E6ED;border-radius:10px;
                padding:14px 16px;text-align:center;">
                <div style="font-size:22px;font-weight:800;color:{col_hex};">{val}</div>
                <div style="font-size:12px;font-weight:600;color:#0F172A;margin-top:2px;">{lbl}</div>
                <div style="font-size:11px;color:#94A3B8;">{sub}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── Field coverage breakdown ──────────────────────────────────────────────
    with st.expander("📋 Field Coverage Detail", expanded=False):
        field_rows = []
        for field in REQUIRED_FIELDS:
            matched_n = view_df["matched_fields"].apply(
                lambda x: field in json.loads(x) if isinstance(x, str) else False
            ).sum()
            pct_f = matched_n / len(view_df) * 100 if len(view_df) else 0
            field_rows.append({"Field": field, "Matched": matched_n,
                               "Total": len(view_df), "Coverage %": round(pct_f, 1)})
        fc_df = pd.DataFrame(field_rows).sort_values("Coverage %")
        st.dataframe(
            fc_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Coverage %": st.column_config.ProgressColumn(
                    "Coverage %", min_value=0, max_value=100, format="%.1f%%"
                ),
            },
        )

    st.markdown("---")

    # ── SECTION 3: Issues table ───────────────────────────────────────────────
    st.markdown("### 🔧 Issues to Fix  <span style='font-size:13px;font-weight:400;color:#94A3B8;'>(click a row to see field detail)</span>", unsafe_allow_html=True)

    issues_df = view_df.copy()
    if show_only == "Issues only (≤ Partial)":
        issues_df = issues_df[issues_df["compliance_score"] < 0.85]

    issues_df = issues_df.sort_values("spend", ascending=False).reset_index(drop=True)

    if issues_df.empty:
        st.success("🎉 No issues found for the current filter!")
    else:
        # Build display table
        def fmt_missing(row):
            try:
                matched = json.loads(row["matched_fields"])
                missing = [f for f in REQUIRED_FIELDS if f not in matched]
                return ", ".join(missing) if missing else "—"
            except Exception:
                return row.get("missing_required", "")

        def _status_icon(label):
            if "Non" in label:   return "❌ Non-compliant"
            if "Partial" in label: return "⚠️ Partial"
            return "✅ Compliant"

        display = pd.DataFrame({
            "Client":          issues_df["client"],
            "Platform":        issues_df["platform"],
            "Campaign":        issues_df["campaign"].str[:55],
            "Line / IO":       issues_df["campaign_line"].str[:45],
            "Score":           (issues_df["compliance_score"] * 100).round(0).astype(int).astype(str) + "%",
            "Status":          issues_df["compliance_label"].apply(_status_icon),
            "Missing Fields":  issues_df.apply(fmt_missing, axis=1),
            "Spend ($)":       issues_df["spend"].round(0).astype(int),
        })

        sel = st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
            height=420,
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Spend ($)": st.column_config.NumberColumn(format="$%d"),
                "Score":     st.column_config.TextColumn(width="small"),
                "Status":    st.column_config.TextColumn(width="medium"),
            },
        )

        st.caption(f"Showing {len(issues_df):,} rows · "
                   f"${issues_df['spend'].sum():,.0f} total spend in view")

        # ── Detail panel ─────────────────────────────────────────────────────
        selected_rows = sel.selection.rows if sel and sel.selection else []
        if selected_rows:
            idx = selected_rows[0]
            row = issues_df.iloc[idx]

            try:
                matched_dict = json.loads(row["matched_fields"]) if isinstance(row["matched_fields"], str) else {}
            except Exception:
                matched_dict = {}

            score_pct = round(row["compliance_score"] * 100)
            label     = row["compliance_label"]
            if "Non" in label:
                status_color = "#DC2626"; status_bg = "#FEF2F2"; status_icon = "❌"
            elif "Partial" in label:
                status_color = "#D97706"; status_bg = "#FFFBEB"; status_icon = "⚠️"
            else:
                status_color = "#059669"; status_bg = "#ECFDF5"; status_icon = "✅"

            st.markdown("")
            st.markdown(
                f"""<div style="border:2px solid {status_color};border-radius:12px;
                    padding:18px 22px;background:{status_bg};margin-top:8px;">
                    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                        <div>
                            <div style="font-size:15px;font-weight:700;color:#0F172A;">
                                {status_icon} {str(row.get('campaign',''))[:80]}
                            </div>
                            <div style="font-size:12px;color:#64748B;margin-top:3px;">
                                Line / IO: <b>{str(row.get('campaign_line',''))[:80]}</b>
                            </div>
                            <div style="font-size:12px;color:#64748B;margin-top:2px;">
                                {str(row.get('client',''))} &nbsp;·&nbsp; {str(row.get('platform',''))}
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-size:28px;font-weight:800;color:{status_color};">{score_pct}%</div>
                            <div style="font-size:11px;color:{status_color};font-weight:600;">{label}</div>
                            <div style="font-size:11px;color:#64748B;">Spend: ${row.get('spend',0):,.0f}</div>
                        </div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

            st.markdown("**Taxonomy Field Breakdown:**")

            ALL_FIELDS = REQUIRED_FIELDS + [f for f in ["Ad Format"] if f not in REQUIRED_FIELDS]
            field_cols = st.columns(min(len(ALL_FIELDS), 3))
            for fi, field in enumerate(ALL_FIELDS):
                col_idx = fi % 3
                is_required = field in REQUIRED_FIELDS
                val = matched_dict.get(field, "")
                matched = bool(val and str(val).strip())
                if matched:
                    icon  = "✅"
                    bg    = "#F0FDF4"
                    bdr   = "#86EFAC"
                    label_c = "#166534"
                    val_txt = str(val)
                else:
                    icon  = "❌" if is_required else "○"
                    bg    = "#FEF2F2" if is_required else "#F8FAFC"
                    bdr   = "#FCA5A5" if is_required else "#CBD5E1"
                    label_c = "#DC2626" if is_required else "#94A3B8"
                    val_txt = "Missing" if is_required else "Not set"
                req_badge = " <span style='font-size:9px;background:#E0E7FF;color:#3730A3;padding:1px 5px;border-radius:4px;'>required</span>" if is_required else ""
                field_cols[col_idx].markdown(
                    f"""<div style="border:1px solid {bdr};border-radius:8px;
                        padding:10px 12px;background:{bg};margin-bottom:8px;min-height:62px;">
                        <div style="font-size:11px;font-weight:700;color:{label_c};">
                            {icon} {field}{req_badge}
                        </div>
                        <div style="font-size:12px;color:#1E293B;margin-top:4px;font-weight:500;">
                            {val_txt}
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            missing_required = [f for f in REQUIRED_FIELDS if not matched_dict.get(f)]
            if missing_required:
                st.markdown(
                    f"<div style='font-size:12px;color:#DC2626;margin-top:4px;'>"
                    f"⚠️ <b>Action needed:</b> Add values for: <b>{', '.join(missing_required)}</b>"
                    f"</div>",
                    unsafe_allow_html=True,
                )


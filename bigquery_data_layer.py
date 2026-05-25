"""
BigQuery data layer — queries resodigital_MelbUnified.all_clients_unified.

Implements the same public API as excel_data_layer.py so data_layer.py can
route transparently between DuckDB (local) and BigQuery (live).

Requires: google-cloud-bigquery  (pip install google-cloud-bigquery)
Auth:      Application Default Credentials  (gcloud auth application-default login)
           OR the same service account used by the Vertex AI integration.
"""
from __future__ import annotations

import hashlib, re as _re
from functools import lru_cache
from typing import Any

import pandas as pd

# ── BigQuery config ────────────────────────────────────────────────────────────
PROJECT   = "res-apac-dev-skynet-au"
DATASET   = "resodigital_MelbUnified"
TABLE_ID  = f"`{PROJECT}.{DATASET}.all_clients_unified`"

# ── Lazy BQ client (avoids import cost on startup) ─────────────────────────────
_BQ = None

def _client():
    global _BQ
    if _BQ is None:
        from google.cloud import bigquery
        _BQ = bigquery.Client(project=PROJECT)
    return _BQ

def _run(sql: str) -> pd.DataFrame:
    """Execute a BigQuery SQL statement and return a DataFrame."""
    return _client().query(sql).to_dataframe()

def bq_available() -> bool:
    """Return True if BQ can be reached (fast ping)."""
    try:
        _run(f"SELECT 1 FROM {TABLE_ID} LIMIT 1")
        return True
    except Exception:
        return False

def get_bq_summary() -> dict | None:
    """Return high-level stats about the BQ table (for the sidebar status chip)."""
    try:
        r = _run(f"""
            SELECT
              COUNT(*)          AS row_count,
              MIN(date)         AS date_min,
              MAX(date)         AS date_max,
              COUNT(DISTINCT client)   AS clients,
              COUNT(DISTINCT platform) AS platforms
            FROM {TABLE_ID}
        """).iloc[0]
        return {
            "row_count": int(r.row_count),
            "date_min":  str(r.date_min)[:10],
            "date_max":  str(r.date_max)[:10],
            "clients":   int(r.clients),
            "platforms": int(r.platforms),
        }
    except Exception:
        return None


# ── Campaign ID helpers ────────────────────────────────────────────────────────
def _camp_id(desc: str) -> str:
    return "bq_" + hashlib.md5(desc.lower().encode()).hexdigest()[:10]

def _camp_label(desc: str) -> str:
    s = str(desc).strip()
    return s if s else "Campaign"

def _all_campaigns_id() -> str:
    return "bq_all_campaigns"


# ── WHERE-clause helpers ───────────────────────────────────────────────────────
def _date_where(start_date, end_date) -> str:
    return f"date BETWEEN '{start_date}' AND '{end_date}'"

def _camp_where(campaign_id: str, client_id: str, start_date, end_date) -> str:
    """Return extra AND clause (can be empty) to filter to one campaign group."""
    if campaign_id == _all_campaigns_id():
        return ""
    # Re-derive the campaign_description for this ID
    df = _run(f"""
        SELECT DISTINCT COALESCE(NULLIF(TRIM(campaign_description), ''), campaign_name, 'Unknown') AS cd
        FROM {TABLE_ID}
        WHERE client = '{_esc(client_id)}'
          AND {_date_where(start_date, end_date)}
    """)
    descs = [r.cd for _, r in df.iterrows() if _camp_id(r.cd) == campaign_id]
    if not descs:
        return ""
    safe = " OR ".join(
        f"COALESCE(NULLIF(TRIM(campaign_description), ''), campaign_name, 'Unknown') = '{_esc(d)}'"
        for d in descs
    )
    return f"AND ({safe})"

def _esc(s: str) -> str:
    """Minimal SQL string escaping."""
    return str(s).replace("'", "\\'")


# ── Public API (mirrors excel_data_layer.py) ───────────────────────────────────

def get_clients(start_date, end_date) -> list[dict]:
    """Return [{client_id, client_name}, ...]."""
    try:
        df = _run(f"""
            SELECT DISTINCT client
            FROM {TABLE_ID}
            WHERE {_date_where(start_date, end_date)}
              AND spend > 0
            ORDER BY client
        """)
        return [{"client_id": r.client, "client_name": r.client} for _, r in df.iterrows()]
    except Exception:
        return []


def get_campaigns(client_id: str, start_date, end_date) -> list[dict]:
    """Return list of campaign dicts with campaign_id, campaign_name, start, end."""
    try:
        df = _run(f"""
            SELECT
              COALESCE(NULLIF(TRIM(campaign_description), ''), campaign_name, 'Unknown') AS cd,
              MIN(date)    AS start_date,
              MAX(date)    AS end_date,
              SUM(spend)   AS total_spend,
              COUNT(DISTINCT platform) AS n_platforms
            FROM {TABLE_ID}
            WHERE client = '{_esc(client_id)}'
              AND {_date_where(start_date, end_date)}
            GROUP BY cd
            ORDER BY total_spend DESC
        """)
    except Exception:
        return []

    if df.empty:
        return []

    total_spend = float(df["total_spend"].sum())
    all_start   = str(df["start_date"].min())[:10]
    all_end     = str(df["end_date"].max())[:10]

    result = [{
        "campaign_id":   _all_campaigns_id(),
        "campaign_name": f"📊 All Campaigns (${total_spend:,.0f} total spend)",
        "objective":     "all",
        "start":         all_start,
        "end":           all_end,
    }]

    for _, r in df.iterrows():
        cd  = str(r.cd)
        result.append({
            "campaign_id":   _camp_id(cd),
            "campaign_name": _camp_label(cd),
            "objective":     "awareness",
            "start":         str(r.start_date)[:10],
            "end":           str(r.end_date)[:10],
        })

    return result


def assemble_pca_data(
    client_id: str,
    campaign_id: str,
    start_date,
    end_date,
    channel_filter: str = "all",
) -> dict:
    """Return the full PCA data dict (same schema as excel_data_layer)."""

    empty = {
        "campaign_meta": {
            "client": client_id, "client_id": client_id,
            "campaign": "Unknown", "campaign_id": campaign_id,
            "flight": f"{start_date} to {end_date}", "objective": "awareness",
            "platforms": [], "planned_spend": 0,
        },
        "overview": [], "weekly_trends": [], "monthly_trends": [],
        "breakdowns": {}, "benchmarks": [], "plan_vs_actual": [],
        "raw_data": [], "campaign_lines": [],
    }

    base = (
        f"FROM {TABLE_ID} "
        f"WHERE client = '{_esc(client_id)}' "
        f"  AND {_date_where(start_date, end_date)} "
        f"  {_camp_where(campaign_id, client_id, start_date, end_date)}"
    )

    # ── Overview (by platform) ─────────────────────────────────────────────────
    try:
        ov = _run(f"""
            SELECT
              platform,
              SUM(spend)             AS total_spend,
              SUM(impressions)       AS total_impressions,
              SUM(clicks)            AS total_clicks,
              SUM(video_completions) AS total_video_completions,
              COALESCE(SUM(reach), 0) AS total_reach,
              COALESCE(SUM(conversions), 0) AS total_conversions
            {base}
            GROUP BY platform
            ORDER BY total_spend DESC
        """)
    except Exception:
        return empty

    if ov.empty:
        return empty

    overview = []
    for _, r in ov.iterrows():
        sp = float(r.total_spend or 0)
        im = int(r.total_impressions or 0)
        cl = int(r.total_clicks or 0)
        vc = int(r.total_video_completions or 0)
        re_ = int(r.total_reach or 0)
        overview.append({
            "platform":              r.platform,
            "channel_type":          "digital",
            "total_spend":           round(sp, 2),
            "total_impressions":     im,
            "total_clicks":          cl,
            "total_completed_views": vc,
            "total_spots":           0,
            "total_reach_est":       re_,
            "cpc":  round(sp / max(cl, 1), 2)       if cl > 0 else None,
            "cpm":  round(sp / max(im, 1) * 1000, 2) if im > 0 else None,
            "cpcv": round(sp / max(vc, 1), 2)        if vc > 0 else None,
            "ctr":  round(cl / max(im, 1) * 100, 3)  if im > 0 else None,
        })

    # ── Campaign lines (with taxonomy dimensions) ──────────────────────────────
    try:
        lines_df = _run(f"""
            SELECT
              COALESCE(NULLIF(TRIM(campaign_description), ''), campaign_name, 'Unknown') AS campaign_line,
              platform,
              COALESCE(objective,        '')  AS objective,
              COALESCE(format,           '')  AS media_type,
              COALESCE(ad_type,          '')  AS ad_format,
              COALESCE(publisher_name,   '')  AS publisher_name,
              COALESCE(buy_type,         '')  AS buy_type,
              COALESCE(audience_segment, '')  AS tactic_audience,
              COALESCE(geo_target,       '')  AS geo,
              COALESCE(environment,      '')  AS environment,
              SUM(spend)             AS spend,
              SUM(impressions)       AS impressions,
              SUM(clicks)            AS clicks,
              SUM(video_completions)  AS video_completions,
              COALESCE(SUM(conversions), 0) AS conversions
            {base}
            GROUP BY 1,2,3,4,5,6,7,8,9,10
            ORDER BY spend DESC
        """)
    except Exception:
        lines_df = pd.DataFrame()

    campaign_lines = []
    for _, r in lines_df.iterrows():
        sp = float(r.spend or 0)
        im = int(r.impressions or 0)
        cl = int(r.clicks or 0)
        vc = float(r.video_completions or 0)
        cv = float(r.conversions or 0)
        campaign_lines.append({
            "campaign_line":   str(r.campaign_line or ""),
            "platform":        str(r.platform or ""),
            "channel_type":    "digital",
            "geo":             str(r.geo or ""),
            "media_type":      str(r.media_type or ""),
            "ad_format":       str(r.ad_format or ""),
            "objective":       str(r.objective or ""),
            "demo_targeting":  "",
            "tactic_audience": str(r.tactic_audience or ""),
            "publisher_name":  str(r.publisher_name or ""),
            "buy_type":        str(r.buy_type or ""),
            "environment":     str(r.environment or ""),
            "spend":           round(sp, 2),
            "impressions":     im,
            "clicks":          cl,
            "conversions":     round(cv, 2),
            "cpm":  round(sp / max(im, 1) * 1000, 2) if im > 0 else None,
            "ctr":  round(cl / max(im, 1) * 100, 3)  if im > 0 else None,
            "cpc":  round(sp / max(cl, 1), 2)         if cl > 0 else None,
            "cpcv": round(sp / max(vc, 1), 2)         if vc > 0 else None,
        })

    # ── Weekly trends ──────────────────────────────────────────────────────────
    try:
        wk = _run(f"""
            SELECT
              DATE_TRUNC(date, WEEK(MONDAY)) AS week_start,
              platform,
              SUM(spend)       AS spend,
              SUM(impressions) AS impressions
            {base}
            GROUP BY 1, 2
            ORDER BY 1, 2
        """)
    except Exception:
        wk = pd.DataFrame()

    weekly, prev = [], {}
    for _, r in wk.iterrows():
        wk_s = str(r.week_start)[:10]
        pl   = r.platform
        sp   = float(r.spend or 0)
        im   = int(r.impressions or 0)
        pr   = prev.get(pl, {})
        wow  = round((sp - pr.get("spend", sp)) / max(pr.get("spend", sp), 1) * 100, 1) if pr else 0
        weekly.append({
            "week_start":    wk_s,
            "platform":      pl,
            "spend":         round(sp, 2),
            "impressions":   im,
            "cpm":           round(sp / max(im, 1) * 1000, 2) if im > 0 else None,
            "spend_wow_pct": wow,
        })
        prev[pl] = {"spend": sp}

    # ── Monthly trends ─────────────────────────────────────────────────────────
    try:
        mo = _run(f"""
            SELECT
              FORMAT_DATE('%Y-%m', date) AS month,
              platform,
              SUM(spend)       AS spend,
              SUM(impressions) AS impressions,
              SUM(clicks)      AS clicks
            {base}
            GROUP BY 1, 2
            ORDER BY 1, 2
        """)
    except Exception:
        mo = pd.DataFrame()

    monthly = []
    for _, r in mo.iterrows():
        sp = float(r.spend or 0)
        im = int(r.impressions or 0)
        monthly.append({
            "month":       str(r.month),
            "platform":    r.platform,
            "spend":       round(sp, 2),
            "impressions": im,
            "clicks":      int(r.clicks or 0),
            "cpm":         round(sp / max(im, 1) * 1000, 2) if im > 0 else None,
        })

    # ── Breakdowns ─────────────────────────────────────────────────────────────
    def _bd(field: str) -> list[dict]:
        try:
            df2 = _run(f"""
                SELECT
                  {field}          AS val,
                  SUM(spend)       AS spend,
                  SUM(impressions) AS impressions,
                  SUM(clicks)      AS clicks
                {base}
                  AND {field} IS NOT NULL
                GROUP BY {field}
                ORDER BY spend DESC
            """)
        except Exception:
            return []
        if df2.empty:
            return []
        total = float(df2["spend"].sum())
        return [
            {
                "value":           str(r.val),
                "spend":           round(float(r.spend or 0), 2),
                "impressions":     int(r.impressions or 0),
                "cpm":             round(float(r.spend or 0) / max(int(r.impressions or 1), 1) * 1000, 2)
                                   if (r.impressions or 0) > 0 else None,
                "spend_share_pct": round(float(r.spend or 0) / max(total, 1) * 100, 1),
            }
            for _, r in df2.iterrows()
        ]

    breakdowns: dict[str, list] = {
        "by_platform":     _bd("platform"),
        "by_channel_type": [{"value": "Digital", "spend": sum(o["total_spend"] for o in overview),
                              "impressions": sum(o["total_impressions"] for o in overview),
                              "spend_share_pct": 100.0, "cpm": None}],
        "by_objective":    _bd("objective"),
        "by_media_type":   _bd("format"),
        "by_ad_format":    _bd("ad_type"),
        "by_geography":    _bd("geo_target"),
        "by_publisher":    _bd("publisher_name"),
        "by_buy_type":     _bd("buy_type"),
        "by_tactic":       _bd("audience_segment"),
        "by_environment":  _bd("environment"),
    }
    # Remove empty breakdowns
    breakdowns = {k: v for k, v in breakdowns.items() if v}

    # ── Benchmarks ─────────────────────────────────────────────────────────────
    BENCH: dict[str, dict] = {
        "DV360":          {"cpm": 18.80},
        "Meta":           {"cpm": 14.50, "cpc": 1.65},
        "TikTok":         {"cpm":  6.80},
        "Google Search":  {"cpm":  9.20, "cpc": 1.65},
        "TTD":            {"cpm": 16.20},
        "Pinterest":      {"cpm": 10.50},
        "Snapchat":       {"cpm":  8.40},
        "Bing":           {"cpm": 12.00, "cpc": 1.95},
    }
    benchmarks = []
    for o in overview:
        for metric, bval in BENCH.get(o["platform"], {}).items():
            aval = o.get(metric)
            if aval is None:
                continue
            benchmarks.append({
                "platform":        o["platform"],
                "metric_name":     metric.upper(),
                "benchmark_value": bval,
                "actual_value":    aval,
                "variance_pct":    round((aval - bval) / max(bval, 0.01) * 100, 1),
                "benchmark_type":  "industry_avg",
                "sample_size":     25,
            })

    # ── Assemble label ─────────────────────────────────────────────────────────
    if campaign_id == _all_campaigns_id():
        camp_label = "All Campaigns"
    else:
        # Try to find the original description
        try:
            df_l = _run(f"""
                SELECT DISTINCT
                  COALESCE(NULLIF(TRIM(campaign_description), ''), campaign_name, 'Unknown') AS cd
                {base}
                LIMIT 1
            """)
            camp_label = str(df_l.iloc[0].cd) if not df_l.empty else campaign_id
        except Exception:
            camp_label = campaign_id

    total_spend = sum(o["total_spend"] for o in overview)

    return {
        "campaign_meta": {
            "client":       client_id,
            "client_id":    client_id,
            "campaign":     camp_label,
            "campaign_id":  campaign_id,
            "flight":       f"{start_date} to {end_date}",
            "objective":    "awareness",
            "platforms":    [o["platform"] for o in overview],
            "planned_spend": total_spend,
        },
        "overview":       overview,
        "weekly_trends":  weekly,
        "monthly_trends": monthly,
        "breakdowns":     breakdowns,
        "benchmarks":     benchmarks,
        "campaign_lines": campaign_lines,
        "plan_vs_actual": [],
        "raw_data":       [],
    }


def get_portfolio_actuals(start_date, end_date, channel_filter: str = "all") -> dict:
    """Return per-client, per-platform performance dict (same schema as excel_data_layer)."""
    try:
        df = _run(f"""
            SELECT
              client, platform,
              SUM(spend)             AS spend,
              SUM(impressions)       AS impressions,
              SUM(clicks)            AS clicks,
              SUM(video_completions) AS video_completions,
              COALESCE(SUM(conversions), 0) AS conversions
            FROM {TABLE_ID}
            WHERE {_date_where(start_date, end_date)}
            GROUP BY client, platform
        """)
    except Exception:
        return {}

    result: dict[str, dict] = {}
    for client, grp in df.groupby("client"):
        plats: dict[str, dict] = {}
        for _, r in grp.iterrows():
            sp = float(r.spend or 0)
            im = int(r.impressions or 0)
            cl = int(r.clicks or 0)
            vc = float(r.video_completions or 0)
            plats[r.platform] = {
                "channel": "digital",
                "spend":   round(sp, 2),
                "cpm":  round(sp / max(im, 1) * 1000, 2) if im > 0 else None,
                "ctr":  round(cl / max(im, 1) * 100, 3)  if im > 0 else None,
                "cpc":  round(sp / max(cl, 1), 2)         if cl > 0 else None,
                "cpcv": round(sp / max(vc, 1), 2)         if vc > 0 else None,
            }
        result[client] = {"client_name": client, "platforms": plats}
    return result


def build_live_clients() -> dict:
    """Return a MOCK_CLIENTS-compatible dict for Campaign Pulse / Slide Generator."""
    try:
        df = _run(f"""
            SELECT
              client,
              COALESCE(NULLIF(TRIM(campaign_description), ''), campaign_name, 'Unknown') AS cd,
              MIN(date)    AS start_date,
              MAX(date)    AS end_date,
              SUM(spend)   AS total_spend,
              ARRAY_AGG(DISTINCT platform IGNORE NULLS)           AS platforms
            FROM {TABLE_ID}
            GROUP BY client, cd
        """)
    except Exception:
        return {}

    live: dict[str, dict] = {}
    for client, grp in df.groupby("client"):
        campaigns: dict[str, dict] = {}
        for _, r in grp.iterrows():
            cd   = str(r.cd)
            cid  = _camp_id(cd)
            plats = list(r.platforms) if r.platforms is not None else []
            try:
                months = max(
                    (pd.to_datetime(r.end_date) - pd.to_datetime(r.start_date)).days / 30.4, 1
                )
            except Exception:
                months = 1
            campaigns[cid] = {
                "name":              _camp_label(cd),
                "objective":         "awareness",
                "start":             str(r.start_date)[:10],
                "end":               str(r.end_date)[:10],
                "platforms_digital": plats,
                "platforms_offline": [],
                "monthly_spend":     round(float(r.total_spend or 0) / months),
            }
        live[client] = {"name": client, "category": "BigQuery Live", "campaigns": campaigns}
    return live


# ── Q&A context builder ────────────────────────────────────────────────────────

def get_qa_context(question: str, start_date="2025-01-01", end_date="2026-12-31") -> dict:
    """
    Fetch relevant aggregated data from BigQuery to use as LLM context
    for answering a natural-language question.

    Returns a dict with:
      - portfolio_summary: spend by client + platform
      - taxonomy_summary: objective/format/geo/publisher breakdowns across all clients
      - date_range: the queried range
    """
    q_upper = question.upper()

    # Detect which clients / platforms are mentioned
    ALL_CLIENTS   = ["Mazda", "Simplot", "Coles", "Hanes", "RACV"]
    ALL_PLATFORMS = ["DV360", "Meta", "TikTok", "Google Search", "TTD",
                     "Pinterest", "Snapchat", "Bing"]

    mentioned_clients   = [c for c in ALL_CLIENTS   if c.upper() in q_upper]
    mentioned_platforms = [p for p in ALL_PLATFORMS if p.upper() in q_upper]

    client_filter   = f"AND client IN ({','.join(repr(c) for c in mentioned_clients)})"   if mentioned_clients   else ""
    platform_filter = f"AND platform IN ({','.join(repr(p) for p in mentioned_platforms)})" if mentioned_platforms else ""

    base_where = (
        f"WHERE {_date_where(start_date, end_date)} {client_filter} {platform_filter}"
    )

    context: dict[str, Any] = {"date_range": f"{start_date} to {end_date}"}

    # Portfolio summary
    try:
        df_port = _run(f"""
            SELECT client, platform,
                   SUM(spend)       AS spend,
                   SUM(impressions) AS impressions,
                   SUM(clicks)      AS clicks,
                   SUM(video_completions) AS video_completions
            FROM {TABLE_ID}
            {base_where}
            GROUP BY client, platform
            ORDER BY spend DESC
            LIMIT 100
        """)
        context["portfolio_summary"] = df_port.to_dict(orient="records")
    except Exception:
        context["portfolio_summary"] = []

    # Taxonomy coverage summary
    try:
        df_tax = _run(f"""
            SELECT
              client,
              platform,
              COUNT(*) AS row_count,
              ROUND(100.0 * COUNTIF(objective IS NOT NULL)      / COUNT(*), 1) AS obj_pct,
              ROUND(100.0 * COUNTIF(format IS NOT NULL)         / COUNT(*), 1) AS fmt_pct,
              ROUND(100.0 * COUNTIF(geo_target IS NOT NULL)     / COUNT(*), 1) AS geo_pct,
              ROUND(100.0 * COUNTIF(publisher_name IS NOT NULL) / COUNT(*), 1) AS pub_pct
            FROM {TABLE_ID}
            {base_where}
            GROUP BY client, platform
            ORDER BY client, spend DESC
        """)
        context["taxonomy_coverage"] = df_tax.to_dict(orient="records")
    except Exception:
        context["taxonomy_coverage"] = []

    # Breakdown by objective (if question asks about it)
    if any(kw in q_upper for kw in ["OBJECTIVE", "AWARENESS", "PERFORMANCE", "REACH"]):
        try:
            df_obj = _run(f"""
                SELECT client, objective, SUM(spend) AS spend
                FROM {TABLE_ID}
                {base_where}
                  AND objective IS NOT NULL
                GROUP BY client, objective
                ORDER BY spend DESC
            """)
            context["objective_breakdown"] = df_obj.to_dict(orient="records")
        except Exception:
            pass

    # Monthly trend if time-related question
    if any(kw in q_upper for kw in ["MONTH", "TREND", "OVER TIME", "WEEKLY", "JANUARY", "FEBRUARY",
                                      "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST",
                                      "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"]):
        try:
            df_mo = _run(f"""
                SELECT client, FORMAT_DATE('%Y-%m', date) AS month,
                       SUM(spend) AS spend
                FROM {TABLE_ID}
                {base_where}
                GROUP BY client, month
                ORDER BY client, month
            """)
            context["monthly_trend"] = df_mo.to_dict(orient="records")
        except Exception:
            pass

    return context

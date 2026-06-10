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
    """Execute a BigQuery SQL statement and return a DataFrame.
    create_bqstorage_client=False forces the standard REST download path and
    avoids the gRPC bigquerystorage.googleapis.com DNS failure in some networks.
    """
    return _client().query(sql).to_dataframe(create_bqstorage_client=False)

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
        sp = float(r.total_spend if pd.notna(r.total_spend) else 0)
        im = int(r.total_impressions if pd.notna(r.total_impressions) else 0)
        cl = int(r.total_clicks if pd.notna(r.total_clicks) else 0)
        vc = int(r.total_video_completions if pd.notna(r.total_video_completions) else 0)
        re_ = int(r.total_reach if pd.notna(r.total_reach) else 0)
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
            LIMIT 300
        """)
    except Exception:
        lines_df = pd.DataFrame()

    campaign_lines = []
    for _, r in lines_df.iterrows():
        sp = float(r.spend if pd.notna(r.spend) else 0)
        im = int(r.impressions if pd.notna(r.impressions) else 0)
        cl = int(r.clicks if pd.notna(r.clicks) else 0)
        vc = float(r.video_completions if pd.notna(r.video_completions) else 0)
        cv = float(r.conversions if pd.notna(r.conversions) else 0)
        campaign_lines.append({
            "campaign_line":   str(r.campaign_line) if pd.notna(r.campaign_line) else "",
            "platform":        str(r.platform) if pd.notna(r.platform) else "",
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
        sp   = float(r.spend if pd.notna(r.spend) else 0)
        im   = int(r.impressions if pd.notna(r.impressions) else 0)
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
        sp = float(r.spend if pd.notna(r.spend) else 0)
        im = int(r.impressions if pd.notna(r.impressions) else 0)
        monthly.append({
            "month":       str(r.month),
            "platform":    r.platform,
            "spend":       round(sp, 2),
            "impressions": im,
            "clicks":      int(r.clicks if pd.notna(r.clicks) else 0),
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
                  AND TRIM(CAST({field} AS STRING)) != ''
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
                "spend":           round(float(r.spend if pd.notna(r.spend) else 0), 2),
                "impressions":     int(r.impressions if pd.notna(r.impressions) else 0),
                "clicks":          int(r.clicks if pd.notna(r.clicks) else 0),
                "cpm":             round(float(r.spend if pd.notna(r.spend) else 0) / max(int(r.impressions if pd.notna(r.impressions) else 1), 1) * 1000, 2)
                                   if pd.notna(r.impressions) and r.impressions > 0 else None,
                "ctr":             round(int(r.clicks if pd.notna(r.clicks) else 0) / max(int(r.impressions if pd.notna(r.impressions) else 1), 1) * 100, 3)
                                   if pd.notna(r.impressions) and r.impressions > 0 else None,
                "spend_share_pct": round(float(r.spend if pd.notna(r.spend) else 0) / max(total, 1) * 100, 1),
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
            sp = float(r.spend if pd.notna(r.spend) else 0)
            im = int(r.impressions if pd.notna(r.impressions) else 0)
            cl = int(r.clicks if pd.notna(r.clicks) else 0)
            vc = float(r.video_completions if pd.notna(r.video_completions) else 0)
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
                "monthly_spend":     int(float(r.total_spend if pd.notna(r.total_spend) else 0) / max(months, 1)),
            }
        live[client] = {"name": client, "category": "BigQuery Live", "campaigns": campaigns}
    return live


# ── Q&A context builder ────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _dataset_date_bounds() -> tuple[str, str]:
    """Return (min_date, max_date) for the entire table — cached for the session."""
    try:
        r = _run(f"SELECT MIN(date) AS d_min, MAX(date) AS d_max FROM {TABLE_ID}").iloc[0]
        return str(r.d_min)[:10], str(r.d_max)[:10]
    except Exception:
        return "2025-01-01", "2026-12-31"


def _parse_date_range_from_question(question: str) -> tuple[str, str]:
    """
    Parse natural-language date references in a question into (start_date, end_date).
    Handles: last week, this week, yesterday, last month, this month, this year,
    last year, named months (January…), quarters (Q1-Q4), and explicit years.
    Falls back to last 90 days.
    """
    import calendar as _cal
    from datetime import date as _date, timedelta as _td

    today = _date.today()
    q     = question.lower()

    # Relative week
    if "last week" in q:
        last_mon = today - _td(days=today.weekday() + 7)
        return str(last_mon), str(last_mon + _td(days=6))
    if "this week" in q:
        return str(today - _td(days=today.weekday())), str(today)

    # Yesterday / today
    if "yesterday" in q:
        yd = today - _td(days=1)
        return str(yd), str(yd)
    if "today" in q:
        return str(today), str(today)

    # Last N days
    import re as _re2
    m = _re2.search(r'last\s+(\d+)\s+days?', q)
    if m:
        n = int(m.group(1))
        return str(today - _td(days=n)), str(today)

    # Relative month
    if "last month" in q:
        first_this = _date(today.year, today.month, 1)
        last_end   = first_this - _td(days=1)
        return str(_date(last_end.year, last_end.month, 1)), str(last_end)
    if "this month" in q:
        return str(_date(today.year, today.month, 1)), str(today)

    # Relative year
    if "last year" in q:
        y = today.year - 1
        return f"{y}-01-01", f"{y}-12-31"
    if "this year" in q or "ytd" in q:
        return f"{today.year}-01-01", str(today)

    # Named month (optionally with year)
    MONTH_MAP = {
        "january": 1, "jan": 1, "february": 2, "feb": 2,
        "march": 3,   "mar": 3, "april": 4,    "apr": 4,
        "may": 5,     "june": 6, "jun": 6,      "july": 7,
        "jul": 7,     "august": 8, "aug": 8,    "september": 9,
        "sep": 9,     "sept": 9, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "december": 12, "dec": 12,
    }
    year_m    = _re2.search(r'\b(202\d)\b', q)
    explicit_year = year_m is not None
    # If no explicit year, pick the year that actually has data for this month
    ds_min, ds_max = _dataset_date_bounds()
    ds_max_year = int(ds_max[:4])
    ds_min_year = int(ds_min[:4])

    for name, mnum in MONTH_MAP.items():
        if name in q:
            if explicit_year:
                yr = int(year_m.group(1))
            else:
                # Prefer the year within the dataset that has this month
                # Try dataset max year first, then fall back to min year
                yr = ds_max_year
                if ds_min_year != ds_max_year:
                    # Check if this month is before the dataset start in the max year
                    _, last_day_check = _cal.monthrange(yr, mnum)
                    if f"{yr}-{mnum:02d}-{last_day_check}" < ds_min:
                        yr = ds_min_year
                    elif f"{yr}-{mnum:02d}-01" > ds_max:
                        yr = ds_min_year
            _, last_day = _cal.monthrange(yr, mnum)
            return f"{yr}-{mnum:02d}-01", f"{yr}-{mnum:02d}-{last_day:02d}"

    # Quarters
    for qnum, (qm_s, qm_e) in {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}.items():
        if f"q{qnum}" in q:
            if explicit_year:
                yr = int(year_m.group(1))
            else:
                yr = ds_max_year
                if f"{yr}-{qm_s:02d}-01" > ds_max:
                    yr = ds_min_year
            _, last_day = _cal.monthrange(yr, qm_e)
            return f"{yr}-{qm_s:02d}-01", f"{yr}-{qm_e:02d}-{last_day:02d}"

    # Explicit year only
    if explicit_year:
        yr = int(year_m.group(1))
        return f"{yr}-01-01", f"{yr}-12-31"

    # Default: use entire dataset range so "give me a summary" returns all data
    return ds_min, ds_max


def get_qa_context(question: str, start_date: str | None = None, end_date: str | None = None) -> dict:
    """
    Fetch granular BigQuery data relevant to the question.
    Automatically parses natural-language date references (last week, January, Q2, etc.)
    Returns a rich context dict for the LLM including weekly breakdown and totals.
    """
    from datetime import date as _date
    import re as _re2

    # ── Date range ─────────────────────────────────────────────────────────────
    if start_date is None or end_date is None:
        start_date, end_date = _parse_date_range_from_question(question)

    q_upper = question.upper()
    q_lower = question.lower()

    # ── Detect mentioned clients & platforms ──────────────────────────────────
    # Pull live client list from BQ so we're not hardcoding names
    try:
        df_known = _run(f"SELECT DISTINCT client FROM {TABLE_ID}")
        ALL_CLIENTS = df_known["client"].dropna().tolist()
    except Exception:
        ALL_CLIENTS = ["Mazda", "Simplot", "Coles", "Hanes", "RACV"]

    ALL_PLATFORMS = ["DV360", "Meta", "TikTok", "Google Search", "Google Ads",
                     "TTD", "Pinterest", "Snapchat", "Bing", "YouTube",
                     "Facebook", "Instagram", "TV", "Radio", "OOH"]

    mentioned_clients   = [c for c in ALL_CLIENTS   if c.upper() in q_upper]
    mentioned_platforms = [p for p in ALL_PLATFORMS if p.upper() in q_upper]

    client_filter   = f"AND client IN ({','.join(repr(c) for c in mentioned_clients)})"   if mentioned_clients   else ""
    platform_filter = f"AND UPPER(platform) IN ({','.join(repr(p.upper()) for p in mentioned_platforms)})" if mentioned_platforms else ""

    base_where = f"WHERE {_date_where(start_date, end_date)} {client_filter} {platform_filter}"

    # ── Always expose the full dataset bounds (unfiltered) so LLM can redirect user ──
    ds_min, ds_max = _dataset_date_bounds()

    context: dict[str, Any] = {
        "queried_period":       f"{start_date} to {end_date}",
        "question_received":    question,
        "clients_filtered":     mentioned_clients or "all",
        "platforms_filtered":   mentioned_platforms or "all",
        "dataset_full_range":   f"{ds_min} to {ds_max}",  # always tell LLM what IS available
    }

    # ── Check if any data exists in this period first ──────────────────────────
    try:
        df_check = _run(f"SELECT MIN(date) AS d_min, MAX(date) AS d_max, COUNT(*) AS row_count FROM {TABLE_ID} {base_where}")
        row = df_check.iloc[0]
        rows_in_period = int(row.row_count)
        context["data_availability"] = {
            "rows_in_period": rows_in_period,
            "earliest_date":  str(row.d_min)[:10] if row.d_min else None,
            "latest_date":    str(row.d_max)[:10] if row.d_max else None,
            "dataset_full_range": f"{ds_min} to {ds_max}",
        }
    except Exception:
        rows_in_period = 0
        context["data_availability"] = {"rows_in_period": 0, "dataset_full_range": f"{ds_min} to {ds_max}"}

    # ── Auto-retry with full dataset range if this period is empty ────────────
    # (catches cases like "may" defaulting to wrong year)
    if rows_in_period == 0 and (start_date != ds_min or end_date != ds_max):
        base_where = f"WHERE {_date_where(ds_min, ds_max)} {client_filter} {platform_filter}"
        context["queried_period"] = f"{ds_min} to {ds_max} (auto-expanded: no data found for {start_date}→{end_date})"
        context["auto_expanded"]  = True
        # Re-check
        try:
            df_check2 = _run(f"SELECT COUNT(*) AS row_count FROM {TABLE_ID} {base_where}")
            rows_in_period = int(df_check2.iloc[0].row_count)
            context["data_availability"]["rows_in_period"] = rows_in_period
        except Exception:
            pass

    # ── Spend/impressions/clicks by client + platform ─────────────────────────
    try:
        df_port = _run(f"""
            SELECT
              client, platform,
              SUM(spend)             AS spend,
              SUM(impressions)       AS impressions,
              SUM(clicks)            AS clicks,
              SUM(video_completions) AS video_completions,
              SAFE_DIVIDE(SUM(spend),       SUM(impressions)) * 1000 AS cpm,
              SAFE_DIVIDE(SUM(clicks),      SUM(impressions)) * 100  AS ctr,
              SAFE_DIVIDE(SUM(spend),       SUM(clicks))             AS cpc,
              SAFE_DIVIDE(SUM(spend),       SUM(video_completions))  AS cpcv
            FROM {TABLE_ID}
            {base_where}
            GROUP BY client, platform
            ORDER BY spend DESC
            LIMIT 150
        """)
        context["by_client_platform"] = df_port.to_dict(orient="records")
        # Top-level totals
        context["totals"] = {
            "spend":       float(df_port.spend.sum()),
            "impressions": float(df_port.impressions.sum()),
            "clicks":      float(df_port.clicks.sum()),
        }
    except Exception:
        context["by_client_platform"] = []

    # ── Weekly breakdown (always included — key for "last week" questions) ─────
    try:
        df_wk = _run(f"""
            SELECT
              client,
              DATE_TRUNC(date, WEEK(MONDAY)) AS week_start,
              SUM(spend)       AS spend,
              SUM(impressions) AS impressions,
              SUM(clicks)      AS clicks
            FROM {TABLE_ID}
            {base_where}
            GROUP BY client, week_start
            ORDER BY week_start DESC, spend DESC
            LIMIT 200
        """)
        context["weekly_by_client"] = df_wk.to_dict(orient="records")
    except Exception:
        context["weekly_by_client"] = []

    # ── Daily breakdown for short windows (≤14 days) ──────────────────────────
    try:
        from datetime import datetime as _dt2
        sd = _dt2.strptime(start_date, "%Y-%m-%d").date()
        ed = _dt2.strptime(end_date,   "%Y-%m-%d").date()
        if (ed - sd).days <= 14:
            df_day = _run(f"""
                SELECT client, platform, date,
                       SUM(spend) AS spend, SUM(impressions) AS impressions, SUM(clicks) AS clicks
                FROM {TABLE_ID}
                {base_where}
                GROUP BY client, platform, date
                ORDER BY date DESC, spend DESC
                LIMIT 300
            """)
            context["daily_detail"] = df_day.to_dict(orient="records")
    except Exception:
        pass

    # ── Monthly breakdown (for trend / multi-month questions) ─────────────────
    try:
        df_mo = _run(f"""
            SELECT client, platform,
                   FORMAT_DATE('%Y-%m', date) AS month,
                   SUM(spend) AS spend, SUM(impressions) AS impressions
            FROM {TABLE_ID}
            {base_where}
            GROUP BY client, platform, month
            ORDER BY month DESC, spend DESC
            LIMIT 200
        """)
        context["monthly_by_client_platform"] = df_mo.to_dict(orient="records")
    except Exception:
        pass

    # ── Taxonomy breakdowns ───────────────────────────────────────────────────
    # Each breakdown: spend + impressions by taxonomy field so the LLM can
    # answer questions about objective split, format mix, geo, publisher, etc.
    def _tax_breakdown(field, alias, limit=80):
        try:
            df2 = _run(f"""
                SELECT client, platform, {field} AS {alias},
                       SUM(spend) AS spend, SUM(impressions) AS impressions,
                       SUM(clicks) AS clicks,
                       SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000 AS cpm,
                       SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100  AS ctr
                FROM {TABLE_ID}
                {base_where}
                  AND {field} IS NOT NULL AND TRIM({field}) != ''
                GROUP BY client, platform, {field}
                ORDER BY spend DESC
                LIMIT {limit}
            """)
            return df2.to_dict(orient="records")
        except Exception:
            return []

    context["by_objective"]        = _tax_breakdown("objective",        "objective",        100)
    context["by_format"]           = _tax_breakdown("format",           "format",            80)
    context["by_geo"]              = _tax_breakdown("geo_target",       "geo_target",        80)
    context["by_publisher"]        = _tax_breakdown("publisher_name",   "publisher_name",    80)
    context["by_audience_segment"] = _tax_breakdown("audience_segment", "audience_segment",  60)
    context["by_ad_type"]          = _tax_breakdown("ad_type",          "ad_type",           60)
    context["by_buy_type"]         = _tax_breakdown("buy_type",         "buy_type",          40)

    return context


# ── Taxonomy Coverage ──────────────────────────────────────────────────────────

TAXONOMY_FIELDS = {
    "objective":        "Objective",
    "format":           "Format / Media Type",
    "geo_target":       "Geo Target",
    "publisher_name":   "Publisher",
    "audience_segment": "Audience / Tactic",
    "ad_type":          "Ad Type",
}


def get_taxonomy_coverage_bq(start_date: str, end_date: str) -> dict:
    """
    Return taxonomy field coverage stats for Taxonomy Compliance view.
    Queries BQ directly (no pickle files needed).

    Returns dict with:
      - 'summary': {client: {field: {total, filled, pct, spend_total, spend_missing}}}
      - 'overall': {field: {total, filled, pct, spend_missing}}
      - 'by_platform': {client: {platform: {field: pct}}}
      - 'campaigns_missing': list of {client, platform, campaign, missing_fields, spend, impressions, row_count}
    """
    try:
        df = _run(f"""
            SELECT
              client,
              platform,
              COALESCE(NULLIF(TRIM(campaign_description), ''), campaign_name, 'Unknown') AS campaign,
              SUM(spend) AS spend,
              SUM(impressions) AS impressions,
              COUNT(*) AS row_count,
              COUNTIF(objective IS NOT NULL AND TRIM(objective) != '') AS has_objective,
              COUNTIF(format IS NOT NULL AND TRIM(format) != '') AS has_format,
              COUNTIF(geo_target IS NOT NULL AND TRIM(geo_target) != '') AS has_geo_target,
              COUNTIF(publisher_name IS NOT NULL AND TRIM(publisher_name) != '') AS has_publisher_name,
              COUNTIF(audience_segment IS NOT NULL AND TRIM(audience_segment) != '') AS has_audience_segment,
              COUNTIF(ad_type IS NOT NULL AND TRIM(ad_type) != '') AS has_ad_type,
              SUM(CASE WHEN objective IS NULL OR TRIM(objective) = '' THEN spend ELSE 0 END) AS spend_missing_objective,
              SUM(CASE WHEN format IS NULL OR TRIM(format) = '' THEN spend ELSE 0 END) AS spend_missing_format,
              SUM(CASE WHEN geo_target IS NULL OR TRIM(geo_target) = '' THEN spend ELSE 0 END) AS spend_missing_geo,
              SUM(CASE WHEN publisher_name IS NULL OR TRIM(publisher_name) = '' THEN spend ELSE 0 END) AS spend_missing_publisher,
              SUM(CASE WHEN audience_segment IS NULL OR TRIM(audience_segment) = '' THEN spend ELSE 0 END) AS spend_missing_audience,
              SUM(CASE WHEN ad_type IS NULL OR TRIM(ad_type) = '' THEN spend ELSE 0 END) AS spend_missing_adtype
            FROM {TABLE_ID}
            WHERE date BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY client, platform, campaign
            ORDER BY spend DESC
        """)
    except Exception as e:
        return {}

    if df is None or df.empty:
        return {}

    # Column map: taxonomy field key -> (has_col, spend_missing_col)
    field_col_map = {
        "objective":        ("has_objective",        "spend_missing_objective"),
        "format":           ("has_format",           "spend_missing_format"),
        "geo_target":       ("has_geo_target",       "spend_missing_geo"),
        "publisher_name":   ("has_publisher_name",   "spend_missing_publisher"),
        "audience_segment": ("has_audience_segment", "spend_missing_audience"),
        "ad_type":          ("has_ad_type",          "spend_missing_adtype"),
    }

    # ── Build per-client summary ───────────────────────────────────────────────
    summary: dict = {}
    for client, grp in df.groupby("client"):
        summary[client] = {}
        for fkey, (has_col, miss_col) in field_col_map.items():
            total        = int(grp["row_count"].sum())
            filled       = int(grp[has_col].sum())
            spend_total  = float(grp["spend"].sum())
            spend_miss   = float(grp[miss_col].sum())
            pct          = (filled / max(total, 1)) * 100
            summary[client][fkey] = {
                "total":         total,
                "filled":        filled,
                "pct":           round(pct, 1),
                "spend_total":   round(spend_total, 2),
                "spend_missing": round(spend_miss, 2),
            }

    # ── Overall (portfolio) ────────────────────────────────────────────────────
    overall: dict = {}
    for fkey, (has_col, miss_col) in field_col_map.items():
        total      = int(df["row_count"].sum())
        filled     = int(df[has_col].sum())
        spend_miss = float(df[miss_col].sum())
        overall[fkey] = {
            "total":         total,
            "filled":        filled,
            "pct":           round((filled / max(total, 1)) * 100, 1),
            "spend_missing": round(spend_miss, 2),
        }

    # ── By platform (per client) ───────────────────────────────────────────────
    by_platform: dict = {}
    for (client, platform), grp in df.groupby(["client", "platform"]):
        if client not in by_platform:
            by_platform[client] = {}
        plat_fields = {}
        for fkey, (has_col, _) in field_col_map.items():
            total  = int(grp["row_count"].sum())
            filled = int(grp[has_col].sum())
            plat_fields[fkey] = round((filled / max(total, 1)) * 100, 1)
        by_platform[client][platform] = plat_fields

    # ── Campaigns missing required fields ─────────────────────────────────────
    REQUIRED_FIELDS_BQ = ["objective", "format", "geo_target"]
    camps_missing = []
    for _, row in df.iterrows():
        missing = []
        for fkey in REQUIRED_FIELDS_BQ:
            has_col = field_col_map[fkey][0]
            # A row is "missing" a field if fewer filled than total rows in that segment
            if int(row[has_col]) < int(row["row_count"]):
                missing.append(TAXONOMY_FIELDS[fkey])
        if missing:
            camps_missing.append({
                "client":        row["client"],
                "platform":      row["platform"],
                "campaign":      str(row["campaign"]),
                "missing_fields": missing,
                "spend":         float(row["spend"]),
                "impressions":   int(row["impressions"]),
                "row_count":     int(row["row_count"]),
            })

    # Sort by spend desc, cap at 200
    camps_missing.sort(key=lambda x: x["spend"], reverse=True)
    camps_missing = camps_missing[:200]

    return {
        "summary":           summary,
        "overall":           overall,
        "by_platform":       by_platform,
        "campaigns_missing": camps_missing,
    }


# ── Weekly Meet data ───────────────────────────────────────────────────────────

def get_weekly_meet_data(client_id: str, week_start: str, week_end: str) -> dict:
    """
    Pull all data needed for a Weekly Meet / WIP meeting brief.

    Returns:
        client, week_start, week_end, prev_start, prev_end,
        this_week  (per-platform metrics),
        last_week  (per-platform metrics for previous 7 days),
        wow        (week-on-week variance per platform),
        by_objective, by_format, by_geo, by_publisher,
        top_campaigns (top 10 by spend this week),
        daily_trend   (daily spend per platform),
        totals        (rolled-up summary across all platforms)
    """
    from datetime import datetime, timedelta

    ws = datetime.strptime(week_start, "%Y-%m-%d")
    we = datetime.strptime(week_end,   "%Y-%m-%d")
    prev_end   = (ws - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_start = (ws - timedelta(days=7)).strftime("%Y-%m-%d")

    def _plat(start, end):
        try:
            df = _run(f"""
                SELECT
                  platform,
                  SUM(spend)              AS spend,
                  SUM(impressions)        AS impressions,
                  SUM(clicks)             AS clicks,
                  SUM(video_completions)  AS vcr,
                  SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000 AS cpm,
                  SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100 AS ctr,
                  SAFE_DIVIDE(SUM(spend), SUM(clicks))              AS cpc,
                  SAFE_DIVIDE(SUM(spend), SUM(video_completions))   AS cpcv
                FROM {TABLE_ID}
                WHERE client = '{_esc(client_id)}'
                  AND date BETWEEN '{start}' AND '{end}'
                  AND spend > 0
                GROUP BY platform
                ORDER BY spend DESC
            """)
        except Exception:
            return []
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "platform":    str(r.platform),
                "spend":       round(float(r.spend) if pd.notna(r.spend) else 0.0, 2),
                "impressions": int(r.impressions)   if pd.notna(r.impressions) else 0,
                "clicks":      int(r.clicks)        if pd.notna(r.clicks)      else 0,
                "vcr":         int(r.vcr)           if pd.notna(r.vcr)         else 0,
                "cpm":         round(float(r.cpm),  2) if pd.notna(r.cpm)  else None,
                "ctr":         round(float(r.ctr),  3) if pd.notna(r.ctr)  else None,
                "cpc":         round(float(r.cpc),  2) if pd.notna(r.cpc)  else None,
                "cpcv":        round(float(r.cpcv), 2) if pd.notna(r.cpcv) else None,
            })
        return rows

    this_week = _plat(week_start, week_end)
    last_week = _plat(prev_start, prev_end)

    # Week-on-week variance per platform
    lw_map = {r["platform"]: r for r in last_week}
    wow = []
    for r in this_week:
        pl  = r["platform"]
        lw  = lw_map.get(pl, {})
        def _var(key):
            a = r.get(key)
            b = lw.get(key)
            if a is None or b is None or b == 0:
                return None
            return round((a - b) / abs(b) * 100, 1)
        wow.append({
            "platform":    pl,
            "spend_var":   _var("spend"),
            "cpm_var":     _var("cpm"),
            "ctr_var":     _var("ctr"),
            "cpc_var":     _var("cpc"),
            "imps_var":    _var("impressions"),
        })

    # Taxonomy breakdowns for the week
    def _breakdown(field, alias, limit=30):
        try:
            df2 = _run(f"""
                SELECT {field} AS val,
                  SUM(spend) AS spend, SUM(impressions) AS impressions, SUM(clicks) AS clicks,
                  SAFE_DIVIDE(SUM(spend), SUM(impressions)) * 1000 AS cpm,
                  SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100  AS ctr
                FROM {TABLE_ID}
                WHERE client = '{_esc(client_id)}'
                  AND date BETWEEN '{week_start}' AND '{week_end}'
                  AND spend > 0
                  AND {field} IS NOT NULL
                  AND TRIM(CAST({field} AS STRING)) != ''
                GROUP BY {field}
                ORDER BY spend DESC
                LIMIT {limit}
            """)
        except Exception:
            return []
        total = float(df2["spend"].sum()) if not df2.empty else 1
        return [
            {
                alias:         str(r.val),
                "spend":       round(float(r.spend) if pd.notna(r.spend) else 0.0, 2),
                "impressions": int(r.impressions)   if pd.notna(r.impressions) else 0,
                "clicks":      int(r.clicks)        if pd.notna(r.clicks)      else 0,
                "cpm":         round(float(r.cpm),  2) if pd.notna(r.cpm)  else None,
                "ctr":         round(float(r.ctr),  3) if pd.notna(r.ctr)  else None,
                "spend_pct":   round((float(r.spend) if pd.notna(r.spend) else 0.0) / max(total, 1) * 100, 1),
            }
            for _, r in df2.iterrows()
        ]

    by_objective = _breakdown("objective",      "objective")
    by_format    = _breakdown("format",          "format")
    by_geo       = _breakdown("geo_target",      "geo_target")
    by_publisher = _breakdown("publisher_name",  "publisher_name")

    # Campaign-level summary by campaign_description — this week + previous week for WoW
    def _camp_week(start, end, limit=60):
        try:
            df = _run(f"""
                SELECT
                  COALESCE(NULLIF(TRIM(campaign_description), ''), campaign_name, 'Unknown') AS campaign,
                  SUM(spend) AS spend, SUM(impressions) AS impressions, SUM(clicks) AS clicks,
                  SAFE_DIVIDE(SUM(spend),  SUM(impressions)) * 1000 AS cpm,
                  SAFE_DIVIDE(SUM(clicks), SUM(impressions)) * 100  AS ctr,
                  SAFE_DIVIDE(SUM(spend),  SUM(clicks))              AS cpc,
                  COUNT(DISTINCT platform) AS n_platforms,
                  STRING_AGG(DISTINCT platform ORDER BY platform LIMIT 5) AS platforms
                FROM {TABLE_ID}
                WHERE client = '{_esc(client_id)}'
                  AND date BETWEEN '{start}' AND '{end}'
                  AND spend > 0
                GROUP BY 1
                ORDER BY spend DESC
                LIMIT {limit}
            """)
        except Exception:
            return []
        return [
            {
                "campaign":     str(r.campaign),
                "spend":        round(float(r.spend)        if pd.notna(r.spend)        else 0.0, 2),
                "impressions":  int(r.impressions)          if pd.notna(r.impressions)  else 0,
                "clicks":       int(r.clicks)               if pd.notna(r.clicks)       else 0,
                "cpm":          round(float(r.cpm),  2)     if pd.notna(r.cpm)          else None,
                "ctr":          round(float(r.ctr),  3)     if pd.notna(r.ctr)          else None,
                "cpc":          round(float(r.cpc),  2)     if pd.notna(r.cpc)          else None,
                "n_platforms":  int(r.n_platforms)          if pd.notna(r.n_platforms)  else 0,
                "platforms":    str(r.platforms or ""),
            }
            for _, r in df.iterrows()
        ]

    campaigns_this_week = _camp_week(week_start, week_end)
    campaigns_last_week = _camp_week(prev_start,  prev_end)

    # Build WoW map for campaigns (keyed by campaign description)
    _cmp_lw_map = {r["campaign"]: r for r in campaigns_last_week}
    for c in campaigns_this_week:
        lw = _cmp_lw_map.get(c["campaign"], {})
        lw_sp = lw.get("spend", 0)
        c["lw_spend"]     = round(lw_sp, 2) if lw_sp else None
        c["spend_wow_pct"] = round((c["spend"] - lw_sp) / max(lw_sp, 0.01) * 100, 1) if lw_sp else None

    # Keep a short top_campaigns list for LLM context (top 10 by spend)
    top_campaigns = [
        {"campaign": c["campaign"], "spend": c["spend"], "impressions": c["impressions"],
         "cpm": c["cpm"], "ctr": c["ctr"]}
        for c in campaigns_this_week[:10]
    ]

    # Daily spend trend for the week (for chart)
    try:
        dd_df = _run(f"""
            SELECT
              CAST(date AS STRING) AS day,
              platform,
              SUM(spend) AS spend
            FROM {TABLE_ID}
            WHERE client = '{_esc(client_id)}'
              AND date BETWEEN '{week_start}' AND '{week_end}'
              AND spend > 0
            GROUP BY 1, 2
            ORDER BY 1, 2
        """)
        daily_trend = [
            {"day": str(r.day), "platform": str(r.platform), "spend": round(float(r.spend if pd.notna(r.spend) else 0), 2)}
            for _, r in dd_df.iterrows()
        ]
    except Exception:
        daily_trend = []

    # Rolled-up totals
    total_spend = sum(r["spend"] for r in this_week)
    total_imps  = sum(r["impressions"] for r in this_week)
    total_clicks = sum(r["clicks"] for r in this_week)
    lw_total_spend = sum(r["spend"] for r in last_week)
    totals = {
        "spend":        round(total_spend, 2),
        "impressions":  total_imps,
        "clicks":       total_clicks,
        "cpm":          round(total_spend / max(total_imps, 1) * 1000, 2) if total_imps else None,
        "ctr":          round(total_clicks / max(total_imps, 1) * 100, 3) if total_imps else None,
        "lw_spend":     round(lw_total_spend, 2),
        "spend_wow_pct": round((total_spend - lw_total_spend) / max(lw_total_spend, 1) * 100, 1) if lw_total_spend else None,
        "n_platforms":  len(this_week),
    }

    return {
        "client":       client_id,
        "week_start":   week_start,
        "week_end":     week_end,
        "prev_start":   prev_start,
        "prev_end":     prev_end,
        "this_week":    this_week,
        "last_week":    last_week,
        "wow":          wow,
        "by_objective": by_objective,
        "by_format":    by_format,
        "by_geo":       by_geo,
        "by_publisher": by_publisher,
        "top_campaigns":       top_campaigns,
        "campaigns_this_week": campaigns_this_week,
        "daily_trend":         daily_trend,
        "totals":              totals,
    }

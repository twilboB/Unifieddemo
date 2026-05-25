"""
Live analytics — replaces mock_data functions for Campaign Pulse, Pacerly,
Media Strategy Builder, and Benchmarks modes.

All data comes from BigQuery via data_layer → bigquery_data_layer.
"""
from __future__ import annotations
from datetime import datetime as _dt, timedelta as _td


# ── Industry benchmark reference rates (kept static — no mock randomness) ──────
_BENCHMARKS = {
    "dv360":          {"channel": "digital",  "cpm": 8.50,  "ctr": 0.08, "cpc": None,  "cpcv": 0.04},
    "meta":           {"channel": "digital",  "cpm": 10.20, "ctr": 1.20, "cpc": 1.80,  "cpcv": None},
    "google_ads":     {"channel": "digital",  "cpm": 6.80,  "ctr": 2.10, "cpc": 1.20,  "cpcv": None},
    "tiktok":         {"channel": "digital",  "cpm": 9.50,  "ctr": 0.60, "cpc": None,  "cpcv": 0.05},
    "youtube":        {"channel": "digital",  "cpm": 7.00,  "ctr": None, "cpc": None,  "cpcv": 0.03},
    "pinterest":      {"channel": "digital",  "cpm": 8.00,  "ctr": 0.50, "cpc": 1.50,  "cpcv": None},
    "snapchat":       {"channel": "digital",  "cpm": 7.50,  "ctr": 0.45, "cpc": None,  "cpcv": 0.04},
    "linkedin":       {"channel": "digital",  "cpm": 28.00, "ctr": 0.45, "cpc": 5.50,  "cpcv": None},
    "programmatic":   {"channel": "digital",  "cpm": 5.00,  "ctr": 0.07, "cpc": None,  "cpcv": None},
    "ttd":            {"channel": "digital",  "cpm": 6.50,  "ctr": 0.09, "cpc": None,  "cpcv": None},
    "tv":             {"channel": "offline",  "cpm": 20.00, "ctr": None, "cpc": None,  "cpcv": None},
    "bvod":           {"channel": "digital",  "cpm": 28.00, "ctr": None, "cpc": None,  "cpcv": 0.05},
    "radio":          {"channel": "offline",  "cpm": 4.00,  "ctr": None, "cpc": None,  "cpcv": None},
    "ooh":            {"channel": "offline",  "cpm": 3.50,  "ctr": None, "cpc": None,  "cpcv": None},
    "cinema":         {"channel": "offline",  "cpm": 15.00, "ctr": None, "cpc": None,  "cpcv": None},
    "search":         {"channel": "digital",  "cpm": None,  "ctr": 4.50, "cpc": 2.10,  "cpcv": None},
    "bing":           {"channel": "digital",  "cpm": None,  "ctr": 3.80, "cpc": 1.80,  "cpcv": None},
}

_SEASONALITY = {
    1: 0.85, 2: 0.80, 3: 0.95, 4: 1.00, 5: 1.05, 6: 0.90,
    7: 0.85, 8: 0.90, 9: 1.05, 10: 1.10, 11: 1.25, 12: 1.30,
}


def _live_clients() -> dict:
    from data_layer import get_live_clients
    return get_live_clients()


def _camp_name(client_id: str, campaign_id: str) -> str:
    """Look up campaign display name from live BQ clients dict."""
    lc = _live_clients()
    client = lc.get(client_id, {})
    camp = client.get("campaigns", {}).get(campaign_id, {})
    return camp.get("name", campaign_id)


def _camp_monthly_spend(client_id: str, campaign_id: str) -> float:
    lc = _live_clients()
    client = lc.get(client_id, {})
    camp = client.get("campaigns", {}).get(campaign_id, {})
    return float(camp.get("monthly_spend", 0))


# ─────────────────────────────────────────────────────────────────────────────
def score_campaign(client_id: str, campaign_id: str, start_date: str, end_date: str) -> dict:
    """
    Compute Campaign Pulse scores using live BigQuery data.
    Returns composite score 0-100, sub-scores by metric, per-platform scores.
    """
    from data_layer import assemble_pca_data
    data = assemble_pca_data(client_id, campaign_id, start_date, end_date)

    benchmarks = data.get("benchmarks", [])
    overview   = data.get("overview", [])
    raw        = data.get("raw_data", [])
    camp_name  = _camp_name(client_id, campaign_id)

    if not overview:
        return {
            "composite": 50, "grade": "B", "scores": {}, "platform_scores": [],
            "campaign": camp_name, "period": f"{start_date} – {end_date}",
            "total_spend": 0, "n_platforms": 0,
        }

    # Score each benchmark (0-100 per row)
    metric_buckets: dict[str, list] = {"CPM": [], "CPC": [], "CPCV": [], "CTR": []}
    for b in benchmarks:
        m        = b["metric_name"]
        variance = b.get("variance_pct", 0)
        if m in ("CPM", "CPC", "CPCV"):
            raw_score = 50 - variance * 0.5
        elif m == "CTR":
            raw_score = 50 + variance * 0.5
        else:
            continue
        if m in metric_buckets:
            metric_buckets[m].append(max(0, min(100, round(raw_score))))

    avg_scores = {m: round(sum(v) / len(v)) for m, v in metric_buckets.items() if v}

    # Channel mix: reward breadth
    channel_types = set(r.get("channel_type") for r in overview)
    avg_scores["Channel Mix"] = min(100, len(channel_types) * 25)

    # Creative / format diversity
    formats = set(r.get("creative_format") for r in raw if r.get("creative_format"))
    avg_scores["Creative Diversity"] = min(100, len(formats) * 10)

    weights = {"CPM": 0.25, "CTR": 0.25, "CPC": 0.20, "CPCV": 0.15,
               "Channel Mix": 0.10, "Creative Diversity": 0.05}
    composite = round(sum(avg_scores.get(m, 50) * w for m, w in weights.items()))
    grade = ("A+" if composite >= 90 else "A"  if composite >= 80 else
             "B+" if composite >= 75 else "B"  if composite >= 65 else
             "C+" if composite >= 55 else "C"  if composite >= 45 else "D")

    total_spend = sum(r["total_spend"] for r in overview)
    platform_scores = []
    for row in overview[:10]:
        plat    = row["platform"]
        plat_bs = [b for b in benchmarks if b["platform"] == plat]
        if not plat_bs:
            continue
        vals = []
        for b in plat_bs:
            m = b["metric_name"]; variance = b.get("variance_pct", 0)
            if m in ("CPM", "CPC", "CPCV"):
                vals.append(max(0, min(100, 50 - variance * 0.5)))
            elif m == "CTR":
                vals.append(max(0, min(100, 50 + variance * 0.5)))
        if vals:
            platform_scores.append({
                "platform":     plat,
                "channel_type": row["channel_type"],
                "score":        round(sum(vals) / len(vals)),
                "spend":        row["total_spend"],
                "spend_share":  round(row["total_spend"] / max(total_spend, 1) * 100, 1),
                "cpm":          row.get("cpm"),
                "ctr":          row.get("ctr"),
                "cpc":          row.get("cpc"),
            })

    return {
        "composite":       composite,
        "grade":           grade,
        "scores":          avg_scores,
        "platform_scores": sorted(platform_scores, key=lambda x: -x["spend"]),
        "campaign":        camp_name,
        "period":          f"{start_date} – {end_date}",
        "total_spend":     round(total_spend, 2),
        "n_platforms":     len(overview),
    }


# ─────────────────────────────────────────────────────────────────────────────
def get_pacing_data(client_id: str, campaign_id: str, start_date: str, end_date: str) -> dict:
    """
    Returns weekly planned vs actual spend for pacing analysis.
    Planned = even distribution of campaign budget across flight with seasonality.
    Actual  = from assemble_pca_data weekly_trends.
    """
    from data_layer import assemble_pca_data
    data    = assemble_pca_data(client_id, campaign_id, start_date, end_date)
    overview = data.get("overview", [])

    camp_name     = _camp_name(client_id, campaign_id)
    monthly_spend = _camp_monthly_spend(client_id, campaign_id)

    start_dt   = _dt.strptime(start_date, "%Y-%m-%d")
    end_dt     = _dt.strptime(end_date,   "%Y-%m-%d")
    total_days = max((end_dt - start_dt).days, 1)

    # If monthly_spend is 0, estimate from actual total spend
    if monthly_spend == 0:
        total_actual = sum(r.get("total_spend", 0) for r in overview)
        monthly_spend = total_actual / max(total_days / 30.44, 1)

    planned_spend = monthly_spend * (total_days / 30.44)

    # Build weekly planned (seasonality-weighted)
    weeks_list: list[str] = []
    cur = start_dt
    while cur <= end_dt:
        weeks_list.append(cur.strftime("%Y-%m-%d"))
        cur += _td(days=7)

    total_sf = sum(_SEASONALITY.get(_dt.strptime(w, "%Y-%m-%d").month, 1.0) for w in weeks_list)
    weekly_planned = {
        w: round(planned_spend * _SEASONALITY.get(_dt.strptime(w, "%Y-%m-%d").month, 1.0) / max(total_sf, 1), 2)
        for w in weeks_list
    }

    # Actual from weekly_trends
    actual_by_week: dict[str, float] = {}
    for row in data.get("weekly_trends", []):
        wk = row["week_start"]
        actual_by_week[wk] = actual_by_week.get(wk, 0) + row["spend"]

    today_str = _dt.today().strftime("%Y-%m-%d")

    all_weeks = sorted(set(list(weekly_planned.keys()) + list(actual_by_week.keys())))
    timeline  = []
    cum_p = 0.0; cum_a = 0.0
    for wk in all_weeks:
        p = weekly_planned.get(wk, 0)
        a = actual_by_week.get(wk, 0) if wk <= today_str else None
        cum_p += p
        if a is not None:
            cum_a += a
        timeline.append({
            "week":        wk,
            "planned":     round(p, 2),
            "actual":      round(a, 2) if a is not None else None,
            "cum_planned": round(cum_p, 2),
            "cum_actual":  round(cum_a, 2) if wk <= today_str else None,
        })

    elapsed_pct  = min(100, ((_dt.today() - start_dt).days / total_days) * 100)
    spent_pct    = (cum_a / max(planned_spend, 1)) * 100
    pacing_index = spent_pct / max(elapsed_pct, 0.1)

    if   pacing_index >= 1.10: status, status_icon = "AHEAD",    "🔴"
    elif pacing_index >= 0.92: status, status_icon = "ON TRACK", "🟢"
    else:                      status, status_icon = "BEHIND",   "🟡"

    total_actual_spend = sum(r["total_spend"] for r in overview)
    platform_pacing = []
    for row in overview[:10]:
        plat_share = row["total_spend"] / max(total_actual_spend, 1)
        plat_budget = round(planned_spend * plat_share, 2)
        plat_actual = round(row["total_spend"], 2)
        plat_pct    = round(plat_actual / max(plat_budget, 1) * 100, 1)
        plat_idx    = plat_pct / max(elapsed_pct, 0.1)
        if   plat_idx >= 1.10: plat_status = "AHEAD"
        elif plat_idx >= 0.90: plat_status = "ON TRACK"
        else:                  plat_status = "BEHIND"
        platform_pacing.append({
            "platform":       row["platform"],
            "channel_type":   row["channel_type"],
            "budget":         plat_budget,
            "actual":         plat_actual,
            "spent_pct":      plat_pct,
            "pacing_index":   round(plat_idx, 2),
            "status":         plat_status,
        })

    return {
        "campaign":      camp_name,
        "planned_spend": round(planned_spend, 2),
        "actual_spend":  round(cum_a, 2),
        "spent_pct":     round(spent_pct, 1),
        "elapsed_pct":   round(elapsed_pct, 1),
        "pacing_index":  round(pacing_index, 2),
        "status":        status,
        "status_icon":   status_icon,
        "timeline":      timeline,
        "platform_pacing": sorted(platform_pacing, key=lambda x: -x["actual"]),
        "start_date":    start_date,
        "end_date":      end_date,
    }


# ─────────────────────────────────────────────────────────────────────────────
def get_portfolio_overview() -> list[dict]:
    """Client-level portfolio summary from BigQuery live clients dict."""
    lc = _live_clients()
    results = []
    for cid, cdata in lc.items():
        camps = list(cdata.get("campaigns", {}).values())
        if not camps:
            continue
        total_spend  = sum(c.get("monthly_spend", 0) for c in camps)
        plats = set()
        for c in camps:
            plats.update(c.get("platforms_digital", []))
            plats.update(c.get("platforms_offline", []))
        results.append({
            "client":           cdata.get("name", cid),
            "category":         cdata.get("category", "BigQuery Live"),
            "campaigns":        len(camps),
            "est_annual_spend": round(total_spend * 12),
            "total_platforms":  len(plats),
            "digital_platforms": len([p for p in plats if p not in ("tv", "radio", "ooh", "cinema", "print")]),
            "offline_platforms": len([p for p in plats if p in ("tv", "radio", "ooh", "cinema", "print")]),
        })
    return sorted(results, key=lambda x: -x["est_annual_spend"])


# ─────────────────────────────────────────────────────────────────────────────
def get_portfolio_benchmarks(channel_filter: str = "all") -> list[dict]:
    """
    Platform-level benchmark table: portfolio actuals vs industry rates.
    Actuals computed from BigQuery via get_portfolio_actuals.
    """
    from data_layer import get_portfolio_actuals
    from datetime import date

    try:
        actuals = get_portfolio_actuals("2025-01-01", str(date.today()), channel_filter)
        by_plat = {r["platform"]: r for r in actuals.get("by_platform", [])}
    except Exception:
        by_plat = {}

    results = []
    for plat, rates in _BENCHMARKS.items():
        ch = rates.get("channel", "digital")
        if channel_filter == "digital" and ch != "digital":
            continue
        if channel_filter == "offline" and ch != "offline":
            continue

        actual = by_plat.get(plat, {})
        o_cpm  = actual.get("cpm")
        o_ctr  = actual.get("ctr")
        o_cpc  = actual.get("cpc")
        o_cpcv = actual.get("cpcv")

        def _var(our, ind):
            if our is None or not ind:
                return None
            return round((our - ind) / ind * 100, 1)

        results.append({
            "platform":          plat,
            "channel":           ch,
            "clients_active":    actual.get("clients", 0),
            "our_cpm":           o_cpm,
            "industry_cpm":      rates.get("cpm"),
            "cpm_vs_benchmark":  _var(o_cpm,  rates.get("cpm")),
            "our_ctr":           o_ctr,
            "industry_ctr":      rates.get("ctr"),
            "ctr_vs_benchmark":  _var(o_ctr,  rates.get("ctr")),
            "our_cpc":           o_cpc,
            "industry_cpc":      rates.get("cpc"),
            "cpc_vs_benchmark":  _var(o_cpc,  rates.get("cpc")),
            "our_cpcv":          o_cpcv,
            "industry_cpcv":     rates.get("cpcv"),
        })

    return sorted(results, key=lambda x: -(x.get("clients_active") or 0))

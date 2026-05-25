"""
Excel workbook generator for PCA Builder.
Produces formatted workbook with 6 tabs from PCA source data.
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side, numbers
from openpyxl.utils import get_column_letter

HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
HEADER_FILL = PatternFill("solid", fgColor="1B1464")
BODY_FONT = Font(name="Arial", size=10)
BOLD_FONT = Font(name="Arial", bold=True, size=10)
CURRENCY = '$#,##0'
DECIMAL = '$#,##0.00'
NUMBER = '#,##0'
PCT = '0.0%'
PCT2 = '0.00%'
thin = Side(style="thin", color="DDDDDD")
BORDER = Border(top=thin, bottom=thin, left=thin, right=thin)


def _write_headers(ws, headers, row=1):
    for col, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=col, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER


def _auto_width(ws):
    for col in range(1, ws.max_column + 1):
        max_len = 0
        for row in range(1, min(ws.max_row + 1, 50)):
            val = ws.cell(row=row, column=col).value
            if val:
                max_len = max(max_len, len(str(val)))
        ws.column_dimensions[get_column_letter(col)].width = min(max(max_len + 2, 10), 25)


def build_pca_workbook(source_data: dict, output_path: str) -> str:
    wb = Workbook()

    # ── Tab 1: Campaign Overview ──
    ws = wb.active
    ws.title = "1. Overview"
    headers = ["Platform", "Spend", "Impressions", "Clicks", "Completed Views", "CPC", "CPM", "CPCV"]
    _write_headers(ws, headers)
    fmts = [None, CURRENCY, NUMBER, NUMBER, NUMBER, DECIMAL, DECIMAL, DECIMAL]

    for i, row in enumerate(source_data["overview"], 2):
        ws.cell(row=i, column=1, value=row.get("platform", "").replace("_", " ").title()).border = BORDER
        ws.cell(row=i, column=2, value=row.get("total_spend", 0)).border = BORDER
        ws.cell(row=i, column=3, value=row.get("total_impressions", 0)).border = BORDER
        ws.cell(row=i, column=4, value=row.get("total_clicks", 0)).border = BORDER
        ws.cell(row=i, column=5, value=row.get("total_completed_views", 0)).border = BORDER
        ws.cell(row=i, column=6, value=row.get("cpc", "")).border = BORDER
        ws.cell(row=i, column=7, value=row.get("cpm", "")).border = BORDER
        ws.cell(row=i, column=8, value=row.get("cpcv", "")).border = BORDER

    for col, fmt in enumerate(fmts, 1):
        if fmt:
            for row in range(2, len(source_data["overview"]) + 2):
                ws.cell(row=row, column=col).number_format = fmt

    total_row = len(source_data["overview"]) + 2
    ws.cell(row=total_row, column=1, value="TOTAL").font = BOLD_FONT
    for col in [2, 3, 4, 5]:
        letter = get_column_letter(col)
        ws.cell(row=total_row, column=col, value=f"=SUM({letter}2:{letter}{total_row-1})")
        ws.cell(row=total_row, column=col).font = BOLD_FONT
        ws.cell(row=total_row, column=col).number_format = fmts[col-1]

    ws.auto_filter.ref = f"A1:H{total_row - 1}"
    ws.freeze_panes = "A2"
    _auto_width(ws)

    # ── Tab 2: Weekly Trends ──
    ws2 = wb.create_sheet("2. Weekly Trends")
    headers2 = ["Week", "Platform", "Spend", "Impressions", "CPM", "Prev Week Spend", "Spend WoW %"]
    _write_headers(ws2, headers2)
    fmts2 = [None, None, CURRENCY, NUMBER, DECIMAL, CURRENCY, '0.0"%"']

    for i, row in enumerate(source_data["weekly_trends"], 2):
        ws2.cell(row=i, column=1, value=row.get("week_start", "")).border = BORDER
        ws2.cell(row=i, column=2, value=row.get("platform", "").replace("_", " ").title()).border = BORDER
        ws2.cell(row=i, column=3, value=row.get("spend", 0)).border = BORDER
        ws2.cell(row=i, column=4, value=row.get("impressions", 0)).border = BORDER
        ws2.cell(row=i, column=5, value=row.get("cpm", 0)).border = BORDER
        ws2.cell(row=i, column=6, value=row.get("prev_spend", "")).border = BORDER
        ws2.cell(row=i, column=7, value=row.get("spend_wow_pct", "")).border = BORDER

    for col, fmt in enumerate(fmts2, 1):
        if fmt:
            for row in range(2, len(source_data["weekly_trends"]) + 2):
                ws2.cell(row=row, column=col).number_format = fmt

    ws2.auto_filter.ref = f"A1:G{len(source_data['weekly_trends']) + 1}"
    ws2.freeze_panes = "A2"
    _auto_width(ws2)

    # ── Tab 3: Breakdowns ──
    ws3 = wb.create_sheet("3. Breakdowns")
    current_row = 1
    for dim_name, dim_data in source_data["breakdowns"].items():
        label = dim_name.replace("by_", "").replace("_", " ").title()
        ws3.cell(row=current_row, column=1, value=f"BY {label.upper()}")
        ws3.cell(row=current_row, column=1).font = Font(name="Arial", bold=True, size=12, color="1B1464")
        current_row += 1

        dim_headers = [label, "Spend", "Impressions", "CPM", "CPC", "CPCV", "Spend Share %"]
        _write_headers(ws3, dim_headers, row=current_row)
        current_row += 1

        for row in dim_data:
            ws3.cell(row=current_row, column=1, value=row.get("value", "")).border = BORDER
            ws3.cell(row=current_row, column=2, value=row.get("spend", 0)).border = BORDER
            ws3.cell(row=current_row, column=2).number_format = CURRENCY
            ws3.cell(row=current_row, column=3, value=row.get("impressions", 0)).border = BORDER
            ws3.cell(row=current_row, column=3).number_format = NUMBER
            ws3.cell(row=current_row, column=4, value=row.get("cpm", 0)).border = BORDER
            ws3.cell(row=current_row, column=4).number_format = DECIMAL
            ws3.cell(row=current_row, column=5, value=row.get("cpc", "")).border = BORDER
            ws3.cell(row=current_row, column=5).number_format = DECIMAL
            ws3.cell(row=current_row, column=6, value=row.get("cpcv", "")).border = BORDER
            ws3.cell(row=current_row, column=6).number_format = DECIMAL
            ws3.cell(row=current_row, column=7, value=row.get("spend_share_pct", 0)).border = BORDER
            ws3.cell(row=current_row, column=7).number_format = '0.0"%"'
            current_row += 1
        current_row += 1

    _auto_width(ws3)

    # ── Tab 4: Benchmarks ──
    ws4 = wb.create_sheet("4. Benchmarks")
    headers4 = ["Platform", "Metric", "Actual", "Benchmark", "Variance %", "Type", "Sample Size"]
    _write_headers(ws4, headers4)

    for i, row in enumerate(source_data["benchmarks"], 2):
        ws4.cell(row=i, column=1, value=row.get("platform", "").replace("_", " ").title()).border = BORDER
        ws4.cell(row=i, column=2, value=row.get("metric_name", "")).border = BORDER
        ws4.cell(row=i, column=3, value=row.get("actual_value", 0)).border = BORDER
        ws4.cell(row=i, column=3).number_format = DECIMAL
        ws4.cell(row=i, column=4, value=row.get("benchmark_value", 0)).border = BORDER
        ws4.cell(row=i, column=4).number_format = DECIMAL
        ws4.cell(row=i, column=5, value=row.get("variance_pct", 0)).border = BORDER
        ws4.cell(row=i, column=5).number_format = '0.0"%"'
        ws4.cell(row=i, column=6, value=row.get("benchmark_type", "")).border = BORDER
        ws4.cell(row=i, column=7, value=row.get("sample_size", "")).border = BORDER

    ws4.auto_filter.ref = f"A1:G{len(source_data['benchmarks']) + 1}"
    ws4.freeze_panes = "A2"
    _auto_width(ws4)

    # ── Tab 5: Plan vs Actual ──
    ws5 = wb.create_sheet("5. Plan vs Actual")
    if source_data.get("plan_vs_actual"):
        headers5 = ["Platform", "Planned Spend", "Actual Spend", "Variance %"]
        _write_headers(ws5, headers5)
        for i, row in enumerate(source_data["plan_vs_actual"], 2):
            ws5.cell(row=i, column=1, value=row.get("platform", "").replace("_", " ").title()).border = BORDER
            ws5.cell(row=i, column=2, value=row.get("planned_spend", 0)).border = BORDER
            ws5.cell(row=i, column=2).number_format = CURRENCY
            ws5.cell(row=i, column=3, value=row.get("actual_spend", 0)).border = BORDER
            ws5.cell(row=i, column=3).number_format = CURRENCY
            ws5.cell(row=i, column=4, value=row.get("spend_variance_pct", 0)).border = BORDER
            ws5.cell(row=i, column=4).number_format = '0.0"%"'
        ws5.auto_filter.ref = f"A1:D{len(source_data['plan_vs_actual']) + 1}"
        ws5.freeze_panes = "A2"
    else:
        ws5.cell(row=1, column=1, value="No media plan data available for this campaign")
        # FIXED: Changed italics=True to italic=True
        ws5.cell(row=1, column=1).font = Font(name="Arial", italic=True, color="888888")
    _auto_width(ws5)

    # ── Tab 6: Raw Campaign Data ──
    ws6 = wb.create_sheet("6. Raw Data")
    raw_headers = ["Date", "Platform", "Campaign", "Tactic", "Targeting", "Device",
                   "Creative Format", "State", "Spend", "Impressions", "Clicks",
                   "Completed Views", "CPC", "CPM", "CPCV", "CTR %"]
    _write_headers(ws6, raw_headers)
    raw_fmts = {9: CURRENCY, 10: NUMBER, 11: NUMBER, 12: NUMBER,
                13: DECIMAL, 14: DECIMAL, 15: DECIMAL, 16: '0.00"%"'}

    raw_data = source_data.get("raw_data", [])
    for i, row in enumerate(raw_data[:10000], 2):
        keys = ["date", "platform", "campaign_name", "tactic", "targeting", "device",
                "creative_format", "state", "spend", "impressions", "clicks",
                "completed_views", "cpc", "cpm", "cpcv", "ctr"]
        for j, key in enumerate(keys, 1):
            c = ws6.cell(row=i, column=j, value=row.get(key, ""))
            c.border = BORDER
            if j in raw_fmts:
                c.number_format = raw_fmts[j]

    ws6.auto_filter.ref = f"A1:{get_column_letter(len(raw_headers))}{min(len(raw_data) + 1, 10001)}"
    ws6.freeze_panes = "A2"
    _auto_width(ws6)

    wb.save(output_path)
    return output_path


# ─── Accent fills for media strategy workbook ───────────────────────────────
_NAVY_FILL   = PatternFill("solid", fgColor="1B1464")
_ORANGE_FILL = PatternFill("solid", fgColor="F05C2C")
_PURPLE_FILL = PatternFill("solid", fgColor="4338CA")
_GREY_FILL   = PatternFill("solid", fgColor="F4F5F7")

_SECTION_FONT  = Font(name="Arial", bold=True, color="FFFFFF", size=11)
_SUBHEAD_FONT  = Font(name="Arial", bold=True, color="1B1464", size=10)
_BODY_FONT2    = Font(name="Arial", size=10)
_BODY_BOLD     = Font(name="Arial", bold=True, size=10)

def _section_row(ws, row, text, fill=None):
    c = ws.cell(row=row, column=1, value=text)
    c.font = _SECTION_FONT
    c.fill = fill or _NAVY_FILL
    c.alignment = Alignment(vertical="center")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ws.max_column or 8)
    ws.row_dimensions[row].height = 22


def build_media_strategy_excel(strategy: dict, output_path: str) -> str:
    wb = Workbook()

    client_name = strategy.get("client_name", "Client")
    headline    = strategy.get("strategy_headline", "Media Strategy")

    # ══════════════════════════════════════════════════════════
    # Tab 1: Strategy Overview
    # ══════════════════════════════════════════════════════════
    ws1 = wb.active
    ws1.title = "1. Strategy Overview"
    ws1.column_dimensions["A"].width = 28
    ws1.column_dimensions["B"].width = 80

    def _kv(row, key, value, key_fill=None):
        k = ws1.cell(row=row, column=1, value=key)
        k.font = _BODY_BOLD
        k.border = BORDER
        if key_fill:
            k.fill = key_fill
            k.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
        v = ws1.cell(row=row, column=2, value=str(value) if value else "")
        v.font = _BODY_FONT2
        v.border = BORDER
        v.alignment = Alignment(wrap_text=True, vertical="top")
        ws1.row_dimensions[row].height = max(30, min(120, len(str(value or "")) // 2))

    r = 1
    ws1.cell(row=r, column=1, value=f"MEDIA STRATEGY — {client_name.upper()}").font = Font(name="Arial", bold=True, color="1B1464", size=14)
    ws1.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
    ws1.row_dimensions[r].height = 28
    r += 1

    ws1.cell(row=r, column=1, value=headline).font = Font(name="Arial", italic=True, color="4338CA", size=11)
    ws1.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
    r += 2

    # Executive Summary
    _kv(r, "Executive Summary", strategy.get("executive_summary", ""), _NAVY_FILL)
    r += 2

    # Brief Summary
    bs = strategy.get("brief_summary", {})
    _kv(r, "Objectives", "\n".join(f"• {o}" for o in bs.get("objectives", [])))
    r += 1
    _kv(r, "Target Audience", bs.get("target_audience", ""))
    r += 1
    _kv(r, "Key Messages", "\n".join(f"• {m}" for m in bs.get("key_messages", [])))
    r += 1
    _kv(r, "Campaign Period", bs.get("campaign_period", ""))
    r += 1
    _kv(r, "Budget Indication", bs.get("budget_indication", ""))
    r += 2

    # Strategic Approach
    sa = strategy.get("strategic_approach", {})
    _kv(r, "Strategic Positioning", sa.get("positioning", ""), _PURPLE_FILL)
    r += 1
    _kv(r, "Channel Philosophy", sa.get("channel_philosophy", ""))
    r += 1
    _kv(r, "Key Tensions", "\n".join(f"• {t}" for t in sa.get("key_tensions", [])))
    r += 2

    # Recommendations
    recs = strategy.get("recommendations", [])
    if recs:
        c = ws1.cell(row=r, column=1, value="RECOMMENDATIONS")
        c.font = _SECTION_FONT
        c.fill = _ORANGE_FILL
        ws1.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
        r += 1
        for i, rec in enumerate(recs, 1):
            prio = rec.get("priority", "")
            prio_col = "DC2626" if prio == "HIGH" else ("F05C2C" if prio == "MEDIUM" else "4338CA")
            k = ws1.cell(row=r, column=1, value=f"[{prio}] {rec.get('recommendation', '')}")
            k.font = Font(name="Arial", bold=True, color=prio_col, size=10)
            k.border = BORDER
            ws1.merge_cells(start_row=r, start_column=1, end_row=r, end_column=2)
            r += 1
            _kv(r, "Rationale", rec.get("rationale", ""))
            r += 1

    _auto_width(ws1)

    # ══════════════════════════════════════════════════════════
    # Tab 2: Channel Mix
    # ══════════════════════════════════════════════════════════
    ws2 = wb.create_sheet("2. Channel Mix")
    ch_headers = ["Channel", "Budget %", "Role", "Platforms", "Formats", "KPIs",
                  "Rationale", "Past Performance", "Market Benchmark"]
    _write_headers(ws2, ch_headers)

    for i, ch in enumerate(strategy.get("channel_mix", []), 2):
        ws2.cell(row=i, column=1, value=ch.get("channel", "")).border = BORDER
        ws2.cell(row=i, column=1).font = _BODY_BOLD
        ws2.cell(row=i, column=2, value=ch.get("budget_pct", 0) / 100).border = BORDER
        ws2.cell(row=i, column=2).number_format = "0%"
        ws2.cell(row=i, column=3, value=ch.get("role", "")).border = BORDER
        ws2.cell(row=i, column=4, value=", ".join(ch.get("platforms", []))).border = BORDER
        ws2.cell(row=i, column=5, value=", ".join(ch.get("recommended_formats", []))).border = BORDER
        ws2.cell(row=i, column=6, value=", ".join(ch.get("kpis", []))).border = BORDER
        ws2.cell(row=i, column=7, value=ch.get("rationale", "")).border = BORDER
        ws2.cell(row=i, column=7).alignment = Alignment(wrap_text=True)
        ws2.cell(row=i, column=8, value=ch.get("past_performance", "")).border = BORDER
        ws2.cell(row=i, column=8).alignment = Alignment(wrap_text=True)
        ws2.cell(row=i, column=9, value=ch.get("market_benchmark", "")).border = BORDER
        ws2.cell(row=i, column=9).alignment = Alignment(wrap_text=True)
        ws2.row_dimensions[i].height = 45

    ws2.auto_filter.ref = f"A1:I{len(strategy.get('channel_mix', [])) + 1}"
    ws2.freeze_panes = "A2"

    for col_i, w in enumerate([20, 10, 25, 25, 25, 20, 40, 35, 35], 1):
        ws2.column_dimensions[get_column_letter(col_i)].width = w

    # ══════════════════════════════════════════════════════════
    # Tab 3: Budget Allocation
    # ══════════════════════════════════════════════════════════
    ws3 = wb.create_sheet("3. Budget Allocation")
    _write_headers(ws3, ["Channel", "Budget %", "Est. Spend"])

    alloc = strategy.get("budget_allocation", [])
    for i, row in enumerate(alloc, 2):
        ws3.cell(row=i, column=1, value=row.get("channel", "")).border = BORDER
        ws3.cell(row=i, column=1).font = _BODY_BOLD
        ws3.cell(row=i, column=2, value=row.get("pct", 0) / 100).border = BORDER
        ws3.cell(row=i, column=2).number_format = "0%"
        ws3.cell(row=i, column=3, value=row.get("est_spend", "")).border = BORDER

    total_r = len(alloc) + 2
    ws3.cell(row=total_r, column=1, value="TOTAL").font = _BODY_BOLD
    ws3.cell(row=total_r, column=2, value=f"=SUM(B2:B{total_r-1})").number_format = "0%"
    ws3.cell(row=total_r, column=2).font = _BODY_BOLD

    ws3.auto_filter.ref = f"A1:C{len(alloc) + 1}"
    ws3.freeze_panes = "A2"
    _auto_width(ws3)

    # ══════════════════════════════════════════════════════════
    # Tab 4: Monthly Flight Plan
    # ══════════════════════════════════════════════════════════
    ws4 = wb.create_sheet("4. Monthly Flight Plan")
    _write_headers(ws4, ["Month", "Phase", "Relative Weight", "Active Channels", "Activity Description"])

    flight = strategy.get("monthly_flight", [])
    weight_fills = {
        "Heavy":  PatternFill("solid", fgColor="FEE2E2"),
        "Medium": PatternFill("solid", fgColor="FEF3C7"),
        "Light":  PatternFill("solid", fgColor="F0FDF4"),
        "Off":    PatternFill("solid", fgColor="F9FAFB"),
    }
    for i, row in enumerate(flight, 2):
        weight = row.get("relative_weight", "Medium")
        fill   = weight_fills.get(weight, _GREY_FILL)
        ws4.cell(row=i, column=1, value=row.get("month", "")).border = BORDER
        ws4.cell(row=i, column=1).font = _BODY_BOLD
        ws4.cell(row=i, column=2, value=row.get("phase", "")).border = BORDER
        ws4.cell(row=i, column=3, value=weight).border = BORDER
        ws4.cell(row=i, column=3).fill = fill
        ws4.cell(row=i, column=3).alignment = Alignment(horizontal="center")
        channels = row.get("channels_active", [])
        ws4.cell(row=i, column=4, value=", ".join(channels) if isinstance(channels, list) else str(channels)).border = BORDER
        ws4.cell(row=i, column=5, value=row.get("activity", "")).border = BORDER
        ws4.cell(row=i, column=5).alignment = Alignment(wrap_text=True)
        ws4.row_dimensions[i].height = 35

    ws4.freeze_panes = "A2"
    for col_i, w in enumerate([14, 22, 16, 35, 55], 1):
        ws4.column_dimensions[get_column_letter(col_i)].width = w

    # ══════════════════════════════════════════════════════════
    # Tab 5: Insights & Learnings
    # ══════════════════════════════════════════════════════════
    ws5 = wb.create_sheet("5. Insights & Learnings")
    r5 = 1

    def _insights_section(title, rows, col_a, col_b, fill):
        nonlocal r5
        c = ws5.cell(row=r5, column=1, value=title)
        c.font = _SECTION_FONT
        c.fill = fill
        ws5.merge_cells(start_row=r5, start_column=1, end_row=r5, end_column=2)
        ws5.row_dimensions[r5].height = 22
        r5 += 1
        _write_headers(ws5, [col_a, col_b], row=r5)
        r5 += 1
        for item in rows:
            a_val = item.get("insight", item.get("learning", item.get("risk", ""))) if item else ""
            b_val = item.get("implication", item.get("applied_as", item.get("mitigation", ""))) if item else ""
            ws5.cell(row=r5, column=1, value=a_val).border = BORDER
            ws5.cell(row=r5, column=1).alignment = Alignment(wrap_text=True, vertical="top")
            ws5.cell(row=r5, column=2, value=b_val).border = BORDER
            ws5.cell(row=r5, column=2).alignment = Alignment(wrap_text=True, vertical="top")
            ws5.row_dimensions[r5].height = 50
            r5 += 1
        r5 += 1

    _insights_section("MARKET INSIGHTS", strategy.get("market_insights", []),
                      "Insight", "Implication", _PURPLE_FILL)
    _insights_section("PAST CAMPAIGN LEARNINGS", strategy.get("past_campaign_learnings", []),
                      "Learning", "Applied As", _NAVY_FILL)
    _insights_section("RISKS & MITIGATIONS", strategy.get("risks_and_mitigations", []),
                      "Risk", "Mitigation", _ORANGE_FILL)

    ws5.column_dimensions["A"].width = 55
    ws5.column_dimensions["B"].width = 55

    wb.save(output_path)
    return output_path
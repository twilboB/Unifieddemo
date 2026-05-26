"""
LLM narrative generation for PCA Builder.
"""
import json
import os
import time
import streamlit as st

_VERTEX_PROJECT  = "res-apac-dev-skynet-au"
_VERTEX_LOCATION = "us-central1"
_VERTEX_MODEL    = "gemini-2.5-pro"                  # confirmed available on res-apac-dev-skynet-au

def _gemini_client():
    """Return Vertex AI client using Application Default Credentials (gcloud ADC)."""
    from google import genai
    return genai.Client(vertexai=True, project=_VERTEX_PROJECT, location=_VERTEX_LOCATION)

def _model_name():
    """Return the active model name."""
    return _VERTEX_MODEL

def _last_usage(metadata):
    """Return usage_metadata only when it has real token counts (not 0/None)."""
    if metadata is None:
        return None
    if getattr(metadata, 'prompt_token_count', None):
        return metadata
    return None

# Fallback model chain — tried in order when the primary model returns 503/429
_FALLBACK_MODELS = [
    "gemini-2.5-pro",    # primary — confirmed available
    "gemini-2.5-flash",  # lighter fallback — confirmed available
]

def _call_with_retry(call_fn, model_name: str, max_retries: int = 3):
    """
    Call call_fn(model) with exponential back-off on 503/429.
    Falls back through _FALLBACK_MODELS on 404 (model not found) or sustained 503.
    call_fn must accept a single model-name string and return the response.
    """
    candidates = [model_name] + [m for m in _FALLBACK_MODELS if m != model_name]
    last_exc = None
    for model in candidates:
        for attempt in range(max_retries):
            try:
                return call_fn(model)
            except Exception as e:
                msg = str(e)
                last_exc = e
                # Transient errors — back-off and retry same model
                if "503" in msg or "UNAVAILABLE" in msg or "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    time.sleep(2 ** attempt)
                    if attempt == max_retries - 1:
                        break   # exhausted retries → try next model
                # Model not found / no access → skip to next model immediately
                elif "404" in msg or "NOT_FOUND" in msg or "not found" in msg.lower():
                    break
                else:
                    raise   # non-retryable, unknown error — re-raise
    raise last_exc or RuntimeError(f"All models unavailable: {candidates}")

def calculate_gemini_cost(prompt_tokens: int, output_tokens: int, model_name: str) -> float:
    """
    Calculates estimated cost based on Vertex AI pricing (per 1M tokens).

    Sources (as at Apr 2026):
      gemini-2.5-pro            <=200K ctx  $1.25 in /  $10.00 out
                                 >200K ctx  $2.50 in /  $15.00 out
      gemini-2.5-flash           all ctx    $0.30 in /  $2.50 out
      gemini-2.0-flash                      $0.10 in /  $0.40 out
      gemini-1.5-pro            <=128K ctx  $1.25 in /  $5.00 out
                                 >128K ctx  $2.50 in /  $10.00 out
    """
    name = model_name.lower()
    total_tokens = prompt_tokens + output_tokens

    # ── Gemini 3.x ────────────────────────────────────────────────────────────
    if "3.1-pro" in name:
        # tiered: <=200K tokens uses lower rate
        if total_tokens <= 200_000:
            return (prompt_tokens / 1_000_000) * 2.00 + (output_tokens / 1_000_000) * 12.00
        else:
            return (prompt_tokens / 1_000_000) * 4.00 + (output_tokens / 1_000_000) * 18.00

    if "3.1-flash-lite" in name:
        return (prompt_tokens / 1_000_000) * 0.25 + (output_tokens / 1_000_000) * 1.50

    if "3-flash" in name or "3.1-flash" in name:
        return (prompt_tokens / 1_000_000) * 0.50 + (output_tokens / 1_000_000) * 3.00

    # ── Gemini 2.5 ────────────────────────────────────────────────────────────
    if "2.5-pro" in name:
        if total_tokens <= 200_000:
            return (prompt_tokens / 1_000_000) * 1.25 + (output_tokens / 1_000_000) * 10.00
        else:
            return (prompt_tokens / 1_000_000) * 2.50 + (output_tokens / 1_000_000) * 15.00

    if "2.5-flash" in name:
        return (prompt_tokens / 1_000_000) * 0.15 + (output_tokens / 1_000_000) * 0.60

    # ── Gemini 2.0 ────────────────────────────────────────────────────────────
    if "2.0-flash-lite" in name:
        return (prompt_tokens / 1_000_000) * 0.075 + (output_tokens / 1_000_000) * 0.30

    if "2.0-flash" in name:
        return (prompt_tokens / 1_000_000) * 0.10 + (output_tokens / 1_000_000) * 0.40

    # ── Gemini 1.5 ────────────────────────────────────────────────────────────
    if "1.5-pro" in name or "1.5 pro" in name:
        if total_tokens <= 128_000:
            return (prompt_tokens / 1_000_000) * 1.25 + (output_tokens / 1_000_000) * 5.00
        else:
            return (prompt_tokens / 1_000_000) * 2.50 + (output_tokens / 1_000_000) * 10.00

    if "1.5-flash" in name or "1.5 flash" in name:
        return (prompt_tokens / 1_000_000) * 0.075 + (output_tokens / 1_000_000) * 0.30

    # ── Unknown model — safe fallback to 3.1-pro rate ─────────────────────────
    return (prompt_tokens / 1_000_000) * 2.00 + (output_tokens / 1_000_000) * 12.00

def _mock_narrative(source_data: dict, error_msg: str = None) -> dict:
    msg = error_msg if error_msg else "Campaign performed well across core digital channels."
    is_error = error_msg is not None
    return {
        "_metadata": {"cost": 0.0000, "tokens": 0},
        "_error": is_error,
        "_error_msg": msg if is_error else "",
        "slides": [
            {
                "title": "API ERROR / MOCK DATA",
                "bullet_points": [
                    "The Gemini API request failed or was disabled.",
                    f"Error Details: {msg}",
                    "Please check your API quota or rate limits."
                ]
            }
        ]
    }

def generate_narrative(source_data: dict, focus: str = None, _progress_ph=None) -> dict:
    if not st.session_state.get("settings_llm_enabled", False):
        return _mock_narrative(source_data, "LLM toggle is turned off in sidebar.")

    provider = st.session_state.get("settings_llm_provider")
    model_name = _model_name()

    if provider == "Vertex AI (Gemini)":
        try:
            from google import genai
            from google.genai import types
            
            client = _gemini_client()
            
            focus_instruction = f"\nFocus heavily on: {focus}\n" if focus else ""
            
            prompt = f"""You are a senior media strategist and storyteller writing a Post-Campaign Analysis deck.
            {focus_instruction}
            Respond ONLY with a valid JSON object. No markdown, no ```json fences.

            ═══════════════════════════════════════
            PHILOSOPHY: BUILD THE STORY FIRST
            ═══════════════════════════════════════
            A great PCA is not a data dump. It is a story with a spine.
            It opens with a verdict, raises tensions, investigates them, resolves them, and closes with clear action.
            Every slide must earn its place by advancing the narrative.

            BEFORE YOU WRITE A SINGLE SLIDE, decide:
            1. What is the single most important thing to know about this campaign? (verdict)
            2. What 2-3 tensions or surprises will you unpack? (things that need explaining — a platform that underdelivered, an unexpected efficiency win, a channel mix question)
            3. Which slides raise each tension, and which slides resolve it?
            4. What does the audience know at the START of the deck vs. the END?

            Fill out narrative_plan completely FIRST. Then generate slides that serve it.

            ═══════════════════════════════════════
            NARRATIVE ARC — follow this structure:
            ═══════════════════════════════════════
            ACT 1 — OPENING (slides 1-2):
              Slide 1 (intro): State the verdict upfront. Tease the 2-3 tensions you'll unpack. Make the reader want to keep going.
              Slide 2 (data): Budget & channel allocation. Set the stage — what did we invest and where?

            ACT 2 — INVESTIGATION (slides 3-9):
              Platform-by-platform or theme-by-theme deep dives. Each slide should REVEAL something.
              At least 2 slides must RAISE a tension ("but", "however", "despite strong reach...").
              At least 2 slides must RESOLVE a tension raised earlier, referencing it explicitly.
              Include: weekly spend trend (line chart), key platform performance slides, a benchmark comparison, and at least one breakdown (creative, device, audience, or geo).

            ACT 3 — RESOLUTION & ACTION (slides 10-13):
              Synthesise what the data adds up to. Connect back to the opening tensions.
              Final 1-2 slides are recommendations — specific, numbered, each grounded in a named finding.

            ═══════════════════════════════════════
            BULLET WRITING RULES
            ═══════════════════════════════════════
            Lead with the INSIGHT, support with the DATA. Never lead with a raw number.

            WEAK (data dump):
              "Meta spend: $45,000. Impressions: 4.7M. CPM: $9.57."

            STRONG (narrative):
              "Meta carried the campaign's reach story — 4.7M impressions at $9.57 CPM, 8% below benchmark — but hid a problem."
              "Despite that reach efficiency, Meta's CTR of 0.62% trailed the industry norm of 0.85%. Volume was there; engagement wasn't."
              "This sets up a question the creative breakdown will answer: was this a targeting issue, or a message one?"

            Rules:
            - Use "however", "but", "despite", "yet" to create narrative pull.
            - End at least one bullet per data slide with a bridge forward or a question to be resolved.
            - Recommendation slides must reference specific slide findings by name (e.g. "Given Meta's CTR shortfall identified on slide 5...").
            - 3-5 bullets per slide. No more.

            ═══════════════════════════════════════
            FULL JSON STRUCTURE
            ═══════════════════════════════════════
            {{
                "narrative_plan": {{
                    "verdict": "One-sentence campaign verdict — the most important thing to know",
                    "opening_tension": "The hook — the tension or surprise that will pull the reader through the deck",
                    "key_tensions": [
                        {{"tension": "...", "raised_on_slide": 4, "resolved_on_slide": 7}},
                        {{"tension": "...", "raised_on_slide": 5, "resolved_on_slide": 9}}
                    ],
                    "arc": "One sentence describing the 3-act shape of the deck",
                    "storylines": [
                        {{"finding": "...", "tension": "...", "resolution": "..."}}
                    ]
                }},
                "sections": [
                    "Section 1 Title",
                    "Section 2 Title",
                    "Section 3 Title"
                ],
                "callout": {{
                    "superhead": "3-6 word phrase (e.g. 'The efficiency story')",
                    "statement": "One bold, punchy sentence max 15 words — the single most important insight of the campaign"
                }},
                "recommendations": {{
                    "columns": [
                        {{"number": "01", "title": "What Worked", "body": "2-3 short findings separated by newlines"}},
                        {{"number": "02", "title": "What Didn't", "body": "2-3 short findings"}},
                        {{"number": "03", "title": "Test Agenda", "body": "2-3 specific tests with hypothesis"}},
                        {{"number": "04", "title": "Verdict", "body": "Overall campaign assessment in 2-3 lines"}}
                    ]
                }},
                "slides": [
                    {{
                        "slide_number": 1,
                        "section": "Section Title (must match one entry in sections array)",
                        "slide_type": "intro",
                        "narrative_role": "State the verdict and tease the tensions — set the hook",
                        "callback_to": null,
                        "title": "Campaign Verdict: [punchy title]",
                        "so_what": "The single insight this slide leaves the reader with",
                        "bullet_points": ["...", "..."],
                        "chart_type": null,
                        "chart_data": null
                    }},
                    {{
                        "slide_number": 5,
                        "slide_type": "data",
                        "narrative_role": "Raises the Meta engagement tension — strong reach, weak CTR",
                        "callback_to": null,
                        "title": "Meta: Reach at Scale, But Engagement Left on the Table",
                        "so_what": "Meta delivered volume efficiently but CTR underperformed benchmark by 27% — a creative format question",
                        "bullet_points": [
                            "Meta led all platforms with 4.7M impressions at a $9.57 CPM — 8% below the $10.40 benchmark, a reach efficiency win.",
                            "However, a CTR of 0.62% fell 27% short of the 0.85% industry norm, meaning the audience saw the ad but didn't act.",
                            "Spend of $45,000 (38% of total budget) makes this the highest-weighted platform — which amplifies both the efficiency win and the engagement miss.",
                            "The creative breakdown on the next slide will investigate whether format or audience drove the shortfall."
                        ],
                        "chart_type": "column",
                        "chart_data": {{
                            "categories": ["Meta", "TikTok", "YouTube", "Google Search", "DV360"],
                            "values": [45000, 18000, 13200, 23800, 9000],
                            "series_name": "Spend ($)"
                        }}
                    }},
                    {{
                        "slide_number": 7,
                        "slide_type": "data",
                        "narrative_role": "Resolves the Meta engagement tension — it was static creative, not targeting",
                        "callback_to": 5,
                        "title": "Creative Breakdown: Static Format Dragged Meta's CTR",
                        "so_what": "Reels/video formats on Meta CTR'd at 1.1% vs 0.4% for static — a format mismatch, not an audience problem",
                        "bullet_points": [
                            "Returning to the Meta engagement question raised on slide 5: the creative breakdown isolates the cause.",
                            "Reels and video formats drove a 1.1% CTR — 29% above benchmark — while static ads delivered just 0.4%.",
                            "Static accounted for 65% of Meta impressions. Flipping that ratio to favour video would have added an estimated 18,000 additional clicks at the same spend.",
                            "This is a format allocation issue, not a targeting one — the audience was right, the creative mix wasn't."
                        ],
                        "chart_type": "column",
                        "chart_data": {{
                            "categories": ["Reels/Video", "Carousel", "Static", "Stories"],
                            "values": [1.1, 0.85, 0.4, 0.72],
                            "series_name": "CTR (%)"
                        }}
                    }},
                    {{
                        "slide_number": 13,
                        "slide_type": "recommendation",
                        "narrative_role": "Close the loop — specific actions grounded in named findings",
                        "callback_to": null,
                        "title": "Recommendations: Three Actions for the Next Flight",
                        "so_what": "Three specific, data-backed changes that would materially improve performance",
                        "bullet_points": [
                            "1. Shift Meta creative mix to 70% video/Reels (from 35%) — the creative breakdown on slide 7 showed video CTR at 1.1% vs 0.4% for static.",
                            "2. Rebalance Google Search budget up 15% — it delivered the highest-quality traffic at a CPC of $2.10, yet was under-invested vs plan.",
                            "3. Introduce a weekly pacing review — the spend trend on slide 4 showed mid-campaign underspend that compressed delivery and inflated CPMs in weeks 5-6."
                        ],
                        "chart_type": null,
                        "chart_data": null
                    }}
                ]
            }}

            ═══════════════════════════════════════
            SLIDE INVENTORY — cover ALL of these that have data
            ═══════════════════════════════════════
            You must generate a separate slide for each of the following where data exists.
            Do not collapse multiple topics onto one slide. Each deserves its own slide.

            OPENING (2 slides):
              [S1] Campaign verdict & hook — executive summary, tease tensions
              [S2] Budget allocation — total spend, channel mix (digital vs offline), platform breakdown

            CHANNEL OVERVIEW (1-2 slides):
              [S3] Digital channel scorecard — all digital platforms ranked by spend, with CPM/CTR/CPC
              [S4] Offline channel scorecard — all TV/radio/OOH platforms (only if offline data exists)

            WEEKLY TREND (1 slide):
              [S5] Weekly spend trend (line chart) — pacing story, peaks and troughs, WoW changes

            PLATFORM DEEP-DIVES (1 slide per significant platform — do not skip any):
              For each platform that received meaningful spend, generate a dedicated slide covering:
              spend, impressions, CPM vs benchmark, CTR or CPCV, key insight, and what it means.
              Typical platforms: Meta, Google Search, YouTube, TikTok, DV360, CTV/BVOD, TV networks, OOH.

            EFFICIENCY COMPARISON (2 slides):
              [Sn] CPM comparison — all platforms ranked by CPM vs benchmark (column chart)
              [Sn+1] Click/engagement efficiency — CPC or CTR across all relevant platforms

            BREAKDOWNS (1 slide each — cover all that have data):
              The source_data["breakdowns"] dict contains: by_platform, by_objective, by_media_type (format),
              by_ad_format (ad_type), by_geography (geo_target), by_publisher, by_buy_type, by_tactic (audience_segment),
              by_environment. Use the actual keys present — do not fabricate breakdowns that aren't in the data.
              Each breakdown entry has: value, spend, impressions, clicks, cpm, ctr, spend_share_pct.
              [Sn] Media type / format breakdown — CTR or spend by format (video vs static vs carousel etc) → use by_media_type or by_ad_format
              [Sn] Environment/device breakdown — spend or CTR by environment (desktop vs mobile vs CTV etc) → use by_environment
              [Sn] Geo breakdown — spend or impressions by geo target / state → use by_geography
              [Sn] Tactic / audience breakdown — prospecting vs retargeting vs lookalike performance → use by_tactic
              [Sn] Objective breakdown — spend split by campaign objective → use by_objective
              [Sn] Publisher breakdown — spend or CPM by publisher → use by_publisher

            BENCHMARK COMPARISON (1-2 slides):
              [Sn] Platform actuals vs benchmarks — CPM, CTR, CPC side by side
              [Sn+1] What beat benchmark, what missed, and by how much

            SYNTHESIS (1-2 slides):
              [Sn] What worked — top 3 efficiency or delivery wins with data
              [Sn+1] What didn't — underperformers, missed targets, tensions resolved

            ═══════════════════════════════════════
            CHART RULES
            ═══════════════════════════════════════
            - ALL "data" slides MUST have chart_data. Never null on a data slide.
            - chart values MUST match the exact numbers cited in bullet_points.
            - Choose the chart type that best serves the data — do NOT default to column for everything:
              "column"  → comparing a metric across 4-8 platforms/creatives/audiences/geos (vertical bars, short labels)
              "bar"     → ranking comparisons where category labels are long (e.g. OOH format names, full platform names) — horizontal bars read better
              "line"    → any trend over time: weekly spend, weekly CPM, weekly impressions, pacing curves
            - Rule of thumb: if you have more than 6 categories with long names → use "bar". If it's time-series → use "line". Otherwise "column".
            - Never use "bar" for time-series. Never use "column" for weekly trends.
            - Values are raw numbers only — no $, no commas, no % symbols.
            - 4-8 categories per chart.

            SINGLE-SERIES (most slides):
              "chart_data": {{"categories": ["Meta","TikTok","YouTube"], "series_name": "Spend ($)", "values": [45000,18000,13200]}}

            MULTI-SERIES (use when comparing actuals vs benchmark, or two related metrics side-by-side):
              "chart_data": {{"categories": ["Meta","TikTok","YouTube","Google Search"],
                              "series": [{{"name": "Actual CPM ($)", "values": [9.57,11.2,8.9,2.1]}},
                                         {{"name": "Benchmark CPM ($)", "values": [10.40,10.40,10.40,2.50]}}]}}
            - Use multi-series for: platform actuals vs benchmark, week-on-week comparison, video vs static CTR.

            ═══════════════════════════════════════
            SECTIONS RULES
            ═══════════════════════════════════════
            - Define 3-5 sections in the top-level "sections" array (max 5).
            - Every slide MUST have a "section" field matching one of those section titles exactly.
            - Sections group slides in the deck; a divider slide is inserted before each group.
            - Example sections: ["Overview & Investment", "Platform Performance", "Audience & Creative", "Efficiency Analysis", "Synthesis"]
            - Recommendations and testing agenda go in the "recommendations" object only — do NOT add them to the slides array.
            - "callout" is the single most striking insight as a bold statement (used once in the deck).

            ═══════════════════════════════════════
            GENERATE: 22-28 slides in the "slides" array (not counting recs/callout which are separate).
            More slides is better — cover every drill-down in the inventory above.
            Do NOT collapse topics. Each platform, each breakdown, each comparison gets its own slide.
            Slide 1 = intro (no chart). All remaining slides = data (must have chart_data).
            ═══════════════════════════════════════

            Data to analyze: {json.dumps(source_data, default=str)}
            """
            
            def _stream(mdl):
                txt = ""
                usg = None
                for chunk in client.models.generate_content_stream(
                    model=mdl,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        max_output_tokens=65536,
                    )
                ):
                    if chunk.text:
                        txt += chunk.text
                        if callable(_progress_ph):
                            _progress_ph(len(txt))
                    candidate_usage = _last_usage(getattr(chunk, 'usage_metadata', None))
                    if candidate_usage:
                        usg = candidate_usage
                return txt, usg, mdl

            full_text, usage, model_name = _call_with_retry(_stream, model_name)

            # Calculate actual LLM Cost
            prompt_tokens    = getattr(usage, 'prompt_token_count',    0) if usage else 0
            candidate_tokens = getattr(usage, 'candidates_token_count', 0) if usage else 0
            cost = calculate_gemini_cost(prompt_tokens, candidate_tokens, model_name)

            text = full_text.replace("```json", "").replace("```", "").strip()
            result_json = json.loads(text)
            
            result_json["_metadata"] = {"cost": cost, "tokens": prompt_tokens + candidate_tokens}
            return result_json
            
        except Exception as e:
            return _mock_narrative(source_data, str(e))
            
    return _mock_narrative(source_data, "Provider not configured properly.")

def _resolve_data_context(user_prompt: str) -> dict:
    """
    Parse client name + date range from the prompt, fetch real BigQuery performance data.
    Uses the same smart year inference as _parse_date_range_from_question so that
    "mazda for 2026" doesn't resolve to full-year 2026 when data only runs to May.
    Always uses live BigQuery — no mock fallback.
    """
    # Delegate date parsing to the BQ layer which already handles year inference correctly
    from bigquery_data_layer import _parse_date_range_from_question, _dataset_date_bounds, _run, TABLE_ID
    from data_layer import get_campaigns_for_client, assemble_pca_data as _assemble

    start_date, end_date = _parse_date_range_from_question(user_prompt)

    # Cap end date at the dataset's actual max so we don't query into the future
    _, ds_max = _dataset_date_bounds()
    if end_date > ds_max:
        end_date = ds_max

    # ── Match client name directly from BQ (no build_live_clients call) ────────
    try:
        df_clients = _run(f"SELECT DISTINCT client FROM {TABLE_ID} WHERE spend > 0 ORDER BY client")
        all_clients = df_clients["client"].tolist()
    except Exception:
        all_clients = []

    pl = user_prompt.lower()
    matched_cid = matched_name = None
    for cname in all_clients:
        if cname.lower() in pl:
            matched_cid  = cname
            matched_name = cname
            break

    if not matched_cid:
        return {"resolved": False, "client_name": None,
                "date_range": f"{start_date} → {end_date}", "campaigns": []}

    camps = get_campaigns_for_client(matched_cid, start_date, end_date)
    # Filter out the synthetic "All Campaigns" entry
    real_camps = [c for c in camps if c["campaign_id"] != "bq_all_campaigns"][:3]

    if not real_camps:
        return {"resolved": False, "client_name": matched_name,
                "date_range": f"{start_date} → {end_date}", "campaigns": []}

    assembled = []
    for c in real_camps:
        try:
            data = _assemble(matched_cid, c["campaign_id"], start_date, end_date, "all")
            data["_campaign_name"] = c["campaign_name"]
            data["_date_range"]    = f"{start_date} → {end_date}"
            assembled.append(data)
        except Exception:
            pass

    return {
        "resolved":    bool(assembled),
        "client_name": matched_name,
        "date_range":  f"{start_date} → {end_date}",
        "campaigns":   assembled,
    }


def generate_quick_slides(user_prompt: str) -> dict:
    """Generate slides from a natural language prompt using real performance data where possible."""
    if not st.session_state.get("settings_llm_enabled", False):
        return {"slides": [{"slide_number": 1, "slide_type": "data", "title": "LLM Disabled",
                             "bullet_points": ["Enable LLM in the sidebar settings."],
                             "chart_type": None, "chart_data": None}],
                "_metadata": {"cost": 0.0, "tokens": 0}, "_resolved": {}}

    provider   = st.session_state.get("settings_llm_provider")
    model_name = _model_name()

    if provider == "Vertex AI (Gemini)":
        try:
            from google import genai
            from google.genai import types

            client = _gemini_client()
            ctx     = _resolve_data_context(user_prompt)

            if ctx["resolved"]:
                data_section = (
                    f"CLIENT: {ctx['client_name']}  |  PERIOD: {ctx['date_range']}\n\n"
                    f"You have FULL campaign performance data below — real spend, impressions, CPM, CTR, "
                    f"CPC, CPCV, weekly trends, and taxonomy breakdowns. Use exact numbers in bullets.\n\n"
                    f"{json.dumps(ctx['campaigns'], default=str)}"
                )
                data_note = (
                    "The data includes: overview (platform-level totals), weekly_trends, "
                    "breakdowns by: objective, format/media type, geo_target, publisher_name, "
                    "audience_segment/tactic, ad_type, buy_type, and environment. "
                    "Also includes benchmarks. Pull specific CPM, CTR, CPC, spend and impression "
                    "figures directly from the data — never make up numbers."
                )
            else:
                from data_layer import get_qa_context
                _ctx_data = get_qa_context(user_prompt)
                data_section = json.dumps(_ctx_data, default=str)
                data_note = (
                    "This is live BigQuery portfolio data. Available breakdowns: by_client_platform "
                    "(spend/impressions/CPM/CTR/CPC by client+platform), weekly_by_client, "
                    "monthly_by_client_platform, by_objective, by_format, by_geo (geo_target), "
                    "by_publisher (publisher_name), by_audience_segment, by_ad_type, by_buy_type. "
                    "Use these breakdowns to answer questions about objective mix, format performance, "
                    "geo distribution, publisher spend, audience tactics, and buy type efficiency."
                )

            prompt = f"""You are a senior media analyst. A user has requested:

"{user_prompt}"

{data_note}

Respond ONLY with a valid JSON object — no markdown, no ```json fences.

STRUCTURE:
{{
    "slides": [
        {{
            "slide_number": 1,
            "slide_type": "data",
            "title": "Punchy, specific title — not generic",
            "so_what": "The single most important takeaway in one plain-English sentence",
            "bullet_points": [
                "Lead with the insight, then back it with the exact number. E.g. 'Meta was the reach engine — 4.7M impressions at a $9.40 CPM, 9% below benchmark.'",
                "Second bullet: a tension or contrast. Use 'however', 'but', 'despite' if warranted.",
                "Third bullet: a concrete implication or recommendation from this data."
            ],
            "chart_type": "column",
            "chart_data": {{
                "categories": ["Meta", "Google Search", "YouTube", "TikTok"],
                "values": [42000, 28000, 15000, 9000],
                "series_name": "Spend ($)"
            }}
        }}
    ]
}}

RULES:
- Generate exactly the number of slides requested. Default to 3-5 if unspecified.
- Every slide MUST have chart_data with numbers pulled directly from the data. Never null.
- Bullets MUST lead with insight, not raw numbers. Commentary is mandatory, not optional.
- Use "column" for short-label platform/metric comparisons. Use "bar" for long-label rankings (OOH formats, full platform names, geo breakdowns). Use "line" for any time-series or weekly trend.
- chart_data values: raw numbers only — no $, commas, or % symbols.
- 4-8 categories per chart.
- series_name: "Spend ($)", "Impressions", "CPM ($)", "CTR (%)", "CPC ($)", etc.

DATA:
{data_section}
"""
            def _call(mdl):
                return client.models.generate_content(
                    model=mdl,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        max_output_tokens=16384
                    )
                ), mdl

            response, model_name = _call_with_retry(_call, model_name)

            usage  = response.usage_metadata
            cost   = calculate_gemini_cost(usage.prompt_token_count, usage.candidates_token_count, model_name)
            result = json.loads(response.text.replace("```json", "").replace("```", "").strip())
            result["_metadata"] = {"cost": cost, "tokens": usage.prompt_token_count + usage.candidates_token_count}
            result["_resolved"] = ctx
            return result

        except Exception as e:
            return {"slides": [{"slide_number": 1, "slide_type": "data", "title": "Error",
                                 "bullet_points": [str(e)], "chart_type": None, "chart_data": None}],
                    "_metadata": {"cost": 0.0, "tokens": 0}, "_resolved": {}}

    return {"slides": [], "_metadata": {"cost": 0.0, "tokens": 0}}


def answer_benchmark_question(query: str, chat_history: list = None, context_data: dict = None) -> dict:
    """Answer benchmark questions. context_data can contain pre-computed client vs pool comparison."""
    if chat_history is None:
        chat_history = []

    if not st.session_state.get("settings_llm_enabled", False):
        return {"answer": "Enable LLM in sidebar settings to use benchmark Q&A.",
                "query_explanation": "", "cost": 0.0}

    provider   = st.session_state.get("settings_llm_provider")
    model_name = _model_name()

    if provider == "Vertex AI (Gemini)":
        try:
            from google import genai
            from live_analytics import get_portfolio_overview, get_portfolio_benchmarks

            client = _gemini_client()
            overview = get_portfolio_overview()

            if context_data:
                context = f"""You are a senior media benchmarking analyst.
You have the following pre-computed benchmark comparison data:

CLIENT BEING ANALYSED: {context_data.get('client_name')}
DATE RANGE: {context_data.get('date_range')}

CLIENT VS POOL COMPARISON (per platform):
{json.dumps(context_data.get('comparison', []), default=str)}

POOL ACTUALS (all other clients, per platform averages):
{json.dumps(context_data.get('pool_averages', {}), default=str)}

PORTFOLIO OVERVIEW:
{json.dumps(overview, default=str)}

Answer with: direct answer first, specific numbers, then a "so what" implication.
For CPM/CPC: negative variance vs pool = client is more efficient (good).
For CTR: positive variance vs pool = client has better engagement (good).
Keep responses concise. Use bullet points.
"""
            else:
                benchmarks = get_portfolio_benchmarks("all")
                context = f"""You are a senior media benchmarking analyst at a media agency.
Portfolio benchmark data (our actuals vs industry standards):
{json.dumps(benchmarks, default=str)}

Portfolio overview:
{json.dumps(overview, default=str)}

Answer with direct insight first, then data, then implication. Be concise.
"""
            contents = [{"role": "user", "parts": [{"text": context}]}]
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            contents.append({"role": "user", "parts": [{"text": query}]})

            def _call(mdl):
                return client.models.generate_content(model=mdl, contents=contents), mdl

            response, model_name = _call_with_retry(_call, model_name)
            usage    = response.usage_metadata
            cost     = calculate_gemini_cost(usage.prompt_token_count, usage.candidates_token_count, model_name)

            return {"answer": response.text,
                    "query_explanation": f"Portfolio benchmarks via {model_name}",
                    "cost": cost}
        except Exception as e:
            return {"answer": f"Error: {e}", "query_explanation": "API Error", "cost": 0.0}

    return {"answer": "LLM provider not configured.", "query_explanation": "", "cost": 0.0}


def answer_question_with_llm(query: str, chat_history: list = None) -> dict:
    if chat_history is None:
        chat_history = []
        
    if not st.session_state.get("settings_llm_enabled", False):
        from data_layer import get_qa_context
        bq_ctx = get_qa_context(query)
        portfolio = bq_ctx.get("portfolio_summary", {})
        total_spend = portfolio.get("total_spend", 0)
        lines = ["**BigQuery Data Spine** (LLM disabled — rule-based answer)\n",
                 f"Total spend: **${total_spend:,.0f}**",
                 f"Date range: {portfolio.get('date_min','?')} → {portfolio.get('date_max','?')}"]
        if bq_ctx.get("by_objective"):
            lines.append("\n**By objective:**")
            for row in bq_ctx["by_objective"]:
                lines.append(f"• {row.get('objective','?')}: ${row.get('spend',0):,.0f}")
        return {"answer": "\n".join(lines), "data": portfolio, "cost": 0.0}

    provider = st.session_state.get("settings_llm_provider")
    model_name = _model_name()

    if provider == "Vertex AI (Gemini)":
        try:
            from google import genai
            from google.genai import types

            client = _gemini_client()

            # Build dataset context — always BigQuery (date-aware)
            from data_layer import get_qa_context
            _dataset = get_qa_context(query)
            _period      = _dataset.get("queried_period", "unknown period")
            _full_range  = _dataset.get("dataset_full_range", "unknown")
            _auto_exp    = _dataset.get("auto_expanded", False)
            _avail       = _dataset.get("data_availability", {})
            _rows        = _avail.get("rows_in_period", 0)
            _d_min       = _avail.get("earliest_date", "N/A")
            _d_max       = _avail.get("latest_date",   "N/A")

            system_instruction = f"""You are a senior media data analyst at a media agency.
You have LIVE data from BigQuery. Period queried: {_period}.
Full dataset spans: {_full_range}.
{"NOTE: The originally queried period had no data, so the query was automatically expanded to the full dataset range." if _auto_exp else ""}

DATA AVAILABILITY:
- Rows returned: {_rows:,}
- Date range of returned rows: {_d_min} → {_d_max}
- Full dataset range: {_full_range}
- Source: res-apac-dev-skynet-au · resodigital_MelbUnified.all_clients_unified

AVAILABLE DATA FIELDS (all in the LIVE DATA block below):
- by_client_platform: spend, impressions, CPM, CTR, CPC, CPCV by client + platform
- weekly_by_client / daily_detail: time-series spend and impressions
- monthly_by_client_platform: month-by-month trends
- by_objective: spend + impressions split by campaign objective (awareness, consideration, conversion, etc.)
- by_format: spend + impressions by media format/type (video, display, search, social, etc.)
- by_geo: spend + impressions by geo_target (state, national, city-level)
- by_publisher: spend + impressions by publisher_name (Meta, Google, TikTok sub-publishers, etc.)
- by_audience_segment: spend + impressions by audience tactic / segment
- by_ad_type: spend + impressions by ad unit type (carousel, video, story, etc.)
- by_buy_type: spend + impressions by buy type (CPM, CPC, CPV, programmatic, direct, etc.)

ANSWERING RULES:
1. Lead with the direct answer using EXACT numbers from the data. Never make up numbers.
2. If rows_returned=0, say: "I couldn't find data for that exact period. The dataset runs from {_full_range}. Here's what I can tell you for the available period:" then summarise the full dataset context.
3. If the query was auto-expanded, mention it naturally: "I didn't find data for [original period] so I'm showing you the full available dataset instead."
4. Format currency as $X,XXX or $X.XM. Impressions as X.XM or X,XXX,XXX.
5. For time questions (last week, yesterday) use weekly_by_client or daily_detail fields.
6. For objective/format/geo/publisher/audience questions, use the matching by_* breakdown.
7. Use bullet points for breakdowns. **Bold** key numbers and client names.
8. End with one "→ So what:" insight line.
9. If a client isn't found, name the clients that ARE in the data.
10. Never say "I don't have access" — you have live data. Say "no data found for this period" if needed.

LIVE DATA:
{json.dumps(_dataset, default=str)}"""

            contents = []
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({'role': role, 'parts': [{'text': msg["content"]}]})
            contents.append({'role': 'user', 'parts': [{'text': query}]})

            def _call(mdl):
                return client.models.generate_content(
                    model=mdl,
                    contents=contents,
                    config=types.GenerateContentConfig(system_instruction=system_instruction),
                ), mdl

            response, model_name = _call_with_retry(_call, model_name)
            usage = response.usage_metadata
            cost = calculate_gemini_cost(
                getattr(usage, 'prompt_token_count', 0),
                getattr(usage, 'candidates_token_count', 0),
                model_name,
            )

            return {
                "answer": response.text,
                "query_explanation": f"Analyzed by {model_name}",
                "cost": cost
            }
        except Exception as e:
            return {"answer": f"Sorry, I encountered an error: {e}", "query_explanation": "API Error", "cost": 0.0}

    return {"answer": "LLM provider not configured. Enable Vertex AI in ⚙️ Settings.", "query_explanation": "", "cost": 0.0}

def generate_optimizations(source_data: dict) -> dict:
    if not st.session_state.get("settings_llm_enabled", False):
        return {"optimizations": [
            {"id": "mock_1", "platform": "Meta", "action": "Shift $15,000 from Static to Video", "rationale": "Video is driving a 45% lower CPC across generic tactics.", "expected_impact": "Est. 1,200 additional clicks", "confidence": 0.88},
            {"id": "mock_2", "platform": "Google Search", "action": "Decrease weekend bid modifiers by 15%", "rationale": "Weekend conversion rates drop significantly dragging down overall efficiency.", "expected_impact": "Save $4,500 with minimal impression loss", "confidence": 0.94}
        ]}

    provider = st.session_state.get("settings_llm_provider")
    model_name = _model_name()

    if provider == "Vertex AI (Gemini)":
        try:
            from google import genai
            from google.genai import types
            
            client = _gemini_client()

            prompt = f"""You are an expert AI Trading Agent analyzing the following live campaign data:
{json.dumps(source_data.get("overview", []), default=str)}

Based on performance metrics (Spend, CPM, CPC, etc), recommend 3-5 specific, highly actionable platform-level optimizations. 
Output STRICTLY in the following JSON schema:
{{
  "optimizations": [
    {{
       "id": "opt_1",
       "platform": "Platform Name",
       "action": "Short descriptive action (e.g. Shift 10% budget from X to Y)",
       "rationale": "Why this action is recommended based on the data",
       "expected_impact": "Predicted outcome (e.g. Save $X or Gain Y clicks)",
       "confidence": 0.85 
    }}
  ]
}}
"""
            def _call(mdl):
                return client.models.generate_content(
                    model=mdl,
                    contents=prompt,
                    config=types.GenerateContentConfig(response_mime_type="application/json")
                ), mdl

            response, model_name = _call_with_retry(_call, model_name)

            try:
                txt = response.text.strip()
                if txt.startswith("```json"): txt = txt[7:]
                elif txt.startswith("```"): txt = txt[3:]
                if txt.endswith("```"): txt = txt[:-3]
                data = json.loads(txt.strip())
                return data
            except Exception as e:
                print("JSON Parsing error in optimizations:", e, response.text)
                return {"optimizations": []}
                
        except Exception as e:
            return {"error": str(e), "optimizations": []}

    return {"optimizations": []}


def generate_media_strategy(brief_text: str, client_history: dict, market_context: dict) -> dict:
    """
    Generate a forward-looking media strategy from a brief + client history + portfolio market context.
    Returns structured JSON with strategy overview, channel mix, budget allocation, flight plan, insights.
    """
    if not st.session_state.get("settings_llm_enabled", False):
        return _mock_media_strategy(client_history.get("client_name", "Client"))

    provider = st.session_state.get("settings_llm_provider")
    model_name = _model_name()

    if provider == "Vertex AI (Gemini)":
        try:
            from google import genai
            from google.genai import types

            client = _gemini_client()

            prompt = f"""You are a senior media strategist at a leading media agency.
You have been given a client brief, the client's historical campaign performance data, and market benchmarks from the broader portfolio.
Your job is to develop a comprehensive media strategy and media plan.

Respond ONLY with a valid JSON object. No markdown, no ```json fences.

═══════════════════════════════════════
CLIENT BRIEF
═══════════════════════════════════════
{brief_text if brief_text.strip() else "No brief text could be extracted — infer objectives from client history and category norms."}

═══════════════════════════════════════
CLIENT HISTORICAL PERFORMANCE
═══════════════════════════════════════
{json.dumps(client_history, default=str)}

═══════════════════════════════════════
MARKET CONTEXT (portfolio benchmarks from other clients we run)
═══════════════════════════════════════
{json.dumps(market_context, default=str)}

═══════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════
Return this exact JSON structure:
{{
  "client_name": "...",
  "strategy_headline": "One punchy sentence summarising the strategic approach",
  "executive_summary": "2-3 sentences: what the brief is asking for, what the strategy does, and the single biggest opportunity",
  "brief_summary": {{
    "objectives": ["Primary objective", "Secondary objective"],
    "target_audience": "Description of the target audience",
    "key_messages": ["Key message 1", "Key message 2"],
    "campaign_period": "e.g. Q1-Q2 FY26 or full year",
    "budget_indication": "e.g. $2.5M estimated or as briefed"
  }},
  "strategic_approach": {{
    "positioning": "How we position this campaign strategically",
    "channel_philosophy": "Why we are choosing the channel mix we are recommending",
    "key_tensions": ["Tension or challenge 1", "Tension or challenge 2"]
  }},
  "channel_mix": [
    {{
      "channel": "e.g. Broadcast TV",
      "platforms": ["Seven Network", "Nine Network", "10 Network"],
      "budget_pct": 35,
      "role": "Mass reach and brand awareness",
      "rationale": "Why this channel, grounded in client history or market data",
      "past_performance": "What this channel delivered for the client historically (CPM, reach, etc.)",
      "market_benchmark": "What we're seeing across the portfolio for this channel",
      "recommended_formats": ["30s TVC", "15s TVC"],
      "kpis": ["TRPs", "Reach %", "Frequency"]
    }}
  ],
  "budget_allocation": [
    {{"channel": "Broadcast TV", "pct": 35, "est_spend": "$875,000"}},
    {{"channel": "Digital Video", "pct": 20, "est_spend": "$500,000"}},
    {{"channel": "Social", "pct": 18, "est_spend": "$450,000"}},
    {{"channel": "Search", "pct": 12, "est_spend": "$300,000"}},
    {{"channel": "OOH", "pct": 10, "est_spend": "$250,000"}},
    {{"channel": "Radio", "pct": 5, "est_spend": "$125,000"}}
  ],
  "monthly_flight": [
    {{
      "month": "Jan 2026",
      "phase": "Launch / Awareness",
      "activity": "Heavy TV + OOH launch burst, social seeding",
      "channels_active": ["TV", "OOH", "Social", "Search"],
      "relative_weight": "Heavy"
    }}
  ],
  "market_insights": [
    {{
      "insight": "A specific market observation from the portfolio data",
      "implication": "What this means for this client's plan"
    }}
  ],
  "past_campaign_learnings": [
    {{
      "learning": "Specific finding from the client's historical campaigns",
      "applied_as": "How this learning has been applied to the new plan"
    }}
  ],
  "recommendations": [
    {{
      "priority": "HIGH",
      "recommendation": "Specific, actionable recommendation",
      "rationale": "Why, grounded in data"
    }}
  ],
  "risks_and_mitigations": [
    {{
      "risk": "A potential risk to the plan",
      "mitigation": "How to mitigate it"
    }}
  ]
}}

IMPORTANT:
- channel_mix should cover 5-8 channels appropriate for this client and category
- monthly_flight should cover every month of the campaign period (6-12 months)
- market_insights should come from the portfolio benchmark data provided — be specific
- past_campaign_learnings must reference actual numbers from the client history data
- budget_allocation percentages must sum to 100
- All est_spend values should be consistent with each other and the total budget
- Be specific and data-grounded — avoid generic platitudes
"""

            def _call(mdl):
                return client.models.generate_content(
                    model=mdl,
                    contents=prompt,
                    config=types.GenerateContentConfig(max_output_tokens=16384)
                ), mdl

            response, model_name = _call_with_retry(_call, model_name)

            usage = response.usage_metadata
            cost = calculate_gemini_cost(
                getattr(usage, "prompt_token_count", 0),
                getattr(usage, "candidates_token_count", 0),
                model_name
            )

            text = response.text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
            result["_metadata"] = {"cost": cost, "tokens": getattr(usage, "total_token_count", 0), "model": model_name}
            return result

        except Exception as e:
            return _mock_media_strategy(client_history.get("client_name", "Client"), error=str(e))

    return _mock_media_strategy(client_history.get("client_name", "Client"), error="Provider not configured.")


def _mock_media_strategy(client_name: str, error: str = None) -> dict:
    return {
        "_error": error,
        "_metadata": {"cost": 0.0, "tokens": 0, "model": "mock"},
        "client_name": client_name,
        "strategy_headline": "Integrated, data-led campaign across broadcast and digital touchpoints",
        "executive_summary": "Based on historical performance and market benchmarks, this strategy recommends a balanced channel mix prioritising mass reach via TV, amplified by targeted digital video and performance search.",
        "brief_summary": {
            "objectives": ["Drive brand awareness", "Generate qualified leads"],
            "target_audience": "Adults 25-54, household decision-makers",
            "key_messages": ["Brand message 1", "Brand message 2"],
            "campaign_period": "FY26 full year",
            "budget_indication": "TBD"
        },
        "strategic_approach": {
            "positioning": "Category leadership through integrated reach",
            "channel_philosophy": "TV builds reach, digital converts it",
            "key_tensions": ["Balancing brand vs performance investment", "National vs state-weighted activity"]
        },
        "channel_mix": [
            {"channel": "Broadcast TV", "platforms": ["Seven", "Nine", "10"], "budget_pct": 35,
             "role": "Mass reach", "rationale": "Highest reach channel in category", "past_performance": "See client history",
             "market_benchmark": "Avg CPM $28-30 across portfolio", "recommended_formats": ["30s TVC"], "kpis": ["TRPs", "Reach%"]},
            {"channel": "Social", "platforms": ["Meta", "TikTok"], "budget_pct": 25,
             "role": "Engagement and retargeting", "rationale": "Strong CTR from previous campaigns", "past_performance": "See client history",
             "market_benchmark": "Meta CPM $9-12 across portfolio", "recommended_formats": ["Video 15s", "Carousel"], "kpis": ["CPM", "CTR", "VTR"]}
        ],
        "budget_allocation": [
            {"channel": "Broadcast TV", "pct": 35, "est_spend": "TBD"},
            {"channel": "Social", "pct": 25, "est_spend": "TBD"},
            {"channel": "Search", "pct": 20, "est_spend": "TBD"},
            {"channel": "Digital Video", "pct": 10, "est_spend": "TBD"},
            {"channel": "OOH", "pct": 10, "est_spend": "TBD"}
        ],
        "monthly_flight": [
            {"month": m, "phase": "Campaign Activity", "activity": "Placeholder — enable LLM for full plan",
             "channels_active": ["TV", "Social", "Search"], "relative_weight": "Medium"}
            for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        ],
        "market_insights": [{"insight": "Enable LLM for market insights", "implication": "N/A"}],
        "past_campaign_learnings": [{"learning": "Enable LLM for learnings", "applied_as": "N/A"}],
        "recommendations": [{"priority": "HIGH", "recommendation": "Enable LLM for recommendations", "rationale": "N/A"}],
        "risks_and_mitigations": [],
        "_metadata": {"cost": 0.0, "tokens": 0}
    }


# ─── Weekly Meet generator ─────────────────────────────────────────────────────

def generate_weekly_meet(data: dict, client_name: str) -> dict:
    """
    Generate a Weekly Meet / WIP meeting brief from weekly BQ data.

    Returns a structured JSON with:
      headline, overall_summary, channels (per-platform), next_week_actions, talking_points
    """
    def _mock(reason=""):
        return {
            "_error": bool(reason),
            "_error_msg": reason,
            "_metadata": {"cost": 0.0, "tokens": 0},
            "headline": "Weekly performance summary",
            "overall_summary": "Enable LLM in sidebar settings to generate a full Weekly Meet brief.",
            "channels": [
                {
                    "platform": r["platform"],
                    "status": "on_track",
                    "summary": f"${r['spend']:,.0f} spend · {r['impressions']:,} imps",
                    "wow_note": "WoW data available — enable LLM for narrative.",
                    "recommendation": "Enable LLM for recommendations.",
                }
                for r in data.get("this_week", [])
            ],
            "next_week_actions": [
                {"priority": "—", "platform": "All", "action": "Enable LLM for next-week recommendations.", "rationale": ""}
            ],
            "talking_points": [
                {"topic": "Overall delivery", "context": "See channel table below.", "suggested_question": "How did we track vs plan this week?"}
            ],
        }

    if not st.session_state.get("settings_llm_enabled", False):
        return _mock()

    provider   = st.session_state.get("settings_llm_provider")
    model_name = _model_name()

    if provider != "Vertex AI (Gemini)":
        return _mock("Provider not configured.")

    try:
        from google import genai
        from google.genai import types

        client = _gemini_client()

        week_start  = data.get("week_start", "")
        week_end    = data.get("week_end", "")
        totals      = data.get("totals", {})
        spend_wow   = totals.get("spend_wow_pct")
        wow_txt     = f"{spend_wow:+.1f}% WoW" if spend_wow is not None else "no prior week data"

        prompt = f"""You are a senior media strategist running a Weekly WIP meeting for the client {client_name}.
The week covered is {week_start} to {week_end}.
Total spend this week: ${totals.get('spend', 0):,.0f}  ({wow_txt}).
Platforms active: {totals.get('n_platforms', 0)}.

Respond ONLY with a valid JSON object. No markdown fences.

Your job is to generate a complete Weekly Meet brief that a media planner would use to:
1. Summarise the week's performance channel by channel with insight-led commentary
2. Recommend concrete actions for next week
3. Arm the account team with talking points for the client meeting

═══════════════════════════════════════
TONE & STYLE
═══════════════════════════════════════
- Direct, confident, no waffle. Lead every comment with the implication, not the raw number.
- "Meta was efficient this week — CPM held at $9.40, 12% below benchmark — but CTR dropped to 0.55%, suggesting fatigue."  ← GOOD
- "Meta spent $45,000 with 4.7M impressions and a $9.40 CPM."  ← BAD (data dump, no insight)
- For WoW changes, flag meaningful shifts (>10%) with a reason or hypothesis.
- Recommendations must be specific and actionable: "Increase Google Search daily cap from $800 to $1,100" not "consider optimising Search budget".
- Talking points should be things the client will ask about — frame them as conversation starters, not status updates.

═══════════════════════════════════════
STATUS CODES — assign one per channel:
  "strong"    → materially beating efficiency benchmarks or plan
  "on_track"  → within ±10% of expected pacing and efficiency
  "watch"     → a metric is drifting — flag it, monitor next week
  "concern"   → underdelivering or efficiency materially off — needs action
═══════════════════════════════════════

OUTPUT SCHEMA:
{{
    "headline": "6-10 word punchy summary of the week — the thing to say in the first 30 seconds of the meeting",
    "overall_summary": "3-4 sentences. Total delivery, top performer, biggest issue, and one forward-looking note.",
    "channels": [
        {{
            "platform": "Meta",
            "status": "strong",
            "summary": "2-3 sentences of insight-led commentary. What happened, why it matters, what it signals.",
            "wow_note": "One sentence on key WoW movement (spend, CPM, CTR, or impressions — pick the most significant). Use +/-% with context.",
            "recommendation": "One specific, actionable instruction for next week. Start with a verb (Increase / Pause / Shift / Test / Cap / etc.)"
        }}
    ],
    "next_week_actions": [
        {{
            "priority": "HIGH",
            "platform": "Google Search",
            "action": "Increase daily budget cap from $800 to $1,100 — Search was impression-constrained 4 of 7 days and delivered the lowest CPC of the portfolio.",
            "rationale": "One sentence explaining why this is the right move based on this week's data."
        }}
    ],
    "talking_points": [
        {{
            "topic": "Meta creative fatigue",
            "context": "CTR has declined 3 weeks in a row. This week it hit 0.55%, 35% below the 0.85% benchmark. The creative pool has not been refreshed since [date].",
            "suggested_question": "Have you had new creative approved? We should brief a refresh this week or we'll see further efficiency loss."
        }}
    ],
    "campaign_summaries": [
        {{
            "campaign": "Campaign description exactly as in data",
            "status": "strong",
            "one_liner": "One insight-led sentence — what this campaign did this week and what it means.",
            "watch": "Optional: one thing to monitor or flag for next week. Omit if nothing notable."
        }}
    ]
}}

RULES:
- Generate one channel entry per platform in this_week.
- Generate 3-6 next_week_actions — prioritise HIGH / MEDIUM / LOW.
- Generate 3-5 talking_points — these are the meaty client conversation topics, not housekeeping.
- Generate one campaign_summary entry per campaign in campaigns_this_week (top 10 max). Use exact campaign names from the data.
- All numbers in text MUST come from the data below. Never invent figures.
- WoW comparisons: use wow[] for platform variance and spend_wow_pct in campaigns_this_week for campaign variance.
- If a metric is null/missing, omit it from the narrative rather than guessing.

DATA:
{json.dumps(data, default=str)}
"""

        def _call(mdl):
            return client.models.generate_content(
                model=mdl,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    max_output_tokens=16384,
                ),
            ), mdl

        response, model_name = _call_with_retry(_call, model_name)
        usage = response.usage_metadata
        cost  = calculate_gemini_cost(
            getattr(usage, "prompt_token_count",     0),
            getattr(usage, "candidates_token_count", 0),
            model_name,
        )
        result = json.loads(response.text.replace("```json", "").replace("```", "").strip())
        result["_metadata"] = {"cost": cost, "tokens": getattr(usage, "prompt_token_count", 0) + getattr(usage, "candidates_token_count", 0)}
        result["_error"]    = False
        result["_error_msg"] = ""
        return result

    except Exception as e:
        return _mock(str(e))
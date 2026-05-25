"""
SuperMetrics Enterprise HTTP API connector.
Calls https://api.supermetrics.com/enterprise/v2/query/data/json directly.
No Python SDK required — just `requests`.

Auth: api_key + ds_user (your SuperMetrics login email) embedded in each query.
"""
from __future__ import annotations

import json
import time
import urllib.parse

import pandas as pd
import requests

BASE_URL = "https://api.supermetrics.com/enterprise/v2/query/data/json"

# ── Field helpers ─────────────────────────────────────────────────────────────
def _dim(field_id: str) -> dict:
    """Dimension field — split into its own column."""
    return {"id": field_id, "split": "column"}

def _met(field_id: str) -> dict:
    """Metric field — aggregated value."""
    return {"id": field_id}


# ── Platform configuration ────────────────────────────────────────────────────
# For each platform:
#   ds_id      : SuperMetrics data source identifier
#   label      : human-readable name
#   fields     : list of field objects in query order
#   field_map  : { supermetrics_field_id : our_schema_column }
#
# Field IDs are taken from the SuperMetrics query builder for each connector.
# Adjust if your account exposes different field names.

PLATFORM_CONFIG: dict[str, dict] = {

    "dv360": {
        "ds_id": "DBM",
        "label": "DV360",
        "fields": [
            _dim("today"),
            _dim("advertiser"), _dim("advertiserID"),
            _dim("campaign"),   _dim("campaignID"),
            _dim("LineItem"),   _dim("LineItemID"),
            _dim("Creative"),   _dim("CreativeID"),
            _dim("DeviceTypeMobile"),
            _met("revenue"),        # spend in DBM = revenue
            _met("impressions"),
            _met("clicks"),
            _met("totalConversions"),
            _met("totalConversionRevenue"),
            _met("reach"),
            _met("videoCompletions"),
            _met("videoFirstQuartiles"),
            _met("videoMidpoints"),
            _met("videoThirdQuartiles"),
        ],
        "field_map": {
            "today":                  "date",
            "advertiser":             "account_name",
            "advertiserID":           "account_id",
            "campaign":               "campaign_name",
            "campaignID":             "campaign_id",
            "LineItem":               "ad_group_name",
            "LineItemID":             "ad_group_id",
            "Creative":               "ad_name",
            "CreativeID":             "ad_id",
            "DeviceTypeMobile":       "device",
            "revenue":                "spend",
            "impressions":            "impressions",
            "clicks":                 "clicks",
            "totalConversions":       "conversions",
            "totalConversionRevenue": "conversion_value",
            "reach":                  "reach",
            "videoCompletions":       "video_views_100pct",
            "videoFirstQuartiles":    "video_views_25pct",
            "videoMidpoints":         "video_views_50pct",
            "videoThirdQuartiles":    "video_views_75pct",
        },
    },

    "meta": {
        "ds_id": "FBA",
        "label": "Meta Ads",
        "fields": [
            _dim("Date"),
            _dim("AccountID"),    _dim("AccountName"),
            _dim("CampaignID"),   _dim("CampaignName"),
            _dim("AdSetID"),      _dim("AdSetName"),
            _dim("AdID"),         _dim("AdName"),
            _dim("DevicePlatform"),
            _met("Spend"),
            _met("Impressions"),
            _met("Clicks"),
            _met("Conversions"),
            _met("ConversionValue"),
            _met("Reach"),
            _met("Frequency"),
            _met("VideoPlays"),
            _met("VideoPlaysAt25Percent"),
            _met("VideoPlaysAt50Percent"),
            _met("VideoPlaysAt75Percent"),
            _met("VideoPlaysAt100Percent"),
            _met("PostEngagements"),
            _met("PostLikes"),
            _met("PostShares"),
            _met("PostComments"),
            _met("PostSaves"),
            _met("LinkClicks"),
            _met("LandingPageViews"),
        ],
        "field_map": {
            "Date":                   "date",
            "AccountID":              "account_id",
            "AccountName":            "account_name",
            "CampaignID":             "campaign_id",
            "CampaignName":           "campaign_name",
            "AdSetID":                "ad_group_id",
            "AdSetName":              "ad_group_name",
            "AdID":                   "ad_id",
            "AdName":                 "ad_name",
            "DevicePlatform":         "device",
            "Spend":                  "spend",
            "Impressions":            "impressions",
            "Clicks":                 "clicks",
            "Conversions":            "conversions",
            "ConversionValue":        "conversion_value",
            "Reach":                  "reach",
            "Frequency":              "frequency",
            "VideoPlays":             "video_views",
            "VideoPlaysAt25Percent":  "video_views_25pct",
            "VideoPlaysAt50Percent":  "video_views_50pct",
            "VideoPlaysAt75Percent":  "video_views_75pct",
            "VideoPlaysAt100Percent": "video_views_100pct",
            "PostEngagements":        "engagements",
            "PostLikes":              "likes",
            "PostShares":             "shares",
            "PostComments":           "comments",
            "PostSaves":              "saves",
            "LinkClicks":             "link_clicks",
            "LandingPageViews":       "landing_page_views",
        },
    },

    "google_search": {
        "ds_id": "AW",
        "label": "Google Search",
        "fields": [
            _dim("Date"),
            _dim("AccountId"),    _dim("AccountName"),
            _dim("CampaignId"),   _dim("CampaignName"),
            _dim("AdGroupId"),    _dim("AdGroupName"),
            _dim("Device"),
            _met("Cost"),
            _met("Impressions"),
            _met("Clicks"),
            _met("Conversions"),
            _met("ConversionValue"),
            _met("SearchImpressionShare"),
            _met("SearchTopImpressionShare"),
            _met("AverageQualityScore"),
        ],
        "field_map": {
            "Date":                     "date",
            "AccountId":                "account_id",
            "AccountName":              "account_name",
            "CampaignId":               "campaign_id",
            "CampaignName":             "campaign_name",
            "AdGroupId":                "ad_group_id",
            "AdGroupName":              "ad_group_name",
            "Device":                   "device",
            "Cost":                     "spend",
            "Impressions":              "impressions",
            "Clicks":                   "clicks",
            "Conversions":              "conversions",
            "ConversionValue":          "conversion_value",
            "SearchImpressionShare":    "search_impression_share",
            "SearchTopImpressionShare": "search_top_impression_share",
            "AverageQualityScore":      "quality_score",
        },
    },

    "google_ads": {
        "ds_id": "AW",
        "label": "Google Display/Video",
        "fields": [
            _dim("Date"),
            _dim("AccountId"),    _dim("AccountName"),
            _dim("CampaignId"),   _dim("CampaignName"),
            _dim("AdGroupId"),    _dim("AdGroupName"),
            _dim("AdId"),         _dim("AdName"),
            _dim("Device"),
            _met("Cost"),
            _met("Impressions"),
            _met("Clicks"),
            _met("Conversions"),
            _met("ConversionValue"),
            _met("VideoViews"),
            _met("VideoViewedTo25Percent"),
            _met("VideoViewedTo50Percent"),
            _met("VideoViewedTo75Percent"),
            _met("VideoViewedTo100Percent"),
        ],
        "field_map": {
            "Date":                    "date",
            "AccountId":               "account_id",
            "AccountName":             "account_name",
            "CampaignId":              "campaign_id",
            "CampaignName":            "campaign_name",
            "AdGroupId":               "ad_group_id",
            "AdGroupName":             "ad_group_name",
            "AdId":                    "ad_id",
            "AdName":                  "ad_name",
            "Device":                  "device",
            "Cost":                    "spend",
            "Impressions":             "impressions",
            "Clicks":                  "clicks",
            "Conversions":             "conversions",
            "ConversionValue":         "conversion_value",
            "VideoViews":              "video_views",
            "VideoViewedTo25Percent":  "video_views_25pct",
            "VideoViewedTo50Percent":  "video_views_50pct",
            "VideoViewedTo75Percent":  "video_views_75pct",
            "VideoViewedTo100Percent": "video_views_100pct",
        },
    },

    "tiktok": {
        "ds_id": "TIKTOKAI",
        "label": "TikTok Ads",
        "fields": [
            _dim("StatTimeDay"),
            _dim("AdvertiserId"),   _dim("AdvertiserName"),
            _dim("CampaignId"),     _dim("CampaignName"),
            _dim("AdGroupId"),      _dim("AdGroupName"),
            _dim("AdId"),           _dim("AdName"),
            _met("Spend"),
            _met("Impressions"),
            _met("Clicks"),
            _met("Conversions"),
            _met("ConversionValue"),
            _met("VideoPlayActions"),
            _met("VideoWatchedTo25"),
            _met("VideoWatchedTo50"),
            _met("VideoWatchedTo75"),
            _met("VideoWatchedTo100"),
            _met("Likes"),
            _met("Shares"),
            _met("Comments"),
        ],
        "field_map": {
            "StatTimeDay":       "date",
            "AdvertiserId":      "account_id",
            "AdvertiserName":    "account_name",
            "CampaignId":        "campaign_id",
            "CampaignName":      "campaign_name",
            "AdGroupId":         "ad_group_id",
            "AdGroupName":       "ad_group_name",
            "AdId":              "ad_id",
            "AdName":            "ad_name",
            "Spend":             "spend",
            "Impressions":       "impressions",
            "Clicks":            "clicks",
            "Conversions":       "conversions",
            "ConversionValue":   "conversion_value",
            "VideoPlayActions":  "video_views",
            "VideoWatchedTo25":  "video_views_25pct",
            "VideoWatchedTo50":  "video_views_50pct",
            "VideoWatchedTo75":  "video_views_75pct",
            "VideoWatchedTo100": "video_views_100pct",
            "Likes":             "likes",
            "Shares":            "shares",
            "Comments":          "comments",
        },
    },

    "the_trade_desk": {
        "ds_id": "TTD",
        "label": "The Trade Desk",
        "fields": [
            _dim("Date"),
            _dim("AdvertiserId"),   _dim("AdvertiserName"),
            _dim("CampaignId"),     _dim("CampaignName"),
            _dim("AdGroupId"),      _dim("AdGroupName"),
            _dim("AdId"),           _dim("AdName"),
            _dim("Device"),
            _met("Spend"),
            _met("Impressions"),
            _met("Clicks"),
            _met("Conversions"),
            _met("Revenue"),
        ],
        "field_map": {
            "Date":           "date",
            "AdvertiserId":   "account_id",
            "AdvertiserName": "account_name",
            "CampaignId":     "campaign_id",
            "CampaignName":   "campaign_name",
            "AdGroupId":      "ad_group_id",
            "AdGroupName":    "ad_group_name",
            "AdId":           "ad_id",
            "AdName":         "ad_name",
            "Device":         "device",
            "Spend":          "spend",
            "Impressions":    "impressions",
            "Clicks":         "clicks",
            "Conversions":    "conversions",
            "Revenue":        "conversion_value",
        },
    },

    "youtube": {
        "ds_id": "YT",
        "label": "YouTube",
        "fields": [
            _dim("Day"),
            _dim("ChannelId"),    _dim("ChannelName"),
            _dim("CampaignId"),   _dim("CampaignName"),
            _dim("AdGroupId"),    _dim("AdGroupName"),
            _dim("Device"),
            _met("Views"),
            _met("Impressions"),
            _met("Clicks"),
            _met("EstimatedMinutesWatched"),
        ],
        "field_map": {
            "Day":                       "date",
            "ChannelId":                 "account_id",
            "ChannelName":               "account_name",
            "CampaignId":                "campaign_id",
            "CampaignName":              "campaign_name",
            "AdGroupId":                 "ad_group_id",
            "AdGroupName":               "ad_group_name",
            "Device":                    "device",
            "Views":                     "video_views",
            "Impressions":               "impressions",
            "Clicks":                    "clicks",
        },
    },

    "linkedin": {
        "ds_id": "LIN",
        "label": "LinkedIn Ads",
        "fields": [
            _dim("StartDate"),
            _dim("AccountId"),    _dim("AccountName"),
            _dim("CampaignId"),   _dim("CampaignName"),
            _dim("CreativeId"),   _dim("CreativeName"),
            _met("Spend"),
            _met("Impressions"),
            _met("Clicks"),
            _met("Conversions"),
            _met("ConversionValue"),
            _met("VideoViews"),
            _met("VideoCompletions"),
            _met("Likes"),
            _met("Shares"),
            _met("Comments"),
        ],
        "field_map": {
            "StartDate":       "date",
            "AccountId":       "account_id",
            "AccountName":     "account_name",
            "CampaignId":      "campaign_id",
            "CampaignName":    "campaign_name",
            "CreativeId":      "ad_id",
            "CreativeName":    "ad_name",
            "Spend":           "spend",
            "Impressions":     "impressions",
            "Clicks":          "clicks",
            "Conversions":     "conversions",
            "ConversionValue": "conversion_value",
            "VideoViews":      "video_views",
            "VideoCompletions":"video_views_100pct",
            "Likes":           "likes",
            "Shares":          "shares",
            "Comments":        "comments",
        },
    },

    "bing_search": {
        "ds_id": "BING",
        "label": "Microsoft/Bing Ads",
        "fields": [
            _dim("TimePeriod"),
            _dim("AccountId"),    _dim("AccountName"),
            _dim("CampaignId"),   _dim("CampaignName"),
            _dim("AdGroupId"),    _dim("AdGroupName"),
            _dim("DeviceOS"),
            _met("Spend"),
            _met("Impressions"),
            _met("Clicks"),
            _met("Conversions"),
            _met("Revenue"),
        ],
        "field_map": {
            "TimePeriod":   "date",
            "AccountId":    "account_id",
            "AccountName":  "account_name",
            "CampaignId":   "campaign_id",
            "CampaignName": "campaign_name",
            "AdGroupId":    "ad_group_id",
            "AdGroupName":  "ad_group_name",
            "DeviceOS":     "device",
            "Spend":        "spend",
            "Impressions":  "impressions",
            "Clicks":       "clicks",
            "Conversions":  "conversions",
            "Revenue":      "conversion_value",
        },
    },

    "spotify": {
        "ds_id": "SPOTAD",
        "label": "Spotify Ads",
        "fields": [
            _dim("Date"),
            _dim("AccountId"),   _dim("AccountName"),
            _dim("CampaignId"),  _dim("CampaignName"),
            _dim("AdSetId"),     _dim("AdSetName"),
            _met("Spend"),
            _met("Impressions"),
            _met("Clicks"),
            _met("AudioCompletions"),
            _met("AudioCompletionRate"),
            _met("Reach"),
            _met("Frequency"),
        ],
        "field_map": {
            "Date":                "date",
            "AccountId":           "account_id",
            "AccountName":         "account_name",
            "CampaignId":          "campaign_id",
            "CampaignName":        "campaign_name",
            "AdSetId":             "ad_group_id",
            "AdSetName":           "ad_group_name",
            "Spend":               "spend",
            "Impressions":         "impressions",
            "Clicks":              "clicks",
            "AudioCompletions":    "audio_completions",
            "AudioCompletionRate": "audio_completion_rate",
            "Reach":               "reach",
            "Frequency":           "frequency",
        },
    },

    "pinterest": {
        "ds_id": "PIN",
        "label": "Pinterest Ads",
        "fields": [
            _dim("Date"),
            _dim("AccountId"),   _dim("AccountName"),
            _dim("CampaignId"),  _dim("CampaignName"),
            _dim("AdGroupId"),   _dim("AdGroupName"),
            _dim("AdId"),        _dim("AdName"),
            _met("Spend"),
            _met("Impressions"),
            _met("Clicks"),
            _met("TotalConversions"),
            _met("ConversionValue"),
            _met("Saves"),
            _met("VideoMrcViews"),
        ],
        "field_map": {
            "Date":             "date",
            "AccountId":        "account_id",
            "AccountName":      "account_name",
            "CampaignId":       "campaign_id",
            "CampaignName":     "campaign_name",
            "AdGroupId":        "ad_group_id",
            "AdGroupName":      "ad_group_name",
            "AdId":             "ad_id",
            "AdName":           "ad_name",
            "Spend":            "spend",
            "Impressions":      "impressions",
            "Clicks":           "clicks",
            "TotalConversions": "conversions",
            "ConversionValue":  "conversion_value",
            "Saves":            "saves",
            "VideoMrcViews":    "video_views",
        },
    },

    "snapchat": {
        "ds_id": "SNAP",
        "label": "Snapchat Ads",
        "fields": [
            _dim("StartTime"),
            _dim("AdAccountId"),   _dim("AdAccountName"),
            _dim("CampaignId"),    _dim("CampaignName"),
            _dim("AdSquadId"),     _dim("AdSquadName"),
            _dim("AdId"),          _dim("AdName"),
            _met("Spend"),
            _met("Impressions"),
            _met("SwipeUps"),
            _met("Conversions"),
            _met("Revenue"),
            _met("VideoViews"),
            _met("Quartile1"),
            _met("Quartile2"),
            _met("Quartile3"),
            _met("Completions"),
            _met("Reach"),
            _met("Frequency"),
        ],
        "field_map": {
            "StartTime":     "date",
            "AdAccountId":   "account_id",
            "AdAccountName": "account_name",
            "CampaignId":    "campaign_id",
            "CampaignName":  "campaign_name",
            "AdSquadId":     "ad_group_id",
            "AdSquadName":   "ad_group_name",
            "AdId":          "ad_id",
            "AdName":        "ad_name",
            "Spend":         "spend",
            "Impressions":   "impressions",
            "SwipeUps":      "clicks",
            "Conversions":   "conversions",
            "Revenue":       "conversion_value",
            "VideoViews":    "video_views",
            "Quartile1":     "video_views_25pct",
            "Quartile2":     "video_views_50pct",
            "Quartile3":     "video_views_75pct",
            "Completions":   "video_views_100pct",
            "Reach":         "reach",
            "Frequency":     "frequency",
        },
    },
}

PLATFORM_TIERS = {
    1: ["meta", "google_search", "google_ads", "dv360", "tiktok"],
    2: ["the_trade_desk", "bing_search", "spotify", "linkedin", "youtube"],
    3: ["pinterest", "snapchat"],
}


# ── HTTP connector ────────────────────────────────────────────────────────────

class SupermetricsConnector:
    """
    Calls the SuperMetrics Enterprise API v2 directly via HTTP.
    No Python SDK required.
    """

    def __init__(self, api_key: str, ds_user: str):
        self.api_key = api_key
        self.ds_user = ds_user

    def _query(self, payload: dict, timeout: int = 120) -> dict:
        """POST a query and return the parsed JSON response."""
        url = BASE_URL + "?json=" + urllib.parse.quote(json.dumps(payload))
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def _parse_response(self, raw: dict) -> pd.DataFrame:
        """
        Convert a SuperMetrics API response into a DataFrame.
        Handles the two common response shapes:
          - {"data": {"headers": [...], "rows": [...]}}
          - {"data": [{"col": val, ...}, ...]}
        """
        data = raw.get("data", raw)

        if isinstance(data, dict) and "rows" in data:
            headers = data.get("headers", [])
            rows = data.get("rows", [])
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows, columns=headers if headers else None)

        elif isinstance(data, list):
            if not data:
                return pd.DataFrame()
            df = pd.DataFrame(data)

        else:
            raise ValueError(f"Unrecognised response shape: {list(raw.keys())}")

        return df

    def test_connection(self) -> tuple[bool, str]:
        """Returns (True, "") on success or (False, error_message)."""
        # Use a tiny DV360 query as a smoke test
        payload = {
            "ds_id":           "DBM",
            "ds_accounts":     "list.all_accounts",
            "ds_user":         self.ds_user,
            "date_range_type": "last_7_days",
            "fields":          [_met("impressions")],
            "max_rows":        1,
            "api_key":         self.api_key,
        }
        try:
            self._query(payload, timeout=30)
            return True, ""
        except requests.HTTPError as exc:
            return False, f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
        except Exception as exc:
            return False, str(exc)

    def pull_platform(
        self,
        platform: str,
        start_date: str,
        end_date: str,
        client_id:   str | None = None,
        client_name: str | None = None,
        max_rows: int = 1_000_000,
    ) -> pd.DataFrame:
        """
        Pull one platform's data for the given date range.
        Returns a normalised DataFrame matching the platform_daily schema.
        """
        cfg = PLATFORM_CONFIG.get(platform)
        if cfg is None:
            raise ValueError(f"Unknown platform: {platform}")

        payload = {
            "ds_id":       cfg["ds_id"],
            "ds_accounts": "list.all_accounts",
            "ds_user":     self.ds_user,
            "start_date":  start_date,
            "end_date":    end_date,
            "fields":      cfg["fields"],
            "max_rows":    max_rows,
            "api_key":     self.api_key,
        }

        raw = self._query(payload)

        # Check for API-level errors
        if raw.get("meta", {}).get("status") == "error" or "error" in raw:
            msg = raw.get("meta", {}).get("error_info", raw.get("error", str(raw)))
            raise RuntimeError(f"SuperMetrics error ({platform}): {msg}")

        df = self._parse_response(raw)
        if df.empty:
            return df

        # Rename SuperMetrics field IDs → our schema columns
        df = df.rename(columns=cfg["field_map"])

        # Any remaining unmapped columns become conv_* (custom conversions)
        known = set(cfg["field_map"].values()) | {
            "date","client_id","client_name","platform",
            "account_id","account_name",
            "campaign_id","campaign_name",
            "ad_group_id","ad_group_name",
            "ad_id","ad_name",
            "device","geo_state",
            "spend","impressions","clicks","conversions","conversion_value",
            "reach","frequency",
            "video_views","video_views_25pct","video_views_50pct",
            "video_views_75pct","video_views_100pct",
            "engagements","likes","shares","comments","saves",
            "link_clicks","landing_page_views",
            "audio_completions","audio_completion_rate",
            "search_impression_share","search_top_impression_share","quality_score",
        }
        rename_extra = {}
        for col in df.columns:
            if col not in known:
                safe = col.lower().replace(" ", "_").replace("-", "_")
                rename_extra[col] = safe if safe.startswith("conv_") else f"conv_{safe}"
        if rename_extra:
            df = df.rename(columns=rename_extra)

        # Stamp platform + client
        df["platform"] = platform
        if client_id:   df["client_id"]   = client_id
        if client_name: df["client_name"] = client_name

        # Normalise date
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")

        # Cast numerics
        for col in [
            "spend","impressions","clicks","conversions","conversion_value",
            "reach","frequency",
            "video_views","video_views_25pct","video_views_50pct",
            "video_views_75pct","video_views_100pct",
            "engagements","likes","shares","comments","saves",
            "link_clicks","landing_page_views",
            "audio_completions","audio_completion_rate",
            "search_impression_share","search_top_impression_share","quality_score",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

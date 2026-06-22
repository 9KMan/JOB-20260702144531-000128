"""Tools module - re-exports all LangGraph @tool functions from all connectors."""

from src.connectors.google.ga4 import get_ga4_report, get_ga4_realtime_users
from src.connectors.google.search_console import get_search_analytics, get_search_console_sites
from src.connectors.google.ads import get_google_ads_campaigns, get_google_ads_performance_report
from src.connectors.hubspot import get_hubspot_contacts, get_hubspot_deals, get_hubspot_tickets
from src.connectors.slack import send_slack_message, list_slack_channels
from src.connectors.semrush import get_semrush_organic_keywords, get_semrush_domain_analytics
from src.connectors.posthog import get_posthog_events, get_posthog_feature_flags

__all__ = [
    # Google GA4
    "get_ga4_report",
    "get_ga4_realtime_users",
    # Google Search Console
    "get_search_analytics",
    "get_search_console_sites",
    # Google Ads
    "get_google_ads_campaigns",
    "get_google_ads_performance_report",
    # HubSpot
    "get_hubspot_contacts",
    "get_hubspot_deals",
    "get_hubspot_tickets",
    # Slack
    "send_slack_message",
    "list_slack_channels",
    # SEMrush
    "get_semrush_organic_keywords",
    "get_semrush_domain_analytics",
    # PostHog
    "get_posthog_events",
    "get_posthog_feature_flags",
]

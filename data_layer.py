"""
Data layer — always routes to BigQuery (res-apac-dev-skynet-au).
Live data only. No mock, no local DuckDB.
"""

def get_clients_in_date_range(start_date, end_date):
    from bigquery_data_layer import get_clients
    return get_clients(start_date, end_date)

def get_campaigns_for_client(client_id, start_date, end_date):
    from bigquery_data_layer import get_campaigns
    return get_campaigns(client_id, start_date, end_date)

def assemble_pca_data(client_id, campaign_id, start_date, end_date, channel_filter="all"):
    from bigquery_data_layer import assemble_pca_data as fn
    return fn(client_id, campaign_id, start_date, end_date, channel_filter)

def get_portfolio_actuals(start_date, end_date, channel_filter="all"):
    from bigquery_data_layer import get_portfolio_actuals as fn
    return fn(start_date, end_date, channel_filter)

def get_qa_context(question: str) -> dict:
    from bigquery_data_layer import get_qa_context
    return get_qa_context(question)

def get_live_clients():
    from bigquery_data_layer import build_live_clients
    return build_live_clients()

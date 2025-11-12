import requests
import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

def analyze_ticker(ticker: str, as_of_date: str):
    r = requests.get(f"{API_BASE}/research/analyze", params={"ticker": ticker, "as_of_date": as_of_date})
    r.raise_for_status()
    return r.json().get("data", {})

def get_mcp_jobs():
    r = requests.get(f"{API_BASE}/mcp/status/all")  # optional endpoint
    if r.status_code == 200:
        return r.json().get("data", [])
    return []
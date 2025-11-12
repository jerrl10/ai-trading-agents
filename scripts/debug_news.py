from datetime import date
import traceback

import os
from dotenv import load_dotenv, find_dotenv

# Ensure .env is loaded for runs outside the VS Code debugger
load_dotenv(find_dotenv(), override=False)

# Optional: in-process debugpy attach if DEBUG_MODE=true in .env
if os.getenv("DEBUG_MODE", "false").lower() == "true":
    try:
        import debugpy
        debugpy.listen(("127.0.0.1", 5678))
        print("🪲 debugpy listening on 127.0.0.1:5678 — open VS Code 'Attach: debugpy 5678' to connect.")
        # Wait only up to 15s to avoid hanging in CI
        debugpy.wait_for_client()
    except Exception as _dbg_err:
        print(f"⚠️ debugpy not available or attach failed: {_dbg_err}")

from tradingagents.data.adapters.news_general_av import fetch_news_general

if __name__ == "__main__":
    print("🔍 Starting debug: fetch_news_general()")

    print(f"ENV DEBUG_MODE={os.getenv('DEBUG_MODE')}  ALPHAVANTAGE_API_KEY set? {'yes' if os.getenv('ALPHAVANTAGE_API_KEY') else 'no'}")

    try:
        ticker = "AAPL"
        as_of = date(2025, 1, 15)
        print(f"Fetching news for {ticker} as of {as_of} ...")

        items = fetch_news_general(ticker, as_of)
        print(f"✅ Fetch complete. {len(items)} items returned.\n")

        if not items:
            print("⚠️ No items fetched — check your ALPHAVANTAGE_API_KEY in .env or rate limit issues.")
        else:
            for i, item in enumerate(items[:5]):
                print(f"--- Item {i+1} ---")
                print(item.model_dump())
                print()

    except Exception as e:
        print("❌ Error occurred during fetch:")
        traceback.print_exc()
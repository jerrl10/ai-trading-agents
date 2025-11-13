# import asyncio
# import os
# from datetime import date
# from tradingagents.services.orchestrator import _run_from_cli

# async def main():
#     as_of_date = os.getenv("DBG_AS_OF_DATE", date.today().isoformat())
#     await _run_from_cli()

# if __name__ == "__main__":
#     asyncio.run(main())

from datetime import date
import traceback

import os
from dotenv import load_dotenv, find_dotenv
import asyncio

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

async def main():
    await _run_from_cli()

from tradingagents.services.orchestrator import _run_from_cli

if __name__ == "__main__":
    print("🔍 Starting debug: _run_from_cli()")

    print(f"ENV DEBUG_MODE={os.getenv('DEBUG_MODE')}  ALPHAVANTAGE_API_KEY set? {'yes' if os.getenv('ALPHAVANTAGE_API_KEY') else 'no'}")

    try:
        # ticker = "AAPL"
        # as_of = date(2025, 1, 15)
        # print(f"Fetching news for {ticker} as of {as_of} ...")

        asyncio.run(main())
        print(f"✅ Fetch complete.  items returned.\n")

    except Exception as e:
        print("❌ Error occurred during fetch:")
        traceback.print_exc()
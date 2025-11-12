import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    """
    Configure global logging for the TradingAgents system.
    """
    # Define a standard log format
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | "
        "%(message)s"
    )

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
    )

    # Silence noisy libraries (optional)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.info(f"✅ Logging initialized at level: {level.upper()}")

def get_logger(name: str | None = None) -> logging.Logger:
    """
    Convenience wrapper to get a project-wide logger instance.
    This respects the global logging configuration.
    """
    return logging.getLogger(name)
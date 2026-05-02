"""
MANO Structured Logging Configuration.
Uses structlog for JSON-formatted, context-rich logging.

WHY STRUCTLOG?
- Standard print() is unstructured text that's impossible to search/filter in production.
- structlog produces JSON logs with consistent fields (timestamp, level, event, context),
  which integrate directly with log aggregation tools (ELK, Grafana Loki, CloudWatch).
"""
import logging
import sys
import structlog


def setup_logging(log_level: str = "INFO"):
    """
    Configures structlog for the entire application.
    Call this ONCE at startup (in main.py lifespan).
    """

    # Step 1: Configure Python's built-in logging (structlog wraps around it)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )

    # Step 2: Configure structlog processors (the pipeline that transforms each log event)
    structlog.configure(
        processors=[
            # Adds log level (INFO, ERROR, etc.) to the event dict
            structlog.stdlib.add_log_level,
            # Adds ISO-8601 timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Adds caller info (file, function, line number) — great for debugging
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            # Pretty-prints dicts and lists in log messages
            structlog.processors.format_exc_info,
            # Final renderer: JSON for production, colorful console for development
            structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "mano"):
    """
    Returns a bound logger with the given name.

    Usage:
        from backend.app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("model_loaded", model="lstm", device="cuda")
    """
    return structlog.get_logger(name)

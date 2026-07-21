"""Central logging configuration."""

import logging

from restaurant_voice_ai.observability.logging import JsonFormatter


class ConsoleFormatter(logging.Formatter):
    """Readable formatter that appends selected structured context."""

    context_fields = ("environment", "version", "method", "path", "status_code", "duration_ms")

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        context = " ".join(
            f"{field}={getattr(record, field)}"
            for field in self.context_fields
            if hasattr(record, field)
        )
        return f"{message} {context}" if context else message


def configure_logging(level: str, log_format: str = "text") -> None:
    """Configure application logging without logging request bodies."""
    handler = logging.StreamHandler()
    formatter: logging.Formatter
    if log_format == "json":
        formatter = JsonFormatter()
    else:
        formatter = ConsoleFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a named application logger."""
    return logging.getLogger(name)

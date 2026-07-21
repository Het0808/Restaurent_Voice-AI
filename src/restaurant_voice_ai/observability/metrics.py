"""Bounded-label Prometheus metrics registry."""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class ApplicationMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.http_requests = Counter(
            "restaurant_http_requests_total",
            "HTTP requests",
            ("method", "route", "status_group"),
            registry=self.registry,
        )
        self.http_latency = Histogram(
            "restaurant_http_request_duration_seconds",
            "HTTP request latency",
            ("method", "route"),
            registry=self.registry,
        )
        self.active_requests = Gauge(
            "restaurant_http_active_requests", "Active HTTP requests", registry=self.registry
        )
        self.conversation_turns = Counter(
            "restaurant_conversation_turns_total",
            "Completed conversation turns",
            ("intent", "provider", "fallback"),
            registry=self.registry,
        )
        self.voice_sessions = Counter(
            "restaurant_voice_sessions_total",
            "Voice sessions",
            ("event",),
            registry=self.registry,
        )
        self.active_voice_sessions = Gauge(
            "restaurant_voice_active_sessions", "Active voice sessions", registry=self.registry
        )
        self.telephony_calls = Counter(
            "restaurant_telephony_calls_total",
            "Twilio call lifecycle events",
            ("event",),
            registry=self.registry,
        )
        self.telephony_escalations = Counter(
            "restaurant_telephony_escalations_total",
            "Calls escalated to staff",
            ("reason",),
            registry=self.registry,
        )
        self.telephony_speech = Counter(
            "restaurant_telephony_speech_total",
            "Speech webhook outcomes",
            ("outcome",),
            registry=self.registry,
        )


metrics = ApplicationMetrics()

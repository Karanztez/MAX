"""max_ai.agent forwarder."""
try:
    from max_ai.agent import MaxAgent, AIClient
except (ImportError, ModuleNotFoundError):
    from src.max_ai.agent import MaxAgent, AIClient  # type: ignore[no-redef]

__all__ = ["MaxAgent", "AIClient"]

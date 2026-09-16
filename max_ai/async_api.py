"""max_ai.async_api forwarder."""
try:
    from max_ai.async_api import ask_async, stream_async
except (ImportError, ModuleNotFoundError):
    from src.max_ai.async_api import ask_async, stream_async  # type: ignore[no-redef]

__all__ = ["ask_async", "stream_async"]

"""max_ai.session forwarder."""
try:
    from max_ai.session import MaxSession, Response
except (ImportError, ModuleNotFoundError):
    from src.max_ai.session import MaxSession, Response  # type: ignore[no-redef]

__all__ = ["MaxSession", "Response"]

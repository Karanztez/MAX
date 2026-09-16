"""max_ai.team forwarder."""
try:
    from max_ai.team import MaxTeam, TeamMember
except (ImportError, ModuleNotFoundError):
    from src.max_ai.team import MaxTeam, TeamMember  # type: ignore[no-redef]

__all__ = ["MaxTeam", "TeamMember"]

"""Shared execution defaults; source semantics cannot grant host authority."""

EXECUTION_MODES = frozenset({"core", "governed", "strict", "pure"})


def resolve_execution_mode(
    declared_mode: str | None = None,
    mode: str | None = None,
    *,
    allow_ungoverned: bool = False,
    force_mode: bool = False,
) -> tuple[str, bool]:
    """Return semantic mode and the minimum required governance posture.

    Only an explicit trusted-host opt-out can permit ungoverned execution.
    A governed request or declaration strengthens even that opt-out. Strict
    initialization and pure-effect semantics remain separate from governance.
    """
    if type(allow_ungoverned) is not bool or type(force_mode) is not bool:
        raise TypeError("execution posture options must be Bool values")
    for candidate in (declared_mode, mode):
        if candidate is not None and (
            type(candidate) is not str or candidate not in EXECUTION_MODES
        ):
            raise ValueError(f"unsupported execution mode: {candidate!r}")
    requested = (
        mode if mode is not None else ("core" if allow_ungoverned else "governed")
    )
    semantic = requested if force_mode or declared_mode is None else declared_mode
    governed = (
        not allow_ungoverned or requested == "governed" or declared_mode == "governed"
    )
    return semantic, governed

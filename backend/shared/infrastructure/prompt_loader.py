"""Load versioned .md prompt files co-located with their owning modules.

Supports ``{{INCLUDE_NAME}}`` placeholders that are resolved against the
shared partials registry.  Register partials at import time via
``register_partial``.
"""

from functools import cache
from pathlib import Path

_partials: dict[str, str] = {}


def register_partial(name: str, content: str) -> None:
    """Make *content* available for ``{{name}}`` substitution in prompts."""
    _partials[name] = content


@cache
def load_prompt(anchor: str, filename: str) -> str:
    """Return the contents of *filename* resolved relative to *anchor*.

    Any ``{{KEY}}`` tokens whose KEY has been registered via
    ``register_partial`` are expanded inline.

    Usage::

        SYSTEM_PROMPT = load_prompt(__file__, "prompt.md")
    """
    text = (Path(anchor).resolve().parent / filename).read_text(encoding="utf-8")
    for key, value in _partials.items():
        text = text.replace("{{" + key + "}}", value)
    return text

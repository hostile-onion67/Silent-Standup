"""GitHub activity retrieval for Silent Standup.

The requested ``github/`` project folder collides with PyGithub's package name.
This module loads PyGithub's public package initializer into the shared package
namespace, then keeps ``github.activity`` available for this application's code.
"""

from pathlib import Path
import sys

_LOCAL_PACKAGE = Path(__file__).resolve().parent
_pygithub_init: Path | None = None
for _search_path in sys.path:
    _candidate = Path(_search_path) / "github" / "__init__.py"
    if _candidate.is_file() and _candidate.parent.resolve() != _LOCAL_PACKAGE:
        _pygithub_init = _candidate
        break

if _pygithub_init is None:
    raise ImportError("PyGithub is required. Install dependencies with pip install -r requirements.txt.")

__path__.append(str(_pygithub_init.parent))
exec(compile(_pygithub_init.read_text(encoding="utf-8"), str(_pygithub_init), "exec"))

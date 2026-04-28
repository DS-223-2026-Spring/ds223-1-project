"""Entrypoint for standalone final DS output generation."""

try:
    from .final_outputs import main
except ImportError:  # pragma: no cover - supports running from inside the ds container
    from final_outputs import main


if __name__ == "__main__":
    raise SystemExit(main())

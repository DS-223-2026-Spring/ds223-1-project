"""DS service entrypoint."""

try:
    from .synthetic.cli import main
except ImportError:  # pragma: no cover - supports running inside the ds container
    from synthetic.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

"""Entrypoint for synthetic dataset exploratory analysis."""

try:
    from ds.eda import main
except ImportError:  # pragma: no cover - supports running from inside the ds container
    from eda import main


if __name__ == "__main__":
    raise SystemExit(main())

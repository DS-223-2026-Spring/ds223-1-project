"""Entrypoint for synthetic dataset exploratory analysis."""

try:
    from .eda import main
except ImportError:  # supports running from inside the ds container
    from eda import main


if __name__ == "__main__":
    raise SystemExit(main())

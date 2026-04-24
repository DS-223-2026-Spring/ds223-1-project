"""Entrypoint for baseline policy comparison."""

try:
    from ds.baselines import main
except ImportError:  # supports running from inside the ds container
    from baselines import main


if __name__ == "__main__":
    raise SystemExit(main())

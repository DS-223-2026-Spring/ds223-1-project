"""Entrypoint for standalone synthetic data generation."""

try:
    from ds.synthetic.cli import main
except ImportError:  # supports running from inside the ds container
    from synthetic.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

"""Repository-level entrypoint for standalone synthetic data generation."""

from ds.synthetic.cli import main


if __name__ == "__main__":
    raise SystemExit(main())

"""Entrypoint for standalone synthetic data generation."""

try:
    from ._routing import load_ds_attr
except ImportError:  # pragma: no cover - supports direct execution in DS container
    from _routing import load_ds_attr

main = load_ds_attr("synthetic.cli", "main")


if __name__ == "__main__":
    raise SystemExit(main())

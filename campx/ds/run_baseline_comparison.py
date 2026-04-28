"""Entrypoint for baseline policy comparison."""

try:
    from ._routing import load_ds_attr
except ImportError:  # pragma: no cover - supports direct execution in DS container
    from _routing import load_ds_attr

main = load_ds_attr("baselines", "main")


if __name__ == "__main__":
    raise SystemExit(main())

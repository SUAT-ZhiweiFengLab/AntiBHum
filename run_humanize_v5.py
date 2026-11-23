"""Compatibility entry point. Install the AntiBHum binary wheel first."""

if __name__ == "__main__":
    try:
        from antibhum.cli import main
    except ImportError as exc:
        raise SystemExit(
            f"Install the AntiBHum Release wheel matching your Python and platform first. Details: {exc}"
        ) from exc
    main()

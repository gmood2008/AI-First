import os


def main() -> None:
    try:
        import uvicorn
    except ImportError as e:
        raise SystemExit("uvicorn is required. Install: pip install -e .[api]") from e

    host = os.getenv("AIF_RUNTIME_API_HOST", "0.0.0.0")
    port = int(os.getenv("AIF_RUNTIME_API_PORT", "8030"))

    uvicorn.run("runtime.api.mission_control:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()

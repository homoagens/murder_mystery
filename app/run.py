import os
import argparse
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

from app import app


def main():
    parser = argparse.ArgumentParser(description="Murder Mystery — web UI")
    parser.add_argument("--host", default=os.getenv("WEB_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("WEB_PORT", 7860)))
    args = parser.parse_args()
    print(f"Murder Mystery UI → http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()

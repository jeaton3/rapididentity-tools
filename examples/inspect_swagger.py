"""Utility for downloading the swagger/OpenAPI document and locating paths.

Usage:
    python examples/inspect_swagger.py --config prod

This was described in the conversation earlier as a way to figure out the
correct user-related endpoints when the library author doesn't know the
tenant-specific paths ahead of time.  It simply loads the configuration, makes
an authenticated GET request to `/api/rest/api-docs` and then searches the
result for keywords like "user" or "person" so you can derive the right URL
format. The fetched JSON is also saved to ``~/rapididentity/{tier}/swagger.json``.
"""
import argparse
import json
import sys
from pathlib import Path

# ensure the package is importable when run from the workspace root
root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from rapididentity.client import RapidIdentityClient
from rapididentity.config import Config


def find_paths(swagger: dict, keywords: list[str]) -> list[str]:
    paths = []
    for p in swagger.get("paths", {}).keys():
        if any(kw.lower() in p.lower() for kw in keywords):
            paths.append(p)
    return paths


def resolve_config_path(config_name: str) -> Path:
    config_file = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return Path.home() / "rapididentity" / "config" / config_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect swagger and list matching paths")
    parser.add_argument(
        "--config",
        default="prod",
        help="Config name under ~/rapididentity/config (e.g. --config prod)",
    )
    return parser.parse_args()


def save_swagger(swagger: dict, tier: str) -> Path:
    output_dir = Path.home() / "rapididentity" / tier
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "swagger.json"
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(swagger, f, indent=2)
        f.write("\n")
    return output_path


def main():
    args = parse_args()
    config_file = resolve_config_path(args.config)
    if not config_file.exists():
        print(f"Configuration file {config_file} not found")
        sys.exit(1)

    # Config accepts an optional file path which it will load
    config = Config(str(config_file))
    tier = str(config.get_tier())

    # use helper to build client from config
    with RapidIdentityClient.from_config(config) as client:
        # the client already prepends "/api/rest" so only provide the suffix
        swagger = client.get("/api-docs")

        # some instances return the Swagger UI HTML instead of raw JSON;
        # if that's the case, fetch the JSON directly at /swagger.json
        if (
            isinstance(swagger, dict)
            and "data" in swagger
            and isinstance(swagger["data"], str)
            and "Swagger UI" in swagger["data"]
        ):
            print("received HTML page; retrying with /swagger.json")
            swagger = client.get("/swagger.json")

    if not isinstance(swagger, dict):
        print("Swagger response was not JSON object data")
        sys.exit(1)

    output_path = save_swagger(swagger, tier)
    print(f"Saved swagger document to {output_path}")

    keywords = ["user", "person", "people", "account"]
    matches = find_paths(swagger, keywords)

    if not matches:
        print("No matching paths found in swagger document.")
    else:
        print("Possible user-related paths:")
        for p in matches:
            print(f"  - {p}")


if __name__ == "__main__":
    main()

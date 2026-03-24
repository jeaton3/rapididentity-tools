"""Fetch and print Connect adapters.

Usage:
    python examples/get_adapters.py --config prod

Loads config from ``~/rapididentity/config/{name}.json`` and prints the result
of ``RapidIdentityClient.from_config(cfg).connect.get_adapters()``.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# ensure the project package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rapididentity import Config, RapidIdentityClient
from rapididentity.exceptions import AuthenticationError, APIError, NotFoundError


def resolve_config_path(config_name: str) -> Path:
    config_file = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return Path.home() / "rapididentity" / "config" / config_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and print Connect adapters")
    parser.add_argument(
        "--config",
        default="prod",
        help="Config name under ~/rapididentity/config (e.g. --config prod)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = resolve_config_path(args.config)

    if not config_path.exists():
        print(f"Configuration file {config_path} not found")
        sys.exit(1)

    cfg = Config(str(config_path))
    with RapidIdentityClient.from_config(cfg) as client:
        try:
            adapters = client.connect.get_adapters()
            print(json.dumps(adapters, indent=2))
        except AuthenticationError:
            print("Access forbidden: credentials lack permission to read adapters")
        except NotFoundError:
            print("Endpoint not found. Are you pointing at the correct host?")
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}")
        except Exception as e:
            print("Request failed:", e)


if __name__ == "__main__":
    main()
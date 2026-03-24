"""POST an actionDef XML file to /admin/connect/actions.

Usage:
    python examples/put_action.py --config prod ~/rapididentity/test/xml/SalesforceToMeta.xml
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
    parser = argparse.ArgumentParser(description="POST actionDef XML to /admin/connect/actions")
    parser.add_argument(
        "--config",
        default="prod",
        help="Config name under ~/rapididentity/config (e.g. --config prod)",
    )
    parser.add_argument(
        "xml_file",
        help="Path to actionDef XML file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = resolve_config_path(args.config)
    xml_path = Path(args.xml_file).expanduser()

    if not config_path.exists():
        print(f"Configuration file {config_path} not found")
        sys.exit(1)

    if not xml_path.exists() or not xml_path.is_file():
        print(f"XML file {xml_path} not found")
        sys.exit(1)

    xml_text = xml_path.read_text(encoding="utf-8")

    cfg = Config(str(config_path))
    with RapidIdentityClient.from_config(cfg) as client:
        try:
            result = client.connect.post_action(xml_text)
            if isinstance(result, (dict, list)):
                print(json.dumps(result, indent=2))
            else:
                print(result)
        except AuthenticationError:
            print("Access forbidden: credentials lack permission to post actions")
        except NotFoundError:
            print("Endpoint not found. Are you pointing at the correct host?")
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}")
        except Exception as e:
            print("Request failed:", e)


if __name__ == "__main__":
    main()

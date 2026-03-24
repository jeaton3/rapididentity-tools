"""Archive all available historical versions for each Connect actionDef.

Usage:
    python examples/archive_action_history.py --config prod

For each actionDef returned by ``client.connect.get_actions()``, this script:
1) Calls ``/admin/connect/actionSetHistory/{guid}`` to discover versions.
2) Calls ``/admin/connect/actionSetHistory/{guid}/{version}`` for each version.
3) Saves XML to ``~/rapididentity/{tier}/archive/xml/{name}-{version}.xml``.
4) Saves decoded script to ``~/rapididentity/{tier}/archive/js/{name}-{version}.js``.
"""

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, List, Optional

# ensure the project package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rapididentity import Config, RapidIdentityClient
from rapididentity.exceptions import AuthenticationError, APIError, NotFoundError
from rapididentity.utils import actiondef_xml_to_script
from rapididentity.utils.helpers import safe_filename, extract_xml_payload, write_indented_xml
from rapididentity.utils.actiondefs import iter_action_defs, has_actions_content, extract_versions

NS_URI = "urn:idauto.net:dss:actiondef"
FNAME_SAFE = re.compile(r"[^A-Za-z0-9_.-]")
VERSION_SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")


def resolve_config_path(config_name: str) -> Path:
    config_file = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return Path.home() / "rapididentity" / "config" / config_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive historical Connect actionDef XML and decoded script versions"
    )
    parser.add_argument(
        "--config",
        default="prod",
        help="Config name under ~/rapididentity/config (e.g. --config prod)",
    )
    return parser.parse_args()





def archive_action_history(config_path: Path) -> None:
    if not config_path.exists():
        print(f"Configuration file {config_path} not found")
        sys.exit(1)

    cfg = Config(str(config_path))
    tier = str(cfg.get_tier())
    archive_root = Path.home() / "rapididentity" / tier / "archive"
    xml_dir = archive_root / "xml"
    js_dir = archive_root / "js"
    xml_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)

    actions_seen = 0
    versions_saved = 0
    actions_without_id = 0
    actions_without_content = 0
    actions_without_versions = 0
    actions_failed_history = 0
    actions_missing_history = 0
    versions_failed_fetch = 0
    versions_missing = 0
    xml_headers = {"Accept": "text/xml"}

    with RapidIdentityClient.from_config(cfg) as client:
        # have to get everything, not just metaDataOnly, to discover which actionDefs
        # actually have content and are worth archiving history for
        actions_xml = client.connect.get_actions(metaDataOnly=False)

        for action_def in _iter_action_defs(actions_xml):
            actions_seen += 1
            action_id = action_def.get("id")
            action_name = action_def.get("name", "unnamed")
            safe_name = _safe_name(action_name)


            if not action_id:
                actions_without_id += 1
                print(f"Skipping action without id: {action_name}")
                continue

            #print(f"Processing action: {action_name} (id: {action_id})")
            if not _has_actions_content(action_def):
                actions_without_content += 1
                #print(f"Skipping action with no actions: {action_name}")
                continue
            try:
                history_payload = client.connect.get_actionset_history(action_id)
            except NotFoundError:
                actions_missing_history += 1
                print(f"{action_name}: history not found")
                continue
            except APIError as e:
                actions_failed_history += 1
                print(f"{action_name}: failed to fetch history ({e.status_code})")
                continue

            versions = _extract_versions(history_payload)

            if not versions:
                actions_without_versions += 1
                continue

            for version in versions:
                xml_path = xml_dir / f"{safe_name}-{version}.xml"
                js_path = js_dir / f"{safe_name}-{version}.js"

                if xml_path.exists():
                    #print(f"Skipping existing file: {xml_path.name}")
                    continue

                print("Fetching history for", action_name, "version", version)
                try:
                    version_xml = client.connect.get_actionset_history(action_id, version=version)
                except NotFoundError:
                    versions_missing += 1
                    print(f"  - version {version}: not found")
                    continue
                except APIError as e:
                    versions_failed_fetch += 1
                    print(f"  - version {version}: fetch failed ({e.status_code})")
                    continue
                
       
                xml_path = xml_dir / f"{safe_name}-{version}.xml"
                js_path = js_dir / f"{safe_name}-{version}.js"

                # Write indented XML matching get_actions.py output
                try:
                    root = ET.fromstring(version_xml)
                    tree = ET.ElementTree(root)
                    # Register the actiondef namespace as the default to avoid
                    # auto-generated ns0: prefixes when serializing.
                    ET.register_namespace("", NS_URI)
                    ET.indent(tree, space="  ")
                    tree.write(xml_path, encoding="unicode", xml_declaration=True)
                except ET.ParseError:
                    # Fall back to raw write if parsing fails
                    xml_path.write_text(version_xml, encoding="utf-8")

                script_text = actiondef_xml_to_script(version_xml)
                js_path.write_text(script_text, encoding="utf-8")

                versions_saved += 1

    print()
    print(f"Actions scanned: {actions_seen}")
    print(f"Actions with no content: {actions_without_content}")
    print(f"Actions missing id: {actions_without_id}")
    print(f"Actions with no history versions: {actions_without_versions}")
    print(f"Actions failed history fetch: {actions_failed_history}")
    print(f"Actions missing history endpoint: {actions_missing_history}")
    print(f"Versions failed fetch: {versions_failed_fetch}")
    print(f"Versions not found: {versions_missing}")
    print(f"Versions archived: {versions_saved}")
    print(f"XML output: {xml_dir}")
    print(f"JS output: {js_dir}")


def main() -> None:
    args = parse_args()
    config_path = resolve_config_path(args.config)

    try:
        archive_action_history(config_path)
    except AuthenticationError:
        print("Access forbidden: credentials lack permission to read action history")
    except NotFoundError:
        print("Action history endpoint not found. Are you pointing at the correct host?")
    except APIError as e:
        print(f"API error {e.status_code}: {e.message}")
    except Exception as e:
        print("Request failed:", e)


if __name__ == "__main__":
    main()

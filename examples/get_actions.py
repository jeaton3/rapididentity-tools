"""Fetch all Connect actionDefs and write each one to its own XML file.

Usage:
    python examples/get_actions.py --config prod [--output-dir /path/to/output]

XML actionDefs are saved as <output_dir>/xml/<name>.xml and script copies as
<output_dir>/actions/<name>.js. If output_dir is omitted, it defaults to
``~/rapididentity/{tier}`` where ``tier`` is read from config.
"""
import argparse
import sys, os
import re
import logging
import xml.etree.ElementTree as ET
from typing import Optional

# ensure the project package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")

from rapididentity import Config, RapidIdentityClient
from rapididentity.exceptions import AuthenticationError, APIError, NotFoundError
from rapididentity.utils import actiondef_element_to_script

NS_URI = "urn:idauto.net:dss:actiondef"
FNAME_SAFE = re.compile(r"[^A-Za-z0-9_.-]")


def _local_name(tag: str) -> str:
    if isinstance(tag, str) and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_modified_ms(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _existing_actiondef_modified_ms(xml_path: str) -> Optional[int]:
    if not os.path.exists(xml_path):
        return None

    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return None

    for elem in root.iter():
        if _local_name(elem.tag) != "actionDef":
            continue
        return _parse_modified_ms(elem.get("modifiedMS") or elem.get("modifiedMs"))
    return None


def split_action_defs(xml_text: str, out_dir: str):
    xml_dir = os.path.join(out_dir, "xml")
    vendor_xml_dir = os.path.join(out_dir, "vendor-xml")
    actions_dir = os.path.join(out_dir, "js")

    os.makedirs(xml_dir, exist_ok=True)
    os.makedirs(vendor_xml_dir, exist_ok=True)
    os.makedirs(actions_dir, exist_ok=True)

    # Register the actiondef namespace as the default (no prefix) so
    # generated files use xmlns="..." rather than an `ad:` prefix.
    ET.register_namespace("", NS_URI)

    root = ET.fromstring(xml_text)
    xml_count = 0
    skipped_xml_count = 0
    vendor_xml_count = 0
    skipped_vendor_xml_count = 0
    js_count = 0

    for ad in root.findall(f"{{{NS_URI}}}actionDef"):
        name = ad.get("name", "unnamed")
        safe = FNAME_SAFE.sub("_", name) or "unnamed"
        xml_path = os.path.join(xml_dir, f"{safe}.xml")
        vendor_xml_path = os.path.join(vendor_xml_dir, f"{safe}.xml")
        js_path = os.path.join(actions_dir, f"{safe}.js")

        # Create a namespace-stripped copy of the element so output does not
        # include any xmlns declaration or namespace prefixes, and remove
        # top-level `id`, `version`, and `project` attributes.
        def _strip_ns(elem, remove_attrs: set | None = None):
            remove_attrs = remove_attrs or set()
            tag = elem.tag
            if isinstance(tag, str) and "}" in tag:
                tag = tag.split("}", 1)[1]
            new = ET.Element(tag)
            for k, v in elem.attrib.items():
                if k in remove_attrs:
                    continue
                new.set(k, v)
            # preserve text (if any)
            if elem.text and elem.text.strip():
                new.text = elem.text
            for child in list(elem):
                new.append(_strip_ns(child, None))
            return new

        new_root = _strip_ns(ad, remove_attrs={"id", "version", "project"})
        # Wrap in an <actionDefs> root with the actiondef namespace as
        # the default via the xmlns attribute (no prefix on child tags).
        wrapper = ET.Element("actionDefs")
        wrapper.set("xmlns", NS_URI)
        wrapper.append(new_root)
        tree2 = ET.ElementTree(wrapper)
        ET.indent(tree2, space="  ")

        actions_block = ad.find(f"{{{NS_URI}}}actions")
        has_actions = actions_block is not None and len(actions_block.findall(f"{{{NS_URI}}}action")) > 0
        if has_actions:
            modified_ms = _parse_modified_ms(ad.get("modifiedMS") or ad.get("modifiedMs"))
            existing_modified_ms = _existing_actiondef_modified_ms(xml_path)

            if existing_modified_ms is None or modified_ms is None or modified_ms > existing_modified_ms:
                print(f"Writing XML and script for {name} with modifiedMS={modified_ms} (existing file has modifiedMS={existing_modified_ms})")
                tree2.write(xml_path, encoding="unicode", xml_declaration=True)
                xml_count += 1

                script_text = actiondef_element_to_script(ad)
                with open(js_path, "w", encoding="utf-8") as js_file:
                    js_file.write(script_text)
                js_count += 1
            else:
                logging.info(f"Skipping XML and script export for {name} with modifiedMS={modified_ms} (existing file has modifiedMS={existing_modified_ms})")
                skipped_xml_count += 1
        else:
            # only overwrite vendor_xml_path if the modifiedMS attribute is newer than the existing file (if any), to avoid unnecessary churn on content-free actionDefs
            modified_ms = _parse_modified_ms(ad.get("modifiedMS") or ad.get("modifiedMs"))
            existing_modified_ms = _existing_actiondef_modified_ms(vendor_xml_path)

            if existing_modified_ms is None or modified_ms is None or modified_ms > existing_modified_ms:
                tree2.write(vendor_xml_path, encoding="unicode", xml_declaration=True)
                vendor_xml_count += 1
            else:
                logging.info(f"Skipping vendor XML for {name} with modifiedMS={modified_ms} (existing file has modifiedMS={existing_modified_ms})")
                skipped_vendor_xml_count += 1

    logging.info(f"Wrote {xml_count} actionDef XML files to {xml_dir}/")
    logging.info(f"Wrote {js_count} actionDef script files to {actions_dir}/")
    logging.info(f"Skipped {skipped_xml_count} actionDefs for XML and script export due to unchanged modifiedMS")
    logging.info(f"Wrote {vendor_xml_count} content-free actionDef XML files to {vendor_xml_dir}/")
    logging.info(f"Skipped {skipped_vendor_xml_count} content-free actionDefs for script export")

    if (js_count > 0):
        # we made relevant updates, return true
        return True

    # no relevant updates
    return False

def get_actionsets(config_path: str = "prod-config.json", out_dir: Optional[str] = None) -> None:
    cfg = Config(config_path)
    tier = str(cfg.get_tier())
    target_dir = out_dir or os.path.join(os.path.expanduser("~"), "rapididentity", tier)
    with RapidIdentityClient.from_config(cfg) as client:
        try:
            xml_text = client.connect.get_actions()
            return split_action_defs(xml_text, target_dir)
        except AuthenticationError:
            print("Access forbidden: credentials lack permission to read actions")
        except NotFoundError:
            print("Endpoint not found.  Are you pointing at the correct host?")
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}")
        except Exception as e:
            print("Request failed:", e)


def resolve_config_path(config_name: str) -> str:
    config_file = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return os.path.join(os.path.expanduser("~"), "rapididentity", "config", config_file)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch actionDefs and write XML/JS outputs")
    parser.add_argument(
        "--config",
        default="prod",
        help="Config name under ~/rapididentity/config (e.g. --config prod)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory override",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    config_path = resolve_config_path(args.config)
    ret = get_actionsets(config_path, args.output_dir)
    if (ret):
        exit(0)
    else:
        exit(1)

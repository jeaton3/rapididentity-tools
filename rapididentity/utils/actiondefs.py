"""Utilities for converting RapidIdentity actionDef XML into script text."""

from __future__ import annotations

import html
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Set

NS_URI = "urn:idauto.net:dss:actiondef"


def _tag(name: str) -> str:
    return f"{{{NS_URI}}}{name}"


def _get_args(action: ET.Element) -> Dict[Optional[str], str]:
    return {
        arg.get("name"): html.unescape(arg.get("value", ""))
        for arg in action.findall(_tag("arg"))
        if arg.get("value") is not None
    }


def _get_arg_elem(action: ET.Element, name: str) -> Optional[ET.Element]:
    for arg in action.findall(_tag("arg")):
        if arg.get("name") == name:
            return arg
    return None


def _child_actions(arg_elem: Optional[ET.Element]) -> List[ET.Element]:
    if arg_elem is None:
        return []
    return list(arg_elem.findall(_tag("action")))


def _positional_args(action: ET.Element, skip: Optional[Set[str]] = None) -> List[str]:
    skip = skip or set()
    parts: List[str] = []
    for arg in action.findall(_tag("arg")):
        if arg.get("name") in skip:
            continue
        value = arg.get("value")
        if value is not None:
            parts.append(html.unescape(value))
    return parts


def _render_actions(actions: List[ET.Element], indent: int = 0, parent_disabled: bool = False) -> List[str]:
    pad = "    " * indent
    lines: List[str] = []

    for action in actions:
        name = action.get("name", "")
        output_var = action.get("outputVar", "").strip()
        disabled = action.get("disabled", "false") == "true"

        action_lines: List[str] = []

        if name == "comment":
            action_lines.append(f"{pad}# {html.unescape(_get_args(action).get('comment', ''))}")

        elif name == "section":
            args = _get_args(action)
            label = args.get("label", "").strip()
            children = _child_actions(_get_arg_elem(action, "do"))

            header = f"{label}: {{" if label else "{"
            action_lines.append(f"{pad}{header}")
            action_lines.extend(_render_actions(children, indent + 1, parent_disabled or disabled))
            action_lines.append(f"{pad}}}")

        elif name == "if":
            args = _get_args(action)
            condition = args.get("condition", "")
            then_actions = _child_actions(_get_arg_elem(action, "then"))
            else_actions = _child_actions(_get_arg_elem(action, "else"))

            action_lines.append(f"{pad}if ({condition}) {{")
            action_lines.extend(_render_actions(then_actions, indent + 1, parent_disabled or disabled))
            action_lines.append(f"{pad}}} else {{")
            action_lines.extend(_render_actions(else_actions, indent + 1, parent_disabled or disabled))
            action_lines.append(f"{pad}}}")

        elif name == "forEach":
            args = _get_args(action)
            label = args.get("label", "").strip()
            variable = args.get("variable", "")
            collection = args.get("collection", "")
            children = _child_actions(_get_arg_elem(action, "do"))

            label_prefix = f"{label}: " if label else ""
            action_lines.append(f"{pad}{label_prefix}forEach {variable}, {collection} {{")
            action_lines.extend(_render_actions(children, indent + 1, parent_disabled or disabled))
            action_lines.append(f"{pad}}}")

        elif name == "continue":
            label = _get_args(action).get("label", "")
            action_lines.append(f"{pad}continue {label}".rstrip())

        elif name == "break":
            label = _get_args(action).get("label", "")
            action_lines.append(f"{pad}break {label}".rstrip())

        elif name == "return":
            value = _get_args(action).get("value", "")
            action_lines.append(f"{pad}return {value}")

        elif name == "setVariable":
            args = _get_args(action)
            var_name = args.get("name", "")
            value = args.get("value", "")
            action_lines.append(f"{pad}{var_name} = {value}")

        elif name == "createRecord":
            if output_var:
                action_lines.append(f"{pad}{output_var} = createRecord()")
            else:
                action_lines.append(f"{pad}createRecord()")

        else:
            args_str = ", ".join(_positional_args(action, skip={"label"}))
            if output_var:
                action_lines.append(f"{pad}{output_var} = {name}({args_str})")
            else:
                action_lines.append(f"{pad}{name}({args_str})")

        if disabled:
            action_lines = [f"## {line}" for line in action_lines]

        lines.extend(action_lines)

    return lines


def actiondef_element_to_script(action_def: ET.Element) -> str:
    """Render a single ``actionDef`` element to readable script text."""
    name = action_def.get("name", "unknown")
    description = action_def.get("description", "")
    args_block = action_def.find(_tag("argDefs"))
    actions_block = action_def.find(_tag("actions"))

    header_lines = [f"// actionDef: {name}"]
    if description:
        header_lines.append(f"// {description}")

    if args_block is not None:
        header_lines.append("//")
        header_lines.append("// Arguments:")
        for arg_def in args_block.findall(_tag("argDef")):
            arg_name = arg_def.get("name", "")
            arg_type = arg_def.get("type", "")
            optional = arg_def.get("optional", "false") == "true"
            optional_label = " (optional)" if optional else ""
            header_lines.append(f"//   {arg_name}: {arg_type}{optional_label}")

    header_lines.append("")
    body_lines = _render_actions(list(actions_block) if actions_block is not None else [])
    return "\n".join(header_lines + body_lines) + "\n"


def actiondef_xml_to_script(xml_text: str) -> str:
    """Render actionDef script text from XML containing one ``actionDef``."""
    root = ET.fromstring(xml_text)
    if root.tag == _tag("actionDef"):
        action_def = root
    elif root.tag == _tag("actionSetVersion"):
        action_def = root
    else:
        action_def = root.find(_tag("actionDef")) or root.find(_tag("actionSetVersion"))

    if action_def is None:
        raise ValueError("No actionDef element found")

    return actiondef_element_to_script(action_def)


def actiondef_file_to_script(xml_path: str) -> str:
    """Render actionDef script text from an XML file path."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    if root.tag == _tag("actionDef"):
        action_def = root
    else:
        action_def = root.find(_tag("actionDef"))

    if action_def is None:
        if root.tag == _tag("actionSetVersion"):
            action_def = root
        else:
            action_def = root.find(_tag("actionSetVersion"))

    if action_def is None:
        raise ValueError(f"No actionDef element found in {xml_path}")

    return actiondef_element_to_script(action_def)


def iter_action_defs(actions_xml: str) -> Iterable[ET.Element]:
    """Yield actionDef or actionSetVersion elements from an XML document."""
    root = ET.fromstring(actions_xml)
    if root.tag == f"{{{NS_URI}}}actionDef":
        yield root
        return

    if root.tag == f"{{{NS_URI}}}actionSetVersion":
        yield root
        return

    for action_def in root.findall(f"{{{NS_URI}}}actionDef"):
        yield action_def


def has_actions_content(action_def: ET.Element) -> bool:
    """Return True if the given `action_def` contains one or more `<action>` elements."""
    actions_block = action_def.find(f"{{{NS_URI}}}actions")
    return actions_block is not None and len(actions_block.findall(f"{{{NS_URI}}}action")) > 0


def _coerce_version(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return str(int(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        if "<" in stripped or ">" in stripped:
            return None
        if len(stripped) > 64:
            return None
        VERSION_SAFE = re.compile(r"^[A-Za-z0-9_.-]+$")
        if not VERSION_SAFE.match(stripped):
            return None
        return stripped
    return None


def extract_versions_from_xml(xml_text: str) -> List[str]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    values: List[str] = []
    for elem in root.iter():
        for attr_name in ("version", "actionSetVersion", "revision"):
            version = _coerce_version(elem.get(attr_name))
            if version:
                values.append(version)

    unique = sorted(set(values), key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))
    return unique


def extract_versions(payload: Any) -> List[str]:
    values: List[str] = []

    if isinstance(payload, str):
        return extract_versions_from_xml(payload)

    if isinstance(payload, dict):
        candidates = payload.get("versions")
        if candidates is None:
            candidates = payload.get("history")
        if candidates is None:
            candidates = payload.get("xml")
        if candidates is None and "data" in payload:
            candidates = payload["data"]
    else:
        candidates = payload

    if isinstance(candidates, list):
        for item in candidates:
            if isinstance(item, dict):
                version = (
                    _coerce_version(item.get("version"))
                    or _coerce_version(item.get("actionSetVersion"))
                    or _coerce_version(item.get("revision"))
                )
                if version:
                    values.append(version)
            else:
                version = _coerce_version(item)
                if version:
                    values.append(version)
    elif isinstance(candidates, dict):
        xml_candidate = candidates.get("xml")
        if isinstance(xml_candidate, str):
            values.extend(extract_versions_from_xml(xml_candidate))

        version = (
            _coerce_version(candidates.get("version"))
            or _coerce_version(candidates.get("actionSetVersion"))
            or _coerce_version(candidates.get("revision"))
        )
        if version:
            values.append(version)
    elif isinstance(candidates, str):
        values.extend(extract_versions_from_xml(candidates))

        version = _coerce_version(candidates)
        if version:
            values.append(version)
    else:
        version = _coerce_version(candidates)
        if version:
            values.append(version)

    unique = sorted(set(values), key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x))
    return unique

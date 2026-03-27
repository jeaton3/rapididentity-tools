import os

from examples.get_actions import split_action_defs


XML_TEMPLATE = """<?xml version='1.0' encoding='UTF-8'?>
<actionDefs xmlns=\"urn:idauto.net:dss:actiondef\">
  <actionDef name=\"VendorOnly\" modifiedMS=\"{modified_ms}\" />
</actionDefs>
"""


def test_split_action_defs_skips_older_vendor_xml(tmp_path):
    split_action_defs(XML_TEMPLATE.format(modified_ms="200"), str(tmp_path))

    vendor_path = tmp_path / "vendor-xml" / "VendorOnly.xml"
    first_text = vendor_path.read_text(encoding="utf-8")
    assert 'modifiedMS="200"' in first_text

    split_action_defs(XML_TEMPLATE.format(modified_ms="100"), str(tmp_path))

    second_text = vendor_path.read_text(encoding="utf-8")
    assert second_text == first_text
    assert 'modifiedMS="200"' in second_text


def test_split_action_defs_overwrites_newer_vendor_xml(tmp_path):
    split_action_defs(XML_TEMPLATE.format(modified_ms="100"), str(tmp_path))

    vendor_path = tmp_path / "vendor-xml" / "VendorOnly.xml"
    assert 'modifiedMS="100"' in vendor_path.read_text(encoding="utf-8")

    split_action_defs(XML_TEMPLATE.format(modified_ms="300"), str(tmp_path))

    updated_text = vendor_path.read_text(encoding="utf-8")
    assert 'modifiedMS="300"' in updated_text

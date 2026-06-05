import os

import examples.get_actions as get_actions_module
from examples.get_actions import split_action_defs


XML_TEMPLATE = """<?xml version='1.0' encoding='UTF-8'?>
<actionDefs xmlns=\"urn:idauto.net:dss:actiondef\">
  <actionDef name=\"VendorOnly\" modifiedMS=\"{modified_ms}\" />
</actionDefs>
"""

ACTION_TEMPLATE = """<?xml version='1.0' encoding='UTF-8'?>
<actionDefs xmlns=\"urn:idauto.net:dss:actiondef\">
  <actionDef name=\"ProjectAction\" project=\"{project}\" modifiedMS=\"100\">
    <actions>
      <action name=\"DoThing\" />
    </actions>
  </actionDef>
</actionDefs>
"""

VENDOR_PROJECT_TEMPLATE = """<?xml version='1.0' encoding='UTF-8'?>
<actionDefs xmlns=\"urn:idauto.net:dss:actiondef\">
  <actionDef name=\"VendorOnly\" project=\"{project}\" modifiedMS=\"200\" />
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


def test_split_action_defs_writes_project_scoped_xml_and_js(tmp_path, monkeypatch):
    monkeypatch.setattr(get_actions_module, "actiondef_element_to_script", lambda _ad: "// generated\n")

    split_action_defs(ACTION_TEMPLATE.format(project="Project A"), str(tmp_path))

    xml_path = tmp_path / "xml" / "Project_A" / "ProjectAction.xml"
    js_path = tmp_path / "js" / "Project_A" / "ProjectAction.js"
    root_xml_path = tmp_path / "xml" / "ProjectAction.xml"
    root_js_path = tmp_path / "js" / "ProjectAction.js"

    assert xml_path.exists()
    assert js_path.exists()
    assert not root_xml_path.exists()
    assert not root_js_path.exists()


def test_split_action_defs_writes_project_scoped_vendor_xml(tmp_path):
    split_action_defs(VENDOR_PROJECT_TEMPLATE.format(project="Vendor Project"), str(tmp_path))

    vendor_path = tmp_path / "vendor-xml" / "Vendor_Project" / "VendorOnly.xml"
    root_vendor_path = tmp_path / "vendor-xml" / "VendorOnly.xml"

    assert vendor_path.exists()
    assert not root_vendor_path.exists()

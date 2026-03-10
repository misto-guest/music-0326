#!/usr/bin/env python3
"""
UI Helpers - Shared utilities for UI analysis
Used for debugging and finding selectors
"""

import subprocess
import xml.etree.ElementTree as ET
from typing import List, Dict


def dump_ui(device_id: str, output_path: str = None) -> str:
    """Dump UI hierarchy from device."""
    if output_path is None:
        output_path = "/sdcard/ui_dump.xml"
    
    # Dump UI
    subprocess.run([
        "adb", "-s", device_id, "shell", 
        "uiautomator", "dump", output_path
    ], capture_output=True)
    
    # Pull to local
    local_path = f"ui_dump_{device_id}.xml"
    subprocess.run([
        "adb", "-s", device_id, "pull", 
        output_path, local_path
    ], capture_output=True)
    
    return local_path


def find_elements_by_text(xml_path: str, text: str) -> List[Dict]:
    """Find UI elements containing specific text."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    results = []
    for node in root.iter():
        node_text = node.attrib.get('text', '')
        if text.lower() in node_text.lower():
            results.append({
                'text': node_text,
                'resource-id': node.attrib.get('resource-id', ''),
                'content-desc': node.attrib.get('content-desc', ''),
                'class': node.attrib.get('class', ''),
                'bounds': node.attrib.get('bounds', ''),
            })
    
    return results


def find_elements_by_desc(xml_path: str, desc: str) -> List[Dict]:
    """Find UI elements by content description."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    results = []
    for node in root.iter():
        node_desc = node.attrib.get('content-desc', '')
        if desc.lower() in node_desc.lower():
            results.append({
                'text': node.attrib.get('text', ''),
                'resource-id': node.attrib.get('resource-id', ''),
                'content-desc': node_desc,
                'class': node.attrib.get('class', ''),
                'bounds': node.attrib.get('bounds', ''),
            })
    
    return results


def find_elements_by_resource_id(xml_path: str, res_id: str) -> List[Dict]:
    """Find UI elements by resource ID."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    results = []
    for node in root.iter():
        node_id = node.attrib.get('resource-id', '')
        if res_id in node_id:
            results.append({
                'text': node.attrib.get('text', ''),
                'resource-id': node_id,
                'content-desc': node.attrib.get('content-desc', ''),
                'class': node.attrib.get('class', ''),
                'bounds': node.attrib.get('bounds', ''),
            })
    
    return results


def print_xpath_for_element(element: Dict) -> str:
    """Generate XPath for an element."""
    if element.get('resource-id'):
        return f'//*[@resource-id="{element["resource-id"]}"]'
    elif element.get('content-desc'):
        return f'//*[@content-desc="{element["content-desc"]}"]'
    elif element.get('text'):
        return f'//*[@text="{element["text"]}"]'
    else:
        return f'//*[@class="{element.get("class", "")}"]'


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python ui_helpers.py <device_id> <search_term>")
        print("Example: python ui_helpers.py R5CR11KHW4W shuffle")
        sys.exit(1)
    
    device_id = sys.argv[1]
    search = sys.argv[2]
    
    print(f"Dumping UI from {device_id}...")
    xml_path = dump_ui(device_id)
    
    print(f"\nSearching for '{search}'...")
    
    # Search by text
    by_text = find_elements_by_text(xml_path, search)
    if by_text:
        print(f"\n=== By Text ({len(by_text)} found) ===")
        for elem in by_text:
            print(f"  - text='{elem['text']}' | id='{elem['resource-id']}' | desc='{elem['content-desc']}'")
    
    # Search by content-desc
    by_desc = find_elements_by_desc(xml_path, search)
    if by_desc:
        print(f"\n=== By Content-Desc ({len(by_desc)} found) ===")
        for elem in by_desc:
            print(f"  - desc='{elem['content-desc']}' | id='{elem['resource-id']}' | class='{elem['class']}'")
    
    # Search by resource-id
    by_id = find_elements_by_resource_id(xml_path, search)
    if by_id:
        print(f"\n=== By Resource-ID ({len(by_id)} found) ===")
        for elem in by_id:
            print(f"  - id='{elem['resource-id']}' | desc='{elem['content-desc']}' | class='{elem['class']}'")

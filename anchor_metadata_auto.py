#!/usr/bin/env python3
"""
WhatsHot, Inc. - On-Chain Metadata Anchor Generator (Auto-Path Version)
---------------------------------------------------------------------
Automatically targets your workspace files directory to hash all IP assets 
and anchor state-registered asset DA-000000992.
"""

import os
import json
import hashlib
from datetime import datetime, timezone

def hash_file(filepath, chunk_size=65536):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def generate_ip_manifest(target_dir):
    manifest = {
        "entity": "WhatsHot, Inc.",
        "wyoming_filing_id": "2017-000751490",
        "digital_asset_registration_id": "DA-000000992",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "assets": {}
    }

    print(f"Scanning target directory: {target_dir}")
    if not os.path.exists(target_dir):
        print(f"[ERROR] Directory not found: {target_dir}")
        return None

    for root, dirs, files in os.walk(target_dir):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for file in files:
            path = os.path.join(root, file)
            rel_path = os.path.relpath(path, target_dir)
            try:
                file_hash = hash_file(path)
                manifest["assets"][rel_path] = {
                    "sha256": file_hash,
                    "size_bytes": os.path.getsize(path)
                }
            except Exception as e:
                print(f"Skipping {rel_path}: {e}")

    # Compute master hash of the entire manifest state
    manifest_bytes = json.dumps(manifest, sort_keys=True).encode('utf-8')
    manifest["master_anchor_hash"] = hashlib.sha256(manifest_bytes).hexdigest()
    
    output_filename = f"WhatsHot_IP_Anchor_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2)
        
    print(f"\n[SUCCESS] Master Anchor Created: {output_filename}")
    print(f"Master Anchor Hash: {manifest['master_anchor_hash']}")
    return manifest['master_anchor_hash']

if __name__ == '__main__':
    # Automatically pointing to your active workspace files directory
    target_directory = r"C:\Users\VHome\.copilot\session-state\965f3f55-0aca-46e6-95dd-de8adecd1a21\files"
    generate_ip_manifest(target_directory)

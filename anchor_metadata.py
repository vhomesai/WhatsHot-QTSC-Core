#!/usr/bin/env python3
"""
WhatsHot, Inc. - On-Chain Metadata Anchor Generator (Hardened)
----------------------------------------------------------------
Improvements added:
- argparse CLI (target dir, output path, dry-run, verbose, exclude patterns)
- deterministic manifest ordering (assets sorted, POSIX-style paths)
- robust logging and error handling
- safe output path handling (writes to directory if given, falls back to cwd)
- options to skip hidden files/dirs and pass additional exclude glob patterns
"""

from __future__ import annotations
import argparse
import json
import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

__version__ = "1.0.0"

logger = logging.getLogger("anchor_generator")


def hash_file(filepath: Path, chunk_size: int = 65536) -> str:
    """Compute SHA-256 hash of a file in streaming chunks."""
    hasher = hashlib.sha256()
    with filepath.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def iter_asset_files(target_dir: Path, exclude_globs: Iterable[str] = (), skip_hidden: bool = True) -> Iterable[Path]:
    """Yield files under target_dir, skipping directories and files according to rules.

    Returned paths are regular files only (symbolic links are followed by default through pathlib.rglob).
    """
    # Normalize exclude patterns
    exclude_globs = list(exclude_globs or [])

    for p in target_dir.rglob("**/*"):
        try:
            # skip directories
            if p.is_dir():
                # optionally skip hidden dirs
                if skip_hidden and p.name.startswith('.'):
                    logger.debug("Skipping hidden dir: %s", p)
                    continue
                continue

            # skip hidden files
            if skip_hidden and p.name.startswith('.'):
                logger.debug("Skipping hidden file: %s", p)
                continue

            # apply exclude globs relative to target_dir
            rel = p.relative_to(target_dir)
            rel_posix = rel.as_posix()
            excluded = False
            for pattern in exclude_globs:
                if Path(rel_posix).match(pattern):
                    logger.debug("Excluding by pattern %s: %s", pattern, rel_posix)
                    excluded = True
                    break
            if excluded:
                continue

            # Only include regular files
            if not p.is_file():
                logger.debug("Skipping non-file: %s", p)
                continue

            yield p
        except Exception as e:
            logger.warning("Error while scanning path %s: %s", p, e)
            continue


def generate_ip_manifest(target_dir: Path, exclude_globs: Iterable[str] = (), skip_hidden: bool = True) -> Dict:
    """Generate the manifest dictionary for a given target directory."""
    if not target_dir.exists():
        raise FileNotFoundError(f"Target directory does not exist: {target_dir}")

    manifest = {
        "manifest_version": "1",
        "tool": "WhatsHot IP Anchor Generator",
        "tool_version": __version__,
        "entity": "WhatsHot, Inc.",
        "wyoming_filing_id": "2017-000751490",
        "digital_asset_registration_id": "DA-000000992",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "assets": {}
    }

    logger.info("Scanning directory: %s", target_dir)

    for file_path in iter_asset_files(target_dir, exclude_globs=exclude_globs, skip_hidden=skip_hidden):
        try:
            rel = file_path.relative_to(target_dir).as_posix()  # use POSIX-style separators for portability
            file_hash = hash_file(file_path)
            manifest["assets"][rel] = {
                "sha256": file_hash,
                "size_bytes": file_path.stat().st_size
            }
            logger.debug("Hashed %s -> %s", rel, file_hash)
        except Exception as e:
            logger.warning("Skipping %s: %s", file_path, e)

    # Create a deterministic ordering for assets before computing the master hash
    # Build a new dict with sorted keys so that JSON serialization is stable
    sorted_assets = {k: manifest["assets"][k] for k in sorted(manifest["assets"].keys())}
    manifest["assets"] = sorted_assets

    # Canonical JSON: sort_keys=True and separators to avoid insignificant whitespace
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    manifest["master_anchor_hash"] = hashlib.sha256(manifest_bytes).hexdigest()

    return manifest


def write_manifest(manifest: Dict, output: Path) -> Path:
    """Write manifest to output path. If output is a directory, write file inside it.

    Returns the final file path written.
    """
    if output.exists() and output.is_dir():
        filename = f"WhatsHot_IP_Anchor_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        output_file = output / filename
    else:
        # If output parent doesn't exist, try to create it
        output_file = output
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            # fallback to current working directory
            output_file = Path.cwd() / output_file.name
            logger.warning("Could not create parent directory; falling back to cwd: %s", output_file)

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)

    logger.info("Master Anchor Created: %s", output_file)
    logger.info("Master Anchor Hash: %s", manifest.get("master_anchor_hash"))
    return output_file


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a deterministic manifest of files and a master anchor hash.")
    p.add_argument("--target", "-t", type=Path, default=Path.cwd(), help="Target directory to scan (default: cwd)")
    p.add_argument("--output", "-o", type=Path, default=Path.cwd(), help="Output file path or directory (default: cwd)")
    p.add_argument("--exclude", "-e", action="append", default=[], help="Glob pattern (relative) to exclude; can be passed multiple times")
    p.add_argument("--no-skip-hidden", dest="skip_hidden", action="store_false", help="Do not skip hidden files and directories")
    p.add_argument("--dry-run", action="store_true", help="Do not write manifest to disk; only print summary")
    p.add_argument("--verbose", "-v", action="store_true", help="Enable verbose (debug) logging")
    return p.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s: %(message)s")

    try:
        manifest = generate_ip_manifest(args.target, exclude_globs=args.exclude, skip_hidden=args.skip_hidden)
        if args.dry_run:
            logger.info("Dry run: manifest would contain %d assets", len(manifest.get("assets", {})))
            # Print short summary
            print(json.dumps({
                "assets_count": len(manifest.get("assets", {})),
                "master_anchor_hash": manifest.get("master_anchor_hash")
            }, indent=2))
            return 0

        out_path = write_manifest(manifest, args.output)
        print(f"[SUCCESS] Wrote manifest to: {out_path}")
        print(f"Master Anchor Hash: {manifest.get('master_anchor_hash')}")
        return 0
    except FileNotFoundError as e:
        logger.error(str(e))
        return 2
    except Exception as e:
        logger.exception("Unhandled error: %s", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

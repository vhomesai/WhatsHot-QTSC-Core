# WhatsHot QTSC Core

Repository for WhatsHot, Inc.'s On-Chain Metadata Anchor Generator and test harness.

This project provides a deterministic file-hashing manifest generator suitable for creating an on-chain anchor for intellectual property assets (Digital Asset Registration: DA-000000992). It includes a hardened CLI script, unit tests, and a GitHub Actions workflow that runs on Windows / Python 3.12.

## Contents

- `anchor_metadata.py` — Hardened manifest generator (CLI)
- `anchor_metadata_auto.py` — earlier auto-path convenience script
- `test_anchor_metadata.py`, `test_anchor_metadata_extra.py` — unit tests
- `.github/workflows/python-tests.yml` — GitHub Actions workflow to run tests
- `push_with_gh.ps1` / `push_with_gh.sh` — helper scripts to create remote and push using GitHub CLI

## Quickstart

Prerequisites:
- Python 3.8+ (3.12 recommended)
- Git (for local version control)
- GitHub CLI (`gh`) if you want to create/push a remote repository with the helper scripts

Install dev dependencies (if any future requirements are added):

```powershell
python -m pip install --upgrade pip
# add project-specific deps here if needed
```

Run the manifest generator (example):

```powershell
python anchor_metadata.py --target "C:\path\to\ip_assets" --output "C:\path\to\output_dir" --verbose
```

Dry run (do not write manifest):

```powershell
python anchor_metadata.py --target . --dry-run --verbose
```

## Telemetry Gateway

A FastAPI-based telemetry gateway is provided in `app.py` to support secure enterprise audit requests.

Run the gateway locally:

```powershell
python -m pip install -r requirements.txt
$env:WHOT_ENTERPRISE_API_KEYS = "replace-with-a-strong-api-key:your-client-name"
uvicorn app:app --host 0.0.0.0 --port 8000
```

Example request:

```powershell
curl -X POST "http://127.0.0.1:8000/v1/audit/ternary-check" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: replace-with-a-strong-api-key" \
  -d '{"asset_id":"DA-000000992","metadata":{"customer":"AcmeCorp"}}'
```

## Software Licensing Agreement

The repository includes an enterprise SLA draft: `ENTERPRISE_SLA.md`.

## CI

The repository includes a GitHub Actions workflow (.github/workflows/python-tests.yml) that runs the unit test suite on push and pull request events using Windows runners and Python 3.12.

A second workflow (.github/workflows/deploy.yml) is configured to run on pushes to `main`, execute the same test suite, and deploy the application to a remote host via SSH when deployment secrets are configured. Add `WHOT_ENTERPRISE_API_KEYS` as a repository secret using `api-key:client-name` entries separated by commas.

## Adding codeowners / branch protection

A `CODEOWNERS` file is provided to nominate default reviewers for changes in specified paths. Update the handles to match your organization/team names.

To protect main and require CI checks, enable branch protection in the repository settings and require the `Python Tests` action to pass.

## Contributing

- Fork and create a branch for changes
- Add unit tests for new behaviors
- Open a pull request and request review from the appropriate team

## Security

Do NOT commit generated manifests (WhatsHot_IP_Anchor_*.json) — these are included in `.gitignore` by default. If you need to publish a manifest to an immutable store, consider signing it and storing only the signed hash on-chain.

## License

Add your project license here (e.g., MIT, Apache-2.0) — replace this placeholder with the actual license text or file.

## Published

Published https://github.com/vhomesai/WhatsHot-QTSC-Core with `main` tracking `origin/main`.

`CODEOWNERS` now assigns project paths to `@vhomesai`; unrelated home-directory files were not included.

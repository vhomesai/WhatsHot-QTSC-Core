# PowerShell script to initialize a local git repository and commit the new files.
# Run this in a PowerShell session where Git is installed and available on PATH.

Set-Location -Path 'C:\Users\VHome'
# Initialize repository and ensure main branch
git init
# Use branch rename to main (works with older/newer git)
git branch -M main
# Configure a local user identity for this repository
git config user.name "WhatsHot CI Bot"
git config user.email "noreply@whatshot.inc"
# Stage files (add all changes / new files)
git add -A
# Commit with Co-authored-by trailer
git commit -m "feat: Add CI workflow and extended test suite for WhatsHot IP metadata anchoring" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

Write-Output "Local git repo initialized and committed. Run 'git status' or 'git log -n 5' to inspect."
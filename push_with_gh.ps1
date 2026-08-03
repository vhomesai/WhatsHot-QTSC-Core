<#
PowerShell helper to create a GitHub repository using GitHub CLI (gh), commit local files,
and push the current repository to the new remote.

Usage (interactive):
  Open PowerShell as your user and run:
    C:\Users\VHome\push_with_gh.ps1

Or pass parameters:
  C:\Users\VHome\push_with_gh.ps1 -RepoName "WhatsHot-QTSC-Core" -Owner "YourOrg" -Visibility public

Requirements:
- Git must be installed and available on PATH
- GitHub CLI (gh) must be installed and available on PATH
- You must be authenticated with gh (run `gh auth login` if prompted)
#>
[CmdletBinding()]
param(
    [string]$RepoName = "",
    [string]$Owner = "",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public"
)

try {
    Set-Location -Path 'C:\Users\VHome'
} catch {
    Write-Error "Failed to change to C:\Users\VHome: $_"
    exit 2
}

# Create README and .gitignore if they don't exist
if (-not (Test-Path README.md)) {
    '# WhatsHot QTSC Core' | Out-File -Encoding utf8 README.md
}
if (-not (Test-Path .gitignore)) {
    "__pycache__/`nWhatsHot_IP_Anchor_*.json" | Out-File -Encoding utf8 .gitignore
}

# Initialize and commit only the project files. This avoids accidentally
# publishing unrelated files when the project is stored in a user profile.
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git not found: install Git and ensure it is available on PATH."
    exit 2
}

git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to initialize the local Git repository."
        exit 2
    }
}

git branch -M main
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to set the branch name to main."
    exit 2
}

$projectPaths = @(
    'README.md',
    'LICENSE',
    '.gitignore',
    '.github',
    'anchor_metadata.py',
    'anchor_metadata_auto.py',
    'init_git_and_commit.ps1',
    'push_with_gh.ps1',
    'push_with_gh.sh',
    'test_anchor_metadata.py',
    'test_anchor_metadata_extra.py'
) | Where-Object { Test-Path $_ }

git add -- $projectPaths
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to stage project files."
    exit 2
}

git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m "feat: Initialize WhatsHot, Inc. metadata anchoring and CI test suite" -m "Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to commit staged project files."
        exit 2
    }
    Write-Output "Committed project files."
} else {
    Write-Output "No staged project changes to commit."
}

# Check for gh (GitHub CLI)
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI 'gh' not found in PATH. Install gh and authenticate (gh auth login) before running this script."
    exit 3
}

# Ensure authentication (will return non-zero if not authenticated)
$authCheck = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Output "Not authenticated with gh. Running 'gh auth login' now..."
    gh auth login
    if ($LASTEXITCODE -ne 0) {
        Write-Error "gh auth login failed or was not completed. Aborting."
        exit 4
    }
}

# Prompt for repo name if not provided
if ([string]::IsNullOrWhiteSpace($RepoName)) {
    $RepoName = Read-Host "Enter repository name (example: WhatsHot-QTSC-Core)"
}
if ([string]::IsNullOrWhiteSpace($RepoName)) {
    Write-Error "Repository name is required."
    exit 5
}

# Optionally prompt for owner/org
if ([string]::IsNullOrWhiteSpace($Owner)) {
    $inputOwner = Read-Host "Enter GitHub owner (user or org). Leave blank to create under your account"
    if (-not [string]::IsNullOrWhiteSpace($inputOwner)) { $Owner = $inputOwner }
}

if ($Owner) { $full = "$Owner/$RepoName" } else { $full = $RepoName }

Write-Output "Creating repository: $full (visibility: $Visibility)"

# Create using gh and push
if ($Visibility -eq 'public') {
    gh repo create "$full" --public --source=. --remote=origin --push
} else {
    gh repo create "$full" --private --source=. --remote=origin --push
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to create or push repository via gh. Review the output above for details."
    exit 6
}

Write-Output "Repository created and pushed. Open: https://github.com/$full"
exit 0

#!/bin/bash
# Setup script to configure git hooks

echo "Setting up git hooks..."

# Configure git to use .githooks directory
git config core.hooksPath .githooks

# Make hooks executable
chmod +x .githooks/pre-commit

# Set executable bit for backup script in git index
git add --chmod=+x nightly_backup.sh
git add --chmod=+x setup-git-hooks.sh

echo "Git hooks configured successfully!"
echo "The pre-commit hook will:"
echo "  - Ensure nightly_backup.sh has executable permissions"
echo "  - Check for accidentally committed secrets"
echo ""
echo "To install hooks, run: git config core.hooksPath .githooks"
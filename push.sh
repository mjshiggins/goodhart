#!/usr/bin/env bash
set -euo pipefail

remote_url=$(git remote get-url origin)

echo "This will FORCE PUSH 'main' to: $remote_url"
echo "The remote's existing history will be overwritten."
read -r -p "Continue? (y/n): " answer
if [ "$answer" != "y" ]; then
    echo "Aborted."
    exit 1
fi

git branch -M main
git push --force -u origin main

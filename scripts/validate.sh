#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

scripts=(
  odoo_install.sh
  odoo_install_debian.sh
)

echo "Running bash syntax checks..."
for script in "${scripts[@]}"; do
  bash -n "$script"
done

if command -v shellcheck >/dev/null 2>&1; then
  echo "Running ShellCheck..."
  shellcheck -S warning "${scripts[@]}"
else
  echo "ShellCheck is not installed; skipping ShellCheck." >&2
fi

if command -v python3 >/dev/null 2>&1 && [ -d tests ]; then
  echo "Running Python feature tests..."
  python3 -m unittest discover -s tests -p 'test_*.py'
fi

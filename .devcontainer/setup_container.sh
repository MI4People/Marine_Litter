#!/bin/bash
set -eou pipefail

containerWorkspaceFolder=$1

sudo mkdir -p /home/ubuntu/.cache || true
sudo chown -R ubuntu:ubuntu /home/ubuntu/.cache
sudo mkdir -p ${containerWorkspaceFolder}/.venv || true
sudo chown -R ubuntu:ubuntu ${containerWorkspaceFolder}/.venv

# gdal is installed into the venv (built against NumPy 2), so the venv must NOT see the system site packages,
# whose python3-gdal is built against NumPy 1.x. The persisted venv volume may still be an old venv created
# with --system-site-packages; recreate it in that case.
if grep -qs "include-system-site-packages = true" .venv/pyvenv.cfg; then
    uv venv --clear
else
    uv venv --allow-existing
fi

# Globally install standard tooling
uv tool install ruff
uv tool install ty
uv tool install pre-commit
uv tool update-shell

echo "source /workspaces/Marine_Litter/.venv/bin/activate" >> ~/.bashrc

# as the updated shell is only available in new shells, we need to install pre-commit hooks with the absolute path to the pre-commit binary
$HOME/.local/bin/pre-commit install

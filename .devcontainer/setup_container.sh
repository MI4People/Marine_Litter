#!/bin/bash
set -eou pipefail

containerWorkspaceFolder=$1

sudo mkdir -p /home/ubuntu/.cache || true
sudo chown -R ubuntu:ubuntu /home/ubuntu/.cache
sudo mkdir -p ${containerWorkspaceFolder}/.venv || true
sudo chown -R ubuntu:ubuntu ${containerWorkspaceFolder}/.venv

# The image contains the gdal libs in the system site packages, so we need to use the system site packages in the uv venv
uv venv --system-site-packages --allow-existing

# Globally install standard tooling
uv tool install ruff
uv tool install ty
uv tool install pre-commit
uv tool update-shell

echo "source /workspaces/Marine_Litter/.venv/bin/activate" >> ~/.bashrc

# as the updated shell is only available in new shells, we need to install pre-commit hooks with the absolute path to the pre-commit binary
$HOME/.local/bin/pre-commit install

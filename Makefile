SHELL := bash

.PHONY: help bootstrap bootstrap-windows config build up down logs token badge-preview remote-methodology remote-recon remote-tool-inventory

help:
	@echo "Available targets:"
	@echo "  bootstrap          Run the Bash bootstrap checks"
	@echo "  bootstrap-windows  Run the PowerShell bootstrap checks"
	@echo "  config             Validate docker compose configuration"
	@echo "  build              Build all lab services"
	@echo "  up                 Start the lab with fresh builds"
	@echo "  down               Stop the lab and remove volumes"
	@echo "  logs               Follow docker compose logs"
	@echo "  token              Generate a forged admin JWT for the lab"
	@echo "  badge-preview      Generate a local preview completion badge"
	@echo "  remote-methodology Run the remote methodology helper"
	@echo "  remote-recon       Run the remote recon helper"
	@echo "  remote-tool-inventory Run the remote tool inventory helper"

bootstrap:
	@bash scripts/setup/bootstrap.sh

bootstrap-windows:
	@powershell -ExecutionPolicy Bypass -File scripts/setup/bootstrap.ps1

config:
	@docker compose config

build:
	@docker compose build

up:
	@docker compose up --build

down:
	@docker compose down -v

logs:
	@docker compose logs -f

token:
	@python tools/forge_admin_jwt.py || python3 tools/forge_admin_jwt.py

badge-preview:
	@python tools/generate_completion_assets.py --recipient-name "Demo Researcher" --github-username demo --track "Full Lab Completion" --output-root reports/preview-awards || python3 tools/generate_completion_assets.py --recipient-name "Demo Researcher" --github-username demo --track "Full Lab Completion" --output-root reports/preview-awards

remote-methodology:
	@bash scripts/remote/remote_methodology_check.sh

remote-recon:
	@bash scripts/remote/remote_recon_scan.sh

remote-tool-inventory:
	@bash scripts/remote/remote_tool_inventory.sh

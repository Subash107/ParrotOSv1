SHELL := bash

.PHONY: help bootstrap bootstrap-windows config config-remediated build build-remediated up up-remediated down logs token badge-preview scenario scenario-remediated compare-modes remote-methodology remote-recon remote-tool-inventory

help:
	@echo "Available targets:"
	@echo "  bootstrap          Run the Bash bootstrap checks"
	@echo "  bootstrap-windows  Run the PowerShell bootstrap checks"
	@echo "  config             Validate docker compose configuration"
	@echo "  config-remediated  Validate the remediated compose configuration"
	@echo "  build              Build all lab services"
	@echo "  build-remediated   Build the remediated lab stack"
	@echo "  up                 Start the lab with fresh builds"
	@echo "  up-remediated      Start the remediated lab stack"
	@echo "  down               Stop the lab and remove volumes"
	@echo "  logs               Follow docker compose logs"
	@echo "  token              Generate a forged admin JWT for the lab"
	@echo "  badge-preview      Generate a local preview completion badge"
	@echo "  scenario           Capture a shared scenario run into reports/manual-scenario"
	@echo "  scenario-remediated Capture a remediated scenario run into reports/remediated-scenario"
	@echo "  compare-modes      Generate a side-by-side vulnerable vs remediated dashboard"
	@echo "  remote-methodology Run the remote methodology helper"
	@echo "  remote-recon       Run the remote recon helper"
	@echo "  remote-tool-inventory Run the remote tool inventory helper"

bootstrap:
	@bash scripts/setup/bootstrap.sh

bootstrap-windows:
	@powershell -ExecutionPolicy Bypass -File scripts/setup/bootstrap.ps1

config:
	@docker compose config

config-remediated:
	@docker compose -f docker-compose.yml -f docker-compose.remediated.yml config

build:
	@docker compose build

build-remediated:
	@docker compose -f docker-compose.yml -f docker-compose.remediated.yml build

up:
	@docker compose up --build

up-remediated:
	@docker compose -f docker-compose.yml -f docker-compose.remediated.yml up --build

down:
	@docker compose down -v

logs:
	@docker compose logs -f

token:
	@python tools/forge_admin_jwt.py || python3 tools/forge_admin_jwt.py

badge-preview:
	@python tools/generate_completion_assets.py --recipient-name "Demo Researcher" --github-username demo --track "Full Lab Completion" --output-root reports/preview-awards || python3 tools/generate_completion_assets.py --recipient-name "Demo Researcher" --github-username demo --track "Full Lab Completion" --output-root reports/preview-awards

scenario:
	@python tools/run_lab_scenario.py --report-root reports/manual-scenario --profile vulnerable --capture-source live --compose-file docker-compose.yml || python3 tools/run_lab_scenario.py --report-root reports/manual-scenario --profile vulnerable --capture-source live --compose-file docker-compose.yml

scenario-remediated:
	@python tools/run_lab_scenario.py --report-root reports/remediated-scenario --profile remediated --capture-source live --compose-file docker-compose.yml || python3 tools/run_lab_scenario.py --report-root reports/remediated-scenario --profile remediated --capture-source live --compose-file docker-compose.yml

compare-modes:
	@python tools/generate_mode_comparison_dashboard.py --output-root reports/mode-comparison || python3 tools/generate_mode_comparison_dashboard.py --output-root reports/mode-comparison

remote-methodology:
	@bash scripts/remote/remote_methodology_check.sh

remote-recon:
	@bash scripts/remote/remote_recon_scan.sh

remote-tool-inventory:
	@bash scripts/remote/remote_tool_inventory.sh

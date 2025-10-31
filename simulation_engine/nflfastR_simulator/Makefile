# Makefile - One-Command Verification
#
# Usage:
#   make clean all          # Build container, install deps
#   make backtest YEAR=2023 # Run dev backtest
#   make holdout YEAR=2024  # Run holdout backtest
#   make report             # Render HTML summary
#   make verify             # Run all verification checks

.PHONY: clean all backtest holdout report verify test golden

# Configuration
PYTHON := python3
ARTIFACTS_DIR := artifacts
TIMESTAMP := $(shell date +%Y%m%d_%H%M%S)
RUN_DIR := $(ARTIFACTS_DIR)/$(TIMESTAMP)

# Git SHA for reproducibility
GIT_SHA := $(shell git rev-parse HEAD)
GIT_DIRTY := $(shell git diff-index --quiet HEAD -- || echo "-dirty")

# Default year for backtest
YEAR ?= 2023

#############################################################################
# Setup
#############################################################################

clean:
	@echo "🧹 Cleaning artifacts..."
	rm -rf $(ARTIFACTS_DIR)/temp
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	@echo "✅ Clean complete"

all: clean
	@echo "🔧 Installing dependencies..."
	$(PYTHON) -m pip install -q -r requirements.txt
	@echo "✅ Setup complete"

#############################################################################
# Backtesting
#############################################################################

backtest:
	@echo "=================================================="
	@echo "BACKTEST: $(YEAR)"
	@echo "Git SHA: $(GIT_SHA)$(GIT_DIRTY)"
	@echo "Timestamp: $(TIMESTAMP)"
	@echo "=================================================="
	@mkdir -p $(RUN_DIR)
	@echo "Running backtest..."
	$(PYTHON) scripts/run_backtest.py \
		--year $(YEAR) \
		--output $(RUN_DIR) \
		--seed 42 \
		--git-sha $(GIT_SHA)$(GIT_DIRTY)
	@echo "✅ Backtest complete: $(RUN_DIR)"

holdout:
	@echo "=================================================="
	@echo "HOLDOUT TEST: $(YEAR)"
	@echo "Git SHA: $(GIT_SHA)$(GIT_DIRTY)"
	@echo "Timestamp: $(TIMESTAMP)"
	@echo "=================================================="
	@mkdir -p $(RUN_DIR)
	@echo "Running holdout test..."
	$(PYTHON) scripts/run_backtest.py \
		--year $(YEAR) \
		--output $(RUN_DIR) \
		--seed 42 \
		--git-sha $(GIT_SHA)$(GIT_DIRTY) \
		--holdout
	@echo "✅ Holdout complete: $(RUN_DIR)"

#############################################################################
# Reporting
#############################################################################

report:
	@echo "📊 Generating report..."
	$(PYTHON) scripts/generate_report.py \
		--input $(RUN_DIR) \
		--output $(RUN_DIR)/summary.html
	@echo "✅ Report generated: $(RUN_DIR)/summary.html"
	@echo ""
	@echo "View report:"
	@echo "  open $(RUN_DIR)/summary.html"

#############################################################################
# Verification Checks
#############################################################################

verify: test golden calibration rollforward
	@echo "✅ All verification checks passed"

test:
	@echo "🧪 Running unit tests..."
	$(PYTHON) -m pytest tests/ \
		--cov=simulator \
		--cov-report=term-missing \
		--cov-fail-under=90
	@echo "✅ Unit tests passed"

golden:
	@echo "🏆 Running golden tests..."
	$(PYTHON) tests/test_golden.py
	@echo "✅ Golden tests passed"

calibration:
	@echo "📏 Running calibration checks..."
	$(PYTHON) scripts/check_calibration.py
	@echo "✅ Calibration checks passed"

rollforward:
	@echo "🔒 Running roll-forward audit..."
	$(PYTHON) scripts/audit_rollforward.py
	@echo "✅ Roll-forward audit passed"

#############################################################################
# Help
#############################################################################

help:
	@echo "Available targets:"
	@echo "  make clean          - Clean artifacts"
	@echo "  make all            - Install dependencies"
	@echo "  make backtest       - Run dev backtest (YEAR=2023)"
	@echo "  make holdout        - Run holdout test (YEAR=2024)"
	@echo "  make report         - Generate HTML report"
	@echo "  make verify         - Run all verification checks"
	@echo "  make test           - Run unit tests"
	@echo "  make golden         - Run golden tests"
	@echo "  make calibration    - Check calibration metrics"
	@echo "  make rollforward    - Audit roll-forward discipline"
	@echo ""
	@echo "Example workflow:"
	@echo "  make clean all"
	@echo "  make backtest YEAR=2023"
	@echo "  make report"
	@echo "  make verify"


.PHONY: help install run web test clean

help:
	@echo "Available commands:"
	@echo "  make install   Install all dependencies (API + dev)"
	@echo "  make run       Start the local API server"
	@echo "  make web       Serve the web UI at http://127.0.0.1:8788"
	@echo "  make test      Run all 42 pytest tests"
	@echo "  make clean     Remove .venv and __pycache__"

install:
	python3.11 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements-dev.txt

run:
	deploy/scripts/run_api.sh

web:
	python3 -m http.server 8788 --directory apps/web

test:
	.venv/bin/pytest

clean:
	rm -rf .venv
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

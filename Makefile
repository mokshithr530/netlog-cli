.PHONY: help install dev test lint format run docker-build docker-run pkg-arch clean

help:
	@echo "netlog-cli build and development commands:"
	@echo "  make install       Install netlog-cli into active Python environment"
	@echo "  make dev           Install development dependencies (pytest, build)"
	@echo "  make test          Run pytest unit test suite"
	@echo "  make run           Launch netlog-cli dashboard locally"
	@echo "  make docker-build  Build local Docker container image"
	@echo "  make docker-run    Run netlog-cli inside Docker with host networking"
	@echo "  make pkg-arch      Build Arch Linux package via makepkg"
	@echo "  make clean         Remove build artifacts and cache files"

install:
	pip install -e .

dev:
	pip install -e .[dev]

test:
	pytest -v

run:
	netlog

docker-build:
	docker build -t mokshithr530/netlog-cli:latest .

docker-run:
	docker run --rm -it --net=host mokshithr530/netlog-cli:latest

pkg-arch:
	cd packaging && makepkg -f

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +

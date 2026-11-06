.PHONY: install frontend-install frontend-build run run-lan pair test lint clean

install:
	python3 -m pip install -r requirements.txt

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build

pair:
	python3 -m app.cli pair

run:
	python3 -m app.cli serve

run-lan:
	python3 -m app.cli serve --lan

test:
	python3 -m pytest

lint:
	python3 -m compileall -q app scripts tests

clean:
	rm -rf frontend/dist .pytest_cache

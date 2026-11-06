.PHONY: install run test lint

install:
	python3 -m pip install -r requirements.txt

run:
	uvicorn app.main:app --host 127.0.0.1 --port 8000

test:
	python3 -m pytest

lint:
	python3 -m compileall -q app scripts tests

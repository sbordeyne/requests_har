all: lint typecheck formatcheck isortcheck test

lint:
	poetry run pylint requests_har

typecheck:
	poetry run mypy requests_har

formatcheck:
	poetry run black --check requests_har

isortcheck:
	poetry run isort --check-only requests_har

format:
	poetry run isort requests_har
	poetry run black requests_har

test:
	poetry run pytest

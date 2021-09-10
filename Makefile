clean_logs:
	rm -rf logs

clean:
	python -m src.clean_all_parquet_files

requirements:
	rm -f requirements.txt
	pip-compile requirements.in \
		--output-file requirements.txt \
		--no-header \
		--no-emit-index-url \
		--verbose

dev-requirements:
	rm -f dev-requirements.txt
	pip-compile requirements.in dev-requirements.in \
		--output-file dev-requirements.txt \
		--no-header \
		--no-emit-index-url \
		--verbose

install:
	pip install -r requirements.txt

dev-install:
	pip install -r dev-requirements.txt

lint:
	flake8
	black --check --diff .
	isort --check --diff .
	python -m mypy --config-file setup.cfg --pretty .

format:
	isort .
	black .

test:
	pytest tests -vv

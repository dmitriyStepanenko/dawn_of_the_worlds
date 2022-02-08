.PHONY: test check_typing
check_typing:
	mypy --config-file pyproject.toml app

test:
	PYTHONPATH=. pytest
.PHONY: start demo check test

# Khởi động toàn bộ Backend + Frontend chỉ bằng 1 lệnh
start:
	./start.sh

demo:
	./start.sh

# Kiểm tra chất lượng mã nguồn (linter + unit test)
check:
	.venv/bin/ruff check mentormind/ tests/
	PYTHONPATH=. .venv/bin/pytest tests/

test:
	PYTHONPATH=. .venv/bin/pytest tests/ -v

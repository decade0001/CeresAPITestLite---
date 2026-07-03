FROM python:3.11-slim

WORKDIR /app
COPY . /app

CMD ["python", "run_tests.py", "--case", "cases/demo_cases.json", "--report-dir", "reports"]


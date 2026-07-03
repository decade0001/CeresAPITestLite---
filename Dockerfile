FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "run_tests.py", "--case", "cases/demo_cases.json", "--report-dir", "reports"]

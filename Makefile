install: ; pip install -r requirements.txt
run:     ; python -m pipelines.ingest && python -m pipelines.transform && python -m pipelines.quality && python -m pipelines.serve
up:      ; docker compose up -d   # Airflow UI -> http://localhost:8080
lint:    ; ruff check .

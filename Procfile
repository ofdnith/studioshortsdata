web: uvicorn app.main:app --reload --reload-dir app --reload-include '*.html' --reload-include '*.css' --reload-include '*.js' --port 8000
worker: watchfiles --filter python "python -m app.worker" app

import logging

from cache_service.api import create_app

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")

# Entry point for `uvicorn cache_service.main:app`.
app = create_app()

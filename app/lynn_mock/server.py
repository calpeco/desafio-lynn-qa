"""Sobe a API mock + frontend como servidor HTTP standalone.

Uso (na raiz do repositório): python app   → http://127.0.0.1:8080   (porta via LYNN_PORT)
"""
import logging
import os

from werkzeug.serving import run_simple

from .api.app import create_app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run_simple("127.0.0.1", int(os.getenv("LYNN_PORT", "8080")), create_app(), threaded=True)


if __name__ == "__main__":
    main()

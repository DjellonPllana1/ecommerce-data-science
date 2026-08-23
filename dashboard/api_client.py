import os
import sys
from functools import lru_cache
from pathlib import Path

import httpx
import requests

BASE_URL = os.getenv("API_BASE_URL")


class APIError(RuntimeError):
    pass


def _load_streamlit_secrets():
    """Expose deployment secrets to the API before it creates a DB engine."""
    try:
        import streamlit as st

        for name in ("DATABASE_URL",):
            if name not in os.environ and name in st.secrets:
                os.environ[name] = str(st.secrets[name])
    except (ImportError, FileNotFoundError, KeyError):
        pass


@lru_cache(maxsize=1)
def _embedded_client():
    """Run FastAPI in-process when no separately deployed API is configured."""
    _load_streamlit_secrets()
    project_root = str(Path(__file__).resolve().parents[1])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from fastapi.testclient import TestClient
    from api.main import app

    return TestClient(app)


def request(method, path, **kwargs):
    try:
        if BASE_URL:
            response = requests.request(
                method, f"{BASE_URL.rstrip('/')}{path}", timeout=30, **kwargs
            )
        else:
            response = _embedded_client().request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, httpx.HTTPError, RuntimeError) as exc:
        raise APIError(f"Application service unavailable: {exc}") from exc


def get(path,**params): return request('GET',path,params=params)
def post(path,payload): return request('POST',path,json=payload)

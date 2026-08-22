from pathlib import Path
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseModel):
    title: str = "E-Commerce Intelligence API"
    version: str = "1.0.0"
    planning_interval_note: str = "Empirical planning interval; not a guaranteed confidence interval."

settings = Settings()

import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "inibsa")
DB_USER = os.getenv("DB_USER", "inibsa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "inibsa")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

CSV_COMMODITIES = os.getenv("CSV_COMMODITIES", "/app/data/master_commodities.csv")
CSV_TECHNICALS = os.getenv("CSV_TECHNICALS", "/app/data/master_technicals.csv")

MADRID_TZ = ZoneInfo("Europe/Madrid")

def today_str() -> str:
    return datetime.now(MADRID_TZ).strftime("%Y-%m-%d")

K_ANTICIPACIO_DIES = 7
PROB_ANTICIPACIO = 0.6
PROB_REACTIVA = 0.8

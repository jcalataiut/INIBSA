import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "inibsa")
DB_USER = os.getenv("DB_USER", "inibsa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "inibsa")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

CSV_COMMODITIES = os.getenv("CSV_COMMODITIES", os.path.join(DATA_DIR, "master_commodities.csv"))
CSV_TECHNICALS = os.getenv("CSV_TECHNICALS", os.path.join(DATA_DIR, "master_technicals.csv"))
POSTAL_GEO_CSV = os.getenv("POSTAL_GEO_CSV", os.path.join(DATA_DIR, "postal_geocodes_es.csv"))

MADRID_TZ = ZoneInfo("Europe/Madrid")

def today_str() -> str:
    return datetime.now(MADRID_TZ).strftime("%Y-%m-%d")

EWM_HALF_LIFE = 4.0
PROB_ANTICIPACIO = 0.01
MAX_ALERTS = 1000
GEO_MIN_NEIGHBORS = 3
GEO_NEIGHBOR_RADIUS_KM = 75.0
GEO_MIN_SHARE_GAP = 0.20
GEO_MIN_INDIVIDUAL_GAP = 0.12

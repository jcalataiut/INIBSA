import os
from datetime import datetime, timezone, timedelta
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

MADRID_TZ = timezone(timedelta(hours=2))  # CEST (UTC+2)

def today_str() -> str:
    return datetime.now(MADRID_TZ).strftime("%Y-%m-%d")

SHARE_FIDEL_THR = 0.70
SHARE_MARGINAL_THR = 0.20
DIES_FUGAT_THR = 365
DIES_NOU_THR = 90
DIES_HISTORIAL_MIN = 180
RATIO_EN_RISC = 0.75
NUM_INTERVALS_MIN = 3
LLINDAR_GROC_STD = 0.0
LLINDAR_TARONJA_STD = 1.5
LLINDAR_VERMELL_STD = 2.5
FINESTRA_CAPTURA_PCT = 0.10
FINESTRA_CAPTURA_MIN = 3
FINESTRA_CAPTURA_MAX = 14

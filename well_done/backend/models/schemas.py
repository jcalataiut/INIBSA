from pydantic import BaseModel
from typing import Optional

class AlertaOut(BaseModel):
    id_cliente: int
    provincia: str
    familia_potencial: str
    segment: str
    segment_anterior: Optional[str] = None
    tipus_alerta: str
    urgencia: str
    canal: str
    share_12m: float
    share_velocity: Optional[float] = None
    share_alerta: Optional[str] = None
    potencial_anual_eur: float
    euros_12m: float
    gap_eur: float
    dies_sense_compra: int
    num_intervals: int
    cicle_mig_dies: Optional[float] = None
    cicle_std_dies: Optional[float] = None
    dies_retard: int
    z_score: Optional[float] = None
    proxim_pedido_esperat: Optional[str] = None
    dies_stock: Optional[float] = None
    prioritat: float
    motiu: str
    data_alerta: str
    tractada: bool = False

class AlertaTreatedIn(BaseModel):
    id_cliente: int
    familia_potencial: str
    tipus_alerta: str

class AlertaTreatedOut(BaseModel):
    id: int
    client_familia_tipus: str
    id_cliente: int
    familia_potencial: str
    tipus_alerta: str
    treated_date: str

class StatsOut(BaseModel):
    total_alertes: int
    pendents: int
    tractades: int
    gap_total: float
    alta_urgencia: int
    per_segment: dict
    per_tipus: dict

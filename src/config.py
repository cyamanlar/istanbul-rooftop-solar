"""Shared paths and site settings."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATA = str(ROOT / 'data' / 'pvgis')
PHYPHOX = str(ROOT / 'data' / 'phyphox')
OUT = str(ROOT / 'outputs')
FIG = str(ROOT / 'outputs' / 'figures')
LAT, LON = 41.105, 29.025          # İTÜ Ayazağa (Maslak) campus, İstanbul
(ROOT / 'outputs' / 'figures').mkdir(parents=True, exist_ok=True)

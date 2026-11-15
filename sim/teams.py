"""Canonical club names. Every source's spelling maps to one name here; nothing downstream sees a second spelling."""
from __future__ import annotations
import csv, os, re, unicodedata
from functools import lru_cache

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAMS_CSV = os.path.join(ROOT, "data", "teams.csv")


class UnknownTeam(KeyError):
    pass


@lru_cache(maxsize=1)
def load_teams():
    with open(TEAMS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def teams(active_only: bool = True):
    return [r["team"] for r in load_teams() if r["active"] == "1" or not active_only]


def code_of():
    return {r["team"]: r["code"] for r in load_teams()}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    s = re.sub(r"\b(fc|cf|club|deportivo|de|cd)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# normalised spelling -> canonical. football-data, ESPN and Pinnacle spellings; add a line whenever a source shows a new one.
_ALIASES = {
    "america": "América", "atlante": "Atlante", "atlas": "Atlas",
    "atl san luis": "Atlético San Luis", "atletico san luis": "Atlético San Luis", "san luis": "Atlético San Luis",
    "cruz azul": "Cruz Azul", "guadalajara": "Guadalajara", "guadalajara chivas": "Guadalajara", "chivas guadalajara": "Guadalajara", "chivas": "Guadalajara",
    "juarez": "Juárez", "leon": "León", "monterrey": "Monterrey", "necaxa": "Necaxa", "pachuca": "Pachuca", "puebla": "Puebla",
    "pumas": "Pumas", "pumas unam": "Pumas", "unam pumas": "Pumas", "unam": "Pumas",
    "queretaro": "Querétaro", "santos": "Santos Laguna", "santos laguna": "Santos Laguna",
    "tigres": "Tigres", "tigres uanl": "Tigres", "uanl": "Tigres", "tijuana": "Tijuana", "toluca": "Toluca",
    "chiapas": "Chiapas", "dorados sinaloa": "Dorados", "dorados": "Dorados", "leones negros": "Leones Negros", "lobos buap": "Lobos BUAP",
    "mazatlan": "Mazatlán", "monarcas": "Morelia", "morelia": "Morelia", "monarcas morelia": "Morelia", "veracruz": "Veracruz",
}


def canon(name: str) -> str:
    n = _norm(str(name))
    if n in _ALIASES:
        return _ALIASES[n]
    raise UnknownTeam(name)

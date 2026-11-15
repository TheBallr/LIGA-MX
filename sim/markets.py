"""Price every futures market from the season archive."""
from __future__ import annotations
import numpy as np
from .liguilla import STAGE


class Archive:
    def __init__(self, arc: dict):
        self.teams = [str(t) for t in arc["teams"]]; self.idx = {t: i for i, t in enumerate(self.teams)}
        self.points = np.asarray(arc["points"]); self.pos = np.asarray(arc["pos"]); self.stage = np.asarray(arc["stage"])
        self.N = self.points.shape[0]

    def _d(self, v):
        return {t: float(x) for t, x in zip(self.teams, v)}

    def champion(self): return self._d((self.stage == STAGE["champion"]).mean(axis=0))
    def reach_final(self): return self._d((self.stage >= STAGE["final"]).mean(axis=0))
    def reach_sf(self): return self._d((self.stage >= STAGE["sf"]).mean(axis=0))
    def liguilla(self): return self._d((self.stage >= STAGE["qf"]).mean(axis=0))
    def top(self, n): return self._d((self.pos <= n).mean(axis=0))
    def seed_dist(self, upto=8): return {t: [float((self.pos[:, i] == k).mean()) for k in range(1, upto + 1)] for i, t in enumerate(self.teams)}

    def points_summary(self):
        p = self.points.astype(float)
        return {t: {"mean": float(p[:, i].mean()), "p10": float(np.percentile(p[:, i], 10)), "p90": float(np.percentile(p[:, i], 90))} for i, t in enumerate(self.teams)}

    def without(self, team):
        keep = self.stage[:, self.idx[team]] != STAGE["champion"]
        return self._d((self.stage[keep] == STAGE["champion"]).mean(axis=0))


def all_markets(arc: Archive) -> dict:
    return {"champion": arc.champion(), "reach_final": arc.reach_final(), "reach_sf": arc.reach_sf(), "liguilla": arc.liguilla(),
            "seed1": arc.top(1), "top4": arc.top(4), "seeds": arc.seed_dist(), "points": arc.points_summary()}

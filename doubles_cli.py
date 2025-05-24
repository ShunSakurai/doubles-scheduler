#!/usr/bin/env python3
"""
py doubles_cli.py -p 9 -c 2

  ―  ダブルス組み合わせ自動生成 CLI

使い方:
    python doubles_cli.py -p 12 -c 3
        -p / --players : プレーヤー人数 (9〜13 程度)
        -c / --courts  : コート数 (1〜3)

Enter キーを押すたびに次の試合を提示し、
Ctrl-C で終了します。
"""

from collections import defaultdict
from itertools import combinations
from ortools.sat.python import cp_model
import argparse


# ─────────────────────────────────────────────────────────
#  スケジューラ本体
# ─────────────────────────────────────────────────────────
class DoublesScheduler:
    def __init__(self, P: int, C: int):
        if P < 4 * C:
            raise ValueError("人数 P は 4×コート数 C 以上が必要です")
        self.P, self.C = P, C
        self.players = list(range(1, P + 1))
        self.round_no = 0
        self.rest_count = defaultdict(int)
        self.pair_count = defaultdict(int)
        self.opp_count = defaultdict(int)

    # パブリック
    def next_round(self) -> dict:
        if self.round_no == 0:
            sched = self._first_round_fixed()
        else:
            sched = self._solve_round()
        self._update_stats(sched)
        self.round_no += 1
        return sched

    # ── 内部 ──
    def _first_round_fixed(self) -> dict:
        sched = {}
        for c in range(self.C):
            grp = self.players[4 * c : 4 * c + 4]
            if len(grp) == 4:
                pairs = [tuple(sorted(grp[:2])), tuple(sorted(grp[2:]))]
                sched[chr(65 + c)] = pairs
        sched["Rest"] = self.players[4 * self.C :]
        return sched

    def _solve_round(self) -> dict:
        rest_slots = self.P - 4 * self.C
        if rest_slots:
            need_sorted = sorted(self.players, key=lambda p: (self.rest_count[p], p))
            rest_today = set(need_sorted[:rest_slots])
        else:
            rest_today = set()

        active = [p for p in self.players if p not in rest_today]
        n_slots = 2 * self.C

        model = cp_model.CpModel()
        y = {(p, s): model.NewBoolVar(f"y_{p}_{s}") for p in active for s in range(n_slots)}
        for p in active:
            model.Add(sum(y[p, s] for s in range(n_slots)) == 1)
        for s in range(n_slots):
            model.Add(sum(y[p, s] for p in active) == 2)

        pair_vars = {}
        for i, j in combinations(active, 2):
            z_ij_s = []
            for s in range(n_slots):
                z = model.NewBoolVar(f"z_{i}_{j}_{s}")
                z_ij_s.append(z)
                model.Add(z <= y[i, s])
                model.Add(z <= y[j, s])
                model.Add(z >= y[i, s] + y[j, s] - 1)
            pair = model.NewBoolVar(f"pair_{i}_{j}")
            model.Add(pair == sum(z_ij_s))
            pair_vars[(i, j)] = pair

        objective = []
        for (i, j), var in pair_vars.items():
            if self.pair_count[(i, j)] == 0:
                objective.append(var * 10)   # 新ペアを奨励
            else:
                objective.append(var * -1)   # 同ペアは軽い罰則
        model.Maximize(sum(objective))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 2
        solver.parameters.num_search_workers = 8
        solver.Solve(model)

        slot_to_players = defaultdict(list)
        for p in active:
            for s in range(n_slots):
                if solver.BooleanValue(y[p, s]):
                    slot_to_players[s].append(p)

        sched = {}
        for c in range(self.C):
            a, b = slot_to_players[2 * c], slot_to_players[2 * c + 1]
            a.sort(), b.sort()
            sched[chr(65 + c)] = [tuple(a), tuple(b)]
        sched["Rest"] = sorted(rest_today)
        return sched

    def _update_stats(self, sched: dict):
        for p in sched["Rest"]:
            self.rest_count[p] += 1
        courts = [k for k in sched if k != "Rest"]
        for court in courts:
            p1, p2 = sched[court]
            for i, j in combinations(p1, 2):
                self.pair_count[tuple(sorted((i, j)))] += 1
            for i, j in combinations(p2, 2):
                self.pair_count[tuple(sorted((i, j)))] += 1
            for i in p1:
                for j in p2:
                    self.opp_count[tuple(sorted((i, j)))] += 1


# ─────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────
def print_round(schedule: dict, no: int):
    print(f"\n=== Round {no} ===")
    courts = sorted(k for k in schedule if k != "Rest")
    for court in courts:
        (a1, a2), (b1, b2) = schedule[court]
        print(f"Court {court}: {a1}-{a2}  vs  {b1}-{b2}")
    rest = schedule["Rest"]
    if rest:
        print("Rest: " + ", ".join(map(str, rest)))
    print("-" * 32)


def main():
    parser = argparse.ArgumentParser(description="Doubles doubles scheduler (interactive)")
    parser.add_argument("-p", "--players", type=int, required=True, help="number of players (≥ 4×courts)")
    parser.add_argument("-c", "--courts", type=int, required=True, help="number of courts (1–3)")
    args = parser.parse_args()

    scheduler = DoublesScheduler(P=args.players, C=args.courts)
    print("準備完了。Enter で次の試合を生成、Ctrl+C で終了します。")

    try:
        while True:
            input()
            round_sched = scheduler.next_round()
            print_round(round_sched, scheduler.round_no)
    except KeyboardInterrupt:
        print("\nスケジューラを終了しました。お疲れさまでした。")


if __name__ == "__main__":
    main()

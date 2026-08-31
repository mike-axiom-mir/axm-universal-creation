from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.specialist_pool import (
    build_specialist_pool,
    inspect_specialist_fit,
    prepare_tournament,
    rank_tournament,
    record_finalist_vote,
)


class SpecialistTournamentTests(unittest.TestCase):
    def _root(self, parent: Path) -> Path:
        root = parent / "machine"
        registry = root / "reference/AXM_Universal_Creation_Map_v0.1/registry"
        registry.mkdir(parents=True)
        shutil.copy2(
            ROOT / "reference/AXM_Universal_Creation_Map_v0.1/registry/master_registry.json",
            registry / "master_registry.json",
        )
        return root

    @staticmethod
    def _single_criterion():
        return [{"id": "evidence", "weight": 1, "description": "evidence quality"}]

    @staticmethod
    def _judgements(tournament: dict, *, reverse: bool = False) -> dict:
        teams = tournament["team_generation"]["teams"]
        result = {}
        count = len(teams)
        for index, team in enumerate(teams):
            ordinal = count - index if reverse else index + 1
            result[team["team_id"]] = {
                "criteria": {"evidence": {"score": min(100, 10 + ordinal * 10), "evidence": f"fixture evidence {ordinal}"}},
                "summary": f"team fixture {ordinal}",
            }
        return result

    def test_live_machine_routes_specialist_tournament_without_faking_reasoning(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "specialist-tournament",
            "inputs": {
                "operation": "prepare",
                "challenge": "improve an adaptive rendering material system",
                "pool_size": 8,
                "team_size": 3,
                "max_teams": 4,
                "criteria": self._single_criterion(),
            },
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        prepared = result["result"]
        self.assertEqual(prepared["status"], "READY_FOR_PARALLEL_SPECIALIST_CHALLENGE")
        self.assertIn("no specialist reasoning is claimed", prepared["execution_claim"])
        self.assertEqual(prepared["team_generation"]["generated_team_count"], 4)

    def test_pool_profiles_are_detailed_and_need_specific(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            pool = build_specialist_pool(
                root,
                "render a shader material scene with adaptive level of detail",
                pool_size=32,
            )
            self.assertEqual(pool["pool_size"], 32)
            self.assertNotEqual(pool["context_key"], "general-unmatched")
            derived = [row for row in pool["specialists"] if row["kind"] == "need-derived-registry-specialist"]
            self.assertTrue(derived)
            required = {
                "temperament", "core_question", "strength", "blind_spot", "evidence_preference",
                "novelty_bias", "risk_posture", "time_horizon", "scale_preference",
                "disagreement_style", "communication", "challenge_behavior", "synthesis_role",
            }
            self.assertTrue(required.issubset(pool["specialists"][0]))
            self.assertTrue(any("render" in str(row.get("domain", "")).casefold() or "shader" in str(row.get("focus", "")).casefold() for row in derived))

    def test_team_generation_preserves_best_middle_low_mixed_and_many_combinations(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            prepared = prepare_tournament(
                root,
                "design a resilient local visual runtime",
                criteria=self._single_criterion(),
                pool_size=20,
                team_size=4,
                max_teams=64,
                seed="same-seed",
            )
            body = prepared["team_generation"]
            team_types = {row["team_type"] for row in body["teams"]}
            self.assertIn("best-evidence-team", team_types)
            self.assertIn("middle-evidence-team", team_types)
            self.assertIn("lowest-third-challenge-team", team_types)
            self.assertIn("mixed-random-team", team_types)
            self.assertGreater(body["combination_space"], body["generated_team_count"])
            self.assertEqual(body["generated_team_count"], 64)
            again = prepare_tournament(
                root,
                "design a resilient local visual runtime",
                criteria=self._single_criterion(),
                pool_size=20,
                team_size=4,
                max_teams=64,
                seed="same-seed",
            )
            self.assertEqual(body, again["team_generation"])

    def test_partial_judging_cannot_fake_two_finalists(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            tournament = prepare_tournament(
                root,
                "find hidden failure modes",
                criteria=self._single_criterion(),
                pool_size=8,
                team_size=3,
                max_teams=5,
            )
            one_team = tournament["team_generation"]["teams"][0]
            ranking = rank_tournament(tournament, {
                one_team["team_id"]: {
                    "criteria": {"evidence": {"score": 100, "evidence": "one result only"}}
                }
            })
            self.assertEqual(ranking["status"], "PARTIAL_RANKING_NO_FINALIST_VOTE")
            self.assertFalse(ranking["complete_parallel_judging"])
            self.assertEqual(ranking["finalists"], [])

    def test_complete_parallel_field_shows_exactly_two_finalists_before_points(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            tournament = prepare_tournament(
                root,
                "compare several repair strategies",
                criteria=self._single_criterion(),
                pool_size=8,
                team_size=3,
                max_teams=6,
            )
            ranking = rank_tournament(tournament, self._judgements(tournament))
            self.assertEqual(ranking["status"], "AWAITING_FINALIST_VOTE")
            self.assertTrue(ranking["complete_parallel_judging"])
            self.assertEqual(len(ranking["finalists"]), 2)
            self.assertFalse(ranking["points_awarded"])
            self.assertGreaterEqual(ranking["finalists"][0]["score"], ranking["finalists"][1]["score"])

    def test_finalist_vote_adds_exactly_one_point_to_each_winning_member_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            tournament = prepare_tournament(
                root,
                "improve rendering reliability",
                criteria=self._single_criterion(),
                pool_size=8,
                team_size=3,
                max_teams=6,
            )
            ranking = rank_tournament(tournament, self._judgements(tournament))
            winner = ranking["finalists"][0]
            first = record_finalist_vote(root, ranking, winner["team_id"])
            self.assertEqual(first["status"], "FINALIST_VOTE_RECORDED")
            self.assertEqual(first["points_each_winner_member"], 1)
            for member in winner["team"]["members"]:
                self.assertEqual(first["member_updates"][member]["context_points"], 1)
                self.assertEqual(first["member_updates"][member]["global_points"], 1)
            second = record_finalist_vote(root, ranking, winner["team_id"])
            self.assertEqual(second["status"], "VOTE_ALREADY_RECORDED")
            history = inspect_specialist_fit(root)
            self.assertEqual(history["recorded_votes"], 1)

    def test_winning_specialists_rise_for_same_context_but_low_and_mixed_challengers_remain(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            challenge = "improve a local renderer and material pipeline"
            tournament = prepare_tournament(
                root,
                challenge,
                criteria=self._single_criterion(),
                pool_size=12,
                team_size=3,
                max_teams=8,
            )
            ranking = rank_tournament(tournament, self._judgements(tournament, reverse=True))
            winner = ranking["finalists"][0]
            winner_members = set(winner["team"]["members"])
            record_finalist_vote(root, ranking, winner["team_id"])

            next_tournament = prepare_tournament(
                root,
                challenge,
                criteria=self._single_criterion(),
                pool_size=12,
                team_size=3,
                max_teams=8,
            )
            best = next(row for row in next_tournament["team_generation"]["teams"] if row["team_type"] == "best-evidence-team")
            self.assertEqual(set(best["members"]), winner_members)
            types = {row["team_type"] for row in next_tournament["team_generation"]["teams"]}
            self.assertIn("lowest-third-challenge-team", types)
            self.assertIn("mixed-random-team", types)

    def test_context_history_does_not_claim_universal_fit(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            rendering = prepare_tournament(
                root,
                "render adaptive materials and lighting",
                criteria=self._single_criterion(),
                pool_size=32,
                team_size=3,
                max_teams=4,
            )
            ranking = rank_tournament(rendering, self._judgements(rendering))
            record_finalist_vote(root, ranking, ranking["finalists"][0]["team_id"])

            unrelated = build_specialist_pool(root, "design a database transaction log", pool_size=32)
            self.assertNotEqual(unrelated["context_key"], rendering["context_key"])
            self.assertTrue(all(row["fit"]["context_points"] == 0 for row in unrelated["specialists"]))
            self.assertTrue(any(row["fit"]["global_points"] > 0 for row in unrelated["specialists"]))


if __name__ == "__main__":
    unittest.main()

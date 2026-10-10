"""Offline behavioral coverage for optional decision providers and routing."""
from __future__ import annotations

import contextlib
import copy
import importlib
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import router


def score_answer(score=2.4, confidence=0.8):
    probabilities = {str(i): 0.0 for i in range(4)}
    lower = int(score)
    probabilities[str(lower)] = 1.0 - (score - lower)
    if lower < 3:
        probabilities[str(lower + 1)] = score - lower
    return {"type": "score", "score": score, "confidence": confidence,
            "probabilities": probabilities}


def candidates(count=3):
    return [{"id": i + 1, "name": f"skill-{i}", "desc": "React dashboard testing",
             "repo": "example/skills", "url": f"https://example.test/skill-{i}",
             "tier": "community"} for i in range(count)]


def response_for(questions, score=2.4, confidence=0.8):
    return {"answers": {key: score_answer(score, confidence) for key in questions}}


class ScoreValidationTests(unittest.TestCase):
    def test_valid_score_and_boundary_values_are_accepted(self):
        for score in (0, 1, 2.4, 3):
            for confidence in (0, 0.8, 1):
                with self.subTest(score=score, confidence=confidence):
                    self.assertIsNone(router.validate_score(score_answer(score, confidence), 4))

    def test_malformed_containers_are_rejected_without_crashing(self):
        for answer in (None, [], "score", 4, True):
            with self.subTest(answer=answer):
                self.assertIsInstance(router.validate_score(answer, 4), str)
        for probabilities in ([], [0, 0, 0, 1], "probabilities", 4, True, None):
            with self.subTest(probabilities=probabilities):
                answer = {**score_answer(), "probabilities": probabilities}
                self.assertIsInstance(router.validate_score(answer, 4), str)

    def test_non_numeric_boolean_and_nonfinite_values_are_rejected(self):
        for field in ("score", "confidence"):
            for value in (None, True, False, "0.5", "bad", float("nan"),
                          float("inf"), float("-inf")):
                with self.subTest(field=field, value=value):
                    self.assertIsInstance(router.validate_score({**score_answer(), field: value}, 4), str)
        for value in (None, True, False, "0", "bad", float("nan"), float("inf")):
            with self.subTest(probability=value):
                answer = score_answer()
                answer["probabilities"]["0"] = value
                self.assertIsInstance(router.validate_score(answer, 4), str)

    def test_probability_keys_sum_ranges_and_weighted_score_are_enforced(self):
        invalid = [
            {**score_answer(), "type": "choice"},
            {**score_answer(), "score": -1},
            {**score_answer(), "score": 4},
            {**score_answer(), "confidence": 1.1},
            {**score_answer(), "probabilities": {"0": 0.5, "1": 0.5}},
            {**score_answer(), "probabilities": {0: 0, "1": 0, "2": 0.6, "3": 0.4}},
            {**score_answer(), "probabilities": {"0": -0.1, "1": 0, "2": 0.7, "3": 0.4}},
            {**score_answer(), "probabilities": {"0": 0, "1": 0, "2": 0.2, "3": 0.2}},
            {**score_answer(), "score": 1.2},
        ]
        for answer in invalid:
            with self.subTest(answer=answer):
                self.assertIsInstance(router.validate_score(answer, 4), str)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"TYPESAFE_API_KEY": "jev-test-key",
            "PERPLEXITY_API_KEY": "pplx-test-key"}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def test_default_mode_preserves_jev_and_existing_output_fields(self):
        calls = []

        def decide(provider, state, questions, **kwargs):
            calls.append((provider, state, questions, kwargs))
            return response_for(questions)

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates())
        self.assertEqual([call[0] for call in calls], ["jev"])
        self.assertEqual(result["project"], "Build a dashboard")
        self.assertEqual(result["provider"], "jev")
        self.assertEqual(list(result["providers"]), ["jev"])
        self.assertEqual(len(result["ranked"]), 3)
        self.assertEqual(result["rejected"], [])
        self.assertAlmostEqual(result["ranked"][0]["score"], 2.4)
        self.assertAlmostEqual(result["ranked"][0]["confidence"], 0.8)

    def test_perplexity_mode_calls_only_perplexity(self):
        with patch.object(router, "decision_call", side_effect=lambda provider, state, questions, **kw:
                          response_for(questions)) as call:
            result = router.score_candidates("Build a dashboard", candidates(), provider="perplexity")
        self.assertEqual(call.call_args.args[0], "perplexity")
        self.assertEqual(call.call_count, 1)
        self.assertEqual(list(result["providers"]), ["perplexity"])
        self.assertEqual(len(result["ranked"]), 3)

    def test_both_uses_identical_rubric_and_averages_scores_and_distributions(self):
        calls = {}

        def decide(provider, state, questions, **kwargs):
            calls[provider] = (copy.deepcopy(state), copy.deepcopy(questions), kwargs)
            return response_for(questions, 2.8 if provider == "jev" else 1.8,
                                0.9 if provider == "jev" else 0.6)

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(), provider="both",
                                             jev_model="jev-test", perplexity_model="pplx-test")
        self.assertEqual(calls["jev"][:2], calls["perplexity"][:2])
        for question in calls["jev"][1].values():
            self.assertEqual(question["type"], "score")
            self.assertEqual(question["criteria"], router.LEVELS)
        self.assertEqual(calls["jev"][2]["model"], "jev-test")
        self.assertEqual(calls["perplexity"][2]["model"], "pplx-test")
        self.assertEqual(list(result["providers"]), ["jev", "perplexity"])
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["used_providers"], ["jev", "perplexity"])
        self.assertEqual(result["aggregation"], "equal_mean_with_fallback")
        row = result["ranked"][0]
        self.assertEqual(row["aggregation"], "equal_mean")
        self.assertEqual(row["used_providers"], ["jev", "perplexity"])
        self.assertAlmostEqual(row["score"], 2.3)
        self.assertAlmostEqual(row["confidence"], 0.6)
        self.assertEqual(row["confidence_kind"], "minimum_provider_confidence")
        self.assertAlmostEqual(row["score_disagreement"], 1.0)
        self.assertAlmostEqual(row["probabilities"]["1"], 0.1)
        self.assertAlmostEqual(row["probabilities"]["2"], 0.5)
        self.assertAlmostEqual(row["probabilities"]["3"], 0.4)
        self.assertAlmostEqual(row["provider_scores"]["jev"]["score"], 2.8)
        self.assertAlmostEqual(row["provider_scores"]["perplexity"]["confidence"], 0.6)

    def test_both_calls_can_run_concurrently(self):
        barrier = threading.Barrier(2)

        def decide(provider, state, questions, **kwargs):
            barrier.wait(timeout=3)
            return response_for(questions)

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(1), provider="both")
        self.assertEqual(len(result["ranked"]), 1)

    def test_confident_provider_disagreement_is_not_presented_as_consensus(self):
        def decide(provider, state, questions, **kwargs):
            return response_for(questions, 0 if provider == "jev" else 3, confidence=1)

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(1), provider="both")
        row = result["ranked"][0]
        self.assertEqual(row["score"], 1.5)
        self.assertEqual(row["confidence"], 1)
        self.assertEqual(row["confidence_kind"], "minimum_provider_confidence")
        self.assertEqual(row["score_disagreement"], 3)
        self.assertEqual(row["probabilities"], {"0": 0.5, "1": 0.0, "2": 0.0, "3": 0.5})
        self.assertEqual(row["provider_scores"]["jev"]["score"], 0)
        self.assertEqual(row["provider_scores"]["perplexity"]["score"], 3)

    def test_large_shortlists_are_batched_to_at_most_128_questions(self):
        calls = []

        def decide(provider, state, questions, **kwargs):
            calls.append((provider, copy.deepcopy(questions)))
            return response_for(questions)

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(257), provider="both")
        for provider in ("jev", "perplexity"):
            batches = [questions for who, questions in calls if who == provider]
            self.assertEqual(sorted(map(len, batches)), [1, 128, 128])
            keys = [key for questions in batches for key in questions]
            self.assertEqual(len(set(keys)), 257)
        self.assertEqual(len(result["ranked"]), 257)
        self.assertEqual(result["rejected"], [])

    def test_every_candidate_is_ranked_or_rejected_exactly_once(self):
        def decide(provider, state, questions, **kwargs):
            answers = {key: score_answer() for key in questions}
            keys = list(answers)
            answers[keys[1]] = None
            del answers[keys[2]]
            answers[keys[3]]["probabilities"]["0"] = "bad"
            return {"answers": answers}

        original = candidates(5)
        snapshot = copy.deepcopy(original)
        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", original)
        ids = [row["id"] for row in result["ranked"] + result["rejected"]]
        self.assertCountEqual(ids, [1, 2, 3, 4, 5])
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len(result["ranked"]), 2)
        self.assertEqual(len(result["rejected"]), 3)
        self.assertTrue(all(row["error"] for row in result["rejected"]))
        self.assertEqual(original, snapshot)

    def test_both_uses_the_surviving_valid_answer_for_each_candidate(self):
        def decide(provider, state, questions, **kwargs):
            result = response_for(questions)
            if provider == "perplexity":
                result["answers"][next(iter(questions))] = {"type": "score"}
            return result

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(2), provider="both")
        self.assertCountEqual([row["id"] for row in result["ranked"]], [1, 2])
        self.assertEqual(result["rejected"], [])
        self.assertEqual(result["status"], "degraded")
        fallback = next(row for row in result["ranked"] if row["id"] == 1)
        self.assertEqual(fallback["used_providers"], ["jev"])
        self.assertEqual(fallback["aggregation"], "single")
        self.assertEqual(fallback["confidence_kind"], "provider_reported")
        self.assertIsNone(fallback["score_disagreement"])
        self.assertEqual(list(fallback["provider_scores"]), ["jev"])
        self.assertIn("perplexity", fallback["provider_errors"])
        combined = next(row for row in result["ranked"] if row["id"] == 2)
        self.assertEqual(combined["used_providers"], ["jev", "perplexity"])
        self.assertEqual(combined["aggregation"], "equal_mean")

    def test_both_provider_failure_uses_the_other_provider_and_reports_it(self):
        providers = importlib.import_module("decision_providers")

        def decide(provider, state, questions, **kwargs):
            if provider == "perplexity":
                raise providers.ProviderError("Perplexity unavailable")
            return response_for(questions)

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(), provider="both")
        self.assertEqual(result["provider"], "both")
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["used_providers"], ["jev"])
        self.assertEqual(len(result["ranked"]), 3)
        self.assertEqual(result["rejected"], [])
        self.assertEqual(result["providers"]["perplexity"]["status"], "error")
        self.assertIn("Perplexity unavailable", result["providers"]["perplexity"]["error"])
        self.assertEqual(result["providers"]["perplexity"]["calls"], 0)
        self.assertTrue(all(row["used_providers"] == ["jev"] for row in result["ranked"]))

    def test_both_missing_key_uses_the_configured_provider_without_calling_the_other(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "jev-test-key"}, clear=True):
            with patch.object(router, "decision_call", side_effect=lambda provider, state, questions, **kw:
                              response_for(questions)) as call:
                result = router.score_candidates("Build a dashboard", candidates(), provider="both")
        self.assertEqual([args.args[0] for args in call.call_args_list], ["jev"])
        self.assertEqual(result["provider"], "both")
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["used_providers"], ["jev"])
        self.assertEqual(len(result["ranked"]), 3)
        self.assertEqual(result["providers"]["perplexity"]["status"], "unavailable")
        self.assertIn("PERPLEXITY_API_KEY", result["providers"]["perplexity"]["error"])
        self.assertEqual(result["providers"]["perplexity"]["calls"], 0)

    def test_both_missing_jev_key_uses_perplexity_without_calling_jev(self):
        providers = importlib.import_module("decision_providers")
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(providers, "KEY_FILE", Path(folder) / "missing-key"):
                with patch.dict(os.environ, {"PERPLEXITY_API_KEY": "pplx-test-key"}, clear=True):
                    with patch.object(router, "decision_call", side_effect=lambda provider, state, questions, **kw:
                                      response_for(questions)) as call:
                        result = router.score_candidates("Build a dashboard", candidates(), provider="both")
        self.assertEqual([args.args[0] for args in call.call_args_list], ["perplexity"])
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["used_providers"], ["perplexity"])
        self.assertEqual(len(result["ranked"]), 3)
        self.assertEqual(result["providers"]["jev"]["status"], "unavailable")
        self.assertEqual(result["providers"]["jev"]["attempted_calls"], 0)

    def test_both_invalid_key_or_model_skips_that_provider_and_keeps_ranking(self):
        for failed in ("jev", "perplexity"):
            survivor = "perplexity" if failed == "jev" else "jev"
            key_variable = "TYPESAFE_API_KEY" if failed == "jev" else "PERPLEXITY_API_KEY"
            model_option = "jev_model" if failed == "jev" else "perplexity_model"
            for problem in ("key", "model"):
                with self.subTest(provider=failed, problem=problem):
                    environment = {key_variable: "invalid\nprivate-key"} if problem == "key" else {}
                    options = {model_option: "invalid\nprivate-model"} if problem == "model" else {}
                    with patch.dict(os.environ, environment):
                        with patch.object(router, "decision_call", side_effect=lambda provider, state, questions, **kw:
                                          response_for(questions)) as call:
                            result = router.score_candidates("Build a dashboard", candidates(),
                                                             provider="both", **options)
                    self.assertEqual([args.args[0] for args in call.call_args_list], [survivor])
                    self.assertEqual(result["status"], "degraded")
                    self.assertEqual(result["used_providers"], [survivor])
                    self.assertEqual(len(result["ranked"]), 3)
                    self.assertEqual(result["providers"][failed]["status"], "unavailable")
                    self.assertEqual(result["providers"][failed]["attempted_calls"], 0)
                    self.assertNotIn("private-", json.dumps(result))
                    if problem == "model":
                        self.assertIsNone(result["providers"][failed]["requested_model"])

    def test_both_unexpected_provider_exception_falls_back_without_exposing_private_details(self):
        def decide(provider, state, questions, **kwargs):
            if provider == "jev":
                raise RuntimeError("private-key Private project specification")
            return response_for(questions)

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(), provider="both")
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["used_providers"], ["perplexity"])
        self.assertEqual(result["providers"]["jev"]["status"], "error")
        self.assertTrue(result["providers"]["jev"]["error"])
        self.assertNotIn("private-key", json.dumps(result))
        self.assertNotIn("Private project specification", json.dumps(result))

    def test_both_malformed_provider_envelope_uses_the_other_provider(self):
        for envelope in (None, [], {}, {"answers": None}, {"answers": []}):
            with self.subTest(envelope=envelope):
                def decide(provider, state, questions, **kwargs):
                    return envelope if provider == "perplexity" else response_for(questions)
                with patch.object(router, "decision_call", side_effect=decide):
                    result = router.score_candidates("Build a dashboard", candidates(), provider="both")
                self.assertEqual(result["status"], "degraded")
                self.assertEqual(result["used_providers"], ["jev"])
                self.assertEqual(len(result["ranked"]), 3)
                self.assertEqual(result["providers"]["perplexity"]["status"], "error")

    def test_both_keeps_successful_batches_and_stops_calling_a_failed_provider(self):
        providers = importlib.import_module("decision_providers")
        calls = {"jev": [], "perplexity": []}
        request_id = "a80f8d70-9c20-4e8e-9cf8-a07e7b009db0"

        def decide(provider, state, questions, **kwargs):
            calls[provider].append(list(questions))
            if provider == "jev" and len(calls[provider]) == 2:
                raise providers.ProviderError("jev request failed (network or timeout).")
            return {**response_for(questions, 2.8 if provider == "jev" else 1.8),
                    "model": f"{provider}-resolved", "_request_id": request_id,
                    "usage": {"input_tokens": 42, "output_tokens": 1}}

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(257), provider="both")
        self.assertEqual(len(calls["jev"]), 2)
        self.assertEqual(list(map(len, calls["perplexity"])), [128, 128, 1])
        self.assertEqual(len(result["ranked"]), 257)
        self.assertEqual(result["rejected"], [])
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["used_providers"], ["jev", "perplexity"])
        rows = {row["id"]: row for row in result["ranked"]}
        for identifier in range(1, 129):
            self.assertEqual(rows[identifier]["aggregation"], "equal_mean")
            self.assertAlmostEqual(rows[identifier]["score"], 2.3)
        for identifier in range(129, 258):
            self.assertEqual(rows[identifier]["used_providers"], ["perplexity"])
            self.assertEqual(rows[identifier]["aggregation"], "single")
            self.assertAlmostEqual(rows[identifier]["score"], 1.8)
            self.assertIsNone(rows[identifier]["score_disagreement"])
        metadata = result["providers"]["jev"]
        self.assertEqual(metadata["status"], "partial")
        self.assertEqual(metadata["calls"], 1)
        self.assertEqual(metadata["attempted_calls"], 2)
        self.assertEqual(metadata["resolved_models"], ["jev-resolved"])
        self.assertEqual(metadata["request_ids"], [request_id])
        self.assertEqual(metadata["usage"], {"input_tokens": None, "output_tokens": None})
        self.assertEqual(result["providers"]["perplexity"]["calls"], 3)
        self.assertEqual(result["providers"]["perplexity"]["usage"],
                         {"input_tokens": 126, "output_tokens": 3})

    def test_both_rejects_a_candidate_only_when_neither_provider_has_a_valid_answer(self):
        def decide(provider, state, questions, **kwargs):
            answers = response_for(questions)["answers"]
            keys = list(questions)
            if provider == "jev":
                del answers[keys[0]]
            else:
                answers[keys[1]] = {"type": "score"}
            answers[keys[2]] = None
            return {"answers": answers}

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(), provider="both")
        rows = {row["id"]: row for row in result["ranked"]}
        self.assertEqual(rows[1]["used_providers"], ["perplexity"])
        self.assertEqual(rows[2]["used_providers"], ["jev"])
        self.assertEqual([row["id"] for row in result["rejected"]], [3])
        self.assertEqual(set(result["rejected"][0]["provider_errors"]), {"jev", "perplexity"})
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["used_providers"], ["jev", "perplexity"])

    def test_both_all_provider_failures_preserves_an_unavailable_result_and_all_rejections(self):
        providers = importlib.import_module("decision_providers")
        with patch.object(router, "decision_call", side_effect=providers.ProviderError("Provider unavailable")):
            result = router.score_candidates("Build a dashboard", candidates(), provider="both")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["provider"], "both")
        self.assertEqual(result["used_providers"], [])
        self.assertEqual(result["ranked"], [])
        self.assertEqual([row["id"] for row in result["rejected"]], [1, 2, 3])
        for provider in ("jev", "perplexity"):
            self.assertEqual(result["providers"][provider]["status"], "error")
            self.assertEqual(result["providers"][provider]["calls"], 0)
            self.assertEqual(result["providers"][provider]["attempted_calls"], 1)

    def test_both_without_any_configured_provider_returns_unavailable_without_requests(self):
        providers = importlib.import_module("decision_providers")
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(providers, "KEY_FILE", Path(folder) / "missing-key"):
                with patch.dict(os.environ, {}, clear=True):
                    with patch.object(router, "decision_call") as call:
                        result = router.score_candidates("Build a dashboard", candidates(), provider="both")
        call.assert_not_called()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["used_providers"], [])
        self.assertEqual(result["ranked"], [])
        self.assertEqual(len(result["rejected"]), 3)
        self.assertTrue(all(item["status"] == "unavailable" for item in result["providers"].values()))

    def test_explicit_single_provider_network_failure_still_raises_without_switching(self):
        providers = importlib.import_module("decision_providers")
        for provider in ("jev", "perplexity"):
            with self.subTest(provider=provider):
                with patch.object(router, "decision_call", side_effect=providers.ProviderError("Provider unavailable")) as call:
                    with self.assertRaises(providers.ProviderError):
                        router.score_candidates("Build a dashboard", candidates(), provider=provider)
                self.assertEqual([args.args[0] for args in call.call_args_list], [provider])

    def test_provider_metadata_collects_usage_and_resolved_model_per_batch(self):
        request_id = "a80f8d70-9c20-4e8e-9cf8-a07e7b009db0"

        def decide(provider, state, questions, **kwargs):
            return {**response_for(questions), "model": f"{provider}-resolved",
                    "usage": {"input_tokens": 42, "output_tokens": 1},
                    "_request_id": request_id}

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(129), provider="both")
        for provider in ("jev", "perplexity"):
            metadata = result["providers"][provider]
            self.assertEqual(metadata["calls"], 2)
            self.assertEqual(metadata["resolved_models"], [f"{provider}-resolved"])
            self.assertEqual(metadata["usage"], {"input_tokens": 84, "output_tokens": 2})
            self.assertIn(request_id, metadata["request_ids"])

    def test_missing_response_metadata_stays_unavailable(self):
        with patch.object(router, "decision_call", side_effect=lambda provider, state, questions, **kwargs:
                          response_for(questions)):
            result = router.score_candidates("Build a dashboard", candidates(129), provider="both")
        for provider in ("jev", "perplexity"):
            metadata = result["providers"][provider]
            self.assertEqual(metadata["calls"], 2)
            self.assertEqual(metadata["usage"], {"input_tokens": None, "output_tokens": None})
            self.assertEqual(metadata["resolved_models"], [])
            self.assertEqual(metadata["request_ids"], [])

    def test_usage_is_total_only_when_every_batch_reports_the_field(self):
        calls = 0

        def decide(provider, state, questions, **kwargs):
            nonlocal calls
            calls += 1
            usage = {"input_tokens": 42, "output_tokens": 1} if calls == 1 else {"output_tokens": 2}
            return {**response_for(questions), "usage": usage}

        with patch.object(router, "decision_call", side_effect=decide):
            result = router.score_candidates("Build a dashboard", candidates(129))
        self.assertEqual(result["providers"]["jev"]["usage"],
                         {"input_tokens": None, "output_tokens": 3})
        self.assertEqual(len(result["ranked"]), 129)

    def test_malformed_entire_envelope_fails_instead_of_rejecting_each_candidate(self):
        providers = importlib.import_module("decision_providers")
        for envelope in (None, [], "answers", {}, {"answers": None}, {"answers": []}):
            with self.subTest(envelope=envelope):
                with patch.object(router, "decision_call", return_value=envelope):
                    with self.assertRaises(providers.ProviderError):
                        router.score_candidates("Build a dashboard", candidates(2))

    def test_invalid_mode_fails_before_any_request(self):
        with patch.object(router, "decision_call") as call:
            with self.assertRaises((ValueError, RuntimeError)):
                router.score_candidates("Build a dashboard", candidates(), provider="other")
        call.assert_not_called()

    def test_empty_candidate_list_does_not_make_a_request(self):
        with patch.object(router, "decision_call") as call:
            result = router.score_candidates("Build a dashboard", [], provider="both")
        call.assert_not_called()
        self.assertEqual(result["ranked"], [])
        self.assertEqual(result["rejected"], [])


class ProviderHTTPTests(unittest.TestCase):
    def setUp(self):
        self.providers = importlib.import_module("decision_providers")
        self.environment = patch.dict(os.environ, {"TYPESAFE_API_KEY": "jev-secret",
            "PERPLEXITY_API_KEY": "pplx-secret"}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.state = {"project": {"spec": "Private project specification"}}
        self.questions = {"skill_000": {"type": "score", "instructions": {
            "candidate_skill": {"name": "dashboard", "description": "Build React dashboards"},
            "question": "How useful is this skill?"}, "criteria": router.LEVELS}}

    def response(self, payload):
        response = io.BytesIO(json.dumps(payload).encode("utf-8"))
        response.headers = {}
        return response

    def test_requests_use_fixed_https_endpoints_correct_keys_and_default_models(self):
        cases = [
            ("jev", "https://api.typesafe.ai/v1/systemone", "jev-secret", "jev-latest"),
            ("perplexity", "https://api.perplexity.ai/v1/decisions", "pplx-secret",
             "pplx-decider-v1.1-27b"),
        ]
        for provider, endpoint, key, model in cases:
            with self.subTest(provider=provider):
                payload = response_for(self.questions)
                with patch.object(self.providers, "_open", return_value=self.response(payload)) as call:
                    result = self.providers.decision_call(provider, self.state, self.questions)
                request = call.call_args.args[0]
                self.assertEqual(request.full_url, endpoint)
                self.assertEqual(request.get_method(), "POST")
                self.assertEqual(request.get_header("Authorization"), f"Bearer {key}")
                self.assertEqual(request.get_header("Content-type"), "application/json")
                body = json.loads(request.data)
                self.assertEqual(body, {"model": model, "state": self.state, "questions": self.questions})
                self.assertEqual(result, payload)
                self.assertEqual(call.call_args.kwargs["timeout"], 180 if provider == "jev" else 30)

    def test_explicit_model_overrides_environment_and_environment_overrides_default(self):
        cases = [("jev", "JEV_MODEL", "jev-custom"),
                 ("perplexity", "PERPLEXITY_DECISION_MODEL", "pplx-custom")]
        for provider, variable, model in cases:
            with self.subTest(provider=provider), patch.dict(os.environ, {variable: model}):
                with patch.object(self.providers, "_open", side_effect=lambda *a, **kw:
                                  self.response(response_for(self.questions))) as call:
                    self.providers.decision_call(provider, self.state, self.questions)
                    self.assertEqual(json.loads(call.call_args.args[0].data)["model"], model)
                    self.providers.decision_call(provider, self.state, self.questions, model="explicit-model")
                    self.assertEqual(json.loads(call.call_args.args[0].data)["model"], "explicit-model")

    def test_perplexity_does_not_use_the_typesafe_key(self):
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "jev-secret"}, clear=True):
            with patch.object(self.providers, "_open") as call:
                with self.assertRaises(self.providers.ProviderError) as caught:
                    self.providers.decision_call("perplexity", self.state, self.questions)
        call.assert_not_called()
        self.assertIn("PERPLEXITY_API_KEY", str(caught.exception))
        self.assertNotIn("jev-secret", str(caught.exception))

    def test_jev_retains_key_file_fallback_with_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            key_file = Path(directory) / "typesafe_api_key"
            key_file.write_text("  saved-test-key\n", encoding="utf-8")
            with patch.object(self.providers, "KEY_FILE", key_file):
                with patch.dict(os.environ, {}, clear=True):
                    self.assertEqual(self.providers.provider_key("jev"), "saved-test-key")
                self.assertEqual(self.providers.provider_key("jev"), "jev-secret")

    def test_invalid_request_limits_or_nonfinite_state_fail_before_network(self):
        invalid_questions = ({}, {f"q{i}": self.questions["skill_000"] for i in range(129)})
        with patch.object(self.providers, "_open") as call:
            for questions in invalid_questions:
                with self.subTest(count=len(questions)), self.assertRaises(self.providers.ProviderError):
                    self.providers.decision_call("perplexity", self.state, questions)
            with self.assertRaises(self.providers.ProviderError):
                self.providers.decision_call("perplexity", {"invalid": float("nan")}, self.questions)
        call.assert_not_called()

    def test_unknown_provider_cannot_send_keys_to_an_arbitrary_url(self):
        with patch.object(self.providers, "_open") as call:
            with self.assertRaises((ValueError, self.providers.ProviderError)):
                self.providers.decision_call("https://attacker.test/", self.state, self.questions)
        call.assert_not_called()

    def test_transport_does_not_follow_redirects_with_bearer_credentials(self):
        requests = []

        class RedirectHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                requests.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/redirected")
                self.end_headers()

            def do_GET(self):
                requests.append(self.path)
                self.send_response(200)
                self.end_headers()

            def log_message(self, format, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}/start",
                data=b"{}", headers={"Authorization": "Bearer dummy-secret"})
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.providers._open(request, timeout=2)
            self.assertEqual(caught.exception.code, 302)
            self.assertEqual(requests, ["/start"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_permanent_http_error_is_not_retried_and_does_not_echo_response_body(self):
        sensitive = b"pplx-secret Private project specification"
        error = urllib.error.HTTPError("https://api.perplexity.ai/v1/decisions", 401,
                                       "Unauthorized", {}, io.BytesIO(sensitive))
        with patch.object(self.providers, "_open", side_effect=error) as call:
            with self.assertRaises(self.providers.ProviderError) as caught:
                self.providers.decision_call("perplexity", self.state, self.questions, retries=3)
        self.assertEqual(call.call_count, 1)
        self.assertIn("401", str(caught.exception))
        self.assertNotIn("pplx-secret", str(caught.exception))
        self.assertNotIn("Private project specification", str(caught.exception))

    def test_transient_http_errors_retry_with_backoff(self):
        for status in (429, 500, 502, 503, 504):
            with self.subTest(status=status):
                error = urllib.error.HTTPError("https://api.perplexity.ai/v1/decisions", status,
                                               "Temporary", {"Retry-After": "2"}, io.BytesIO(b""))
                with patch.object(self.providers, "_open", side_effect=[error,
                                  self.response(response_for(self.questions))]) as call:
                    with patch("time.sleep") as sleep:
                        result = self.providers.decision_call("perplexity", self.state,
                                                              self.questions, retries=1)
                self.assertEqual(call.call_count, 2)
                self.assertEqual(len(result["answers"]), 1)
                sleep.assert_called()

    def test_network_failures_are_bounded_and_sanitized(self):
        with patch.object(self.providers, "_open", side_effect=urllib.error.URLError(
                          "pplx-secret Private project specification")) as call:
            with patch("time.sleep"):
                with self.assertRaises(self.providers.ProviderError) as caught:
                    self.providers.decision_call("perplexity", self.state, self.questions, retries=2)
        self.assertEqual(call.call_count, 3)
        self.assertNotIn("pplx-secret", str(caught.exception))
        self.assertNotIn("Private project specification", str(caught.exception))

    def test_retry_after_is_respected_or_rejected_if_above_wait_limit(self):
        endpoint = "https://api.perplexity.ai/v1/decisions"
        error = urllib.error.HTTPError(endpoint, 429, "Rate limited", {"Retry-After": "2"},
                                       io.BytesIO(b""))
        with patch.object(self.providers, "_open", side_effect=[error,
                          self.response(response_for(self.questions))]):
            with patch("time.sleep") as sleep:
                self.providers.decision_call("perplexity", self.state, self.questions, retries=1)
        self.assertGreaterEqual(sleep.call_args.args[0], 2)
        error = urllib.error.HTTPError(endpoint, 429, "Rate limited", {"Retry-After": "120"},
                                       io.BytesIO(b""))
        with patch.object(self.providers, "_open", side_effect=error) as call:
            with patch("time.sleep") as sleep:
                with self.assertRaises(self.providers.ProviderError):
                    self.providers.decision_call("perplexity", self.state, self.questions, retries=1)
        self.assertEqual(call.call_count, 1)
        sleep.assert_not_called()

    def test_only_valid_uuid_request_ids_are_captured(self):
        request_id = "a80f8d70-9c20-4e8e-9cf8-a07e7b009db0"
        for header in (request_id, "pplx-secret Private project specification"):
            response = self.response(response_for(self.questions))
            response.headers = {"x-request-id": header}
            with patch.object(self.providers, "_open", return_value=response):
                result = self.providers.decision_call("perplexity", self.state, self.questions)
            if header == request_id:
                self.assertEqual(result["_request_id"], request_id)
            else:
                self.assertNotIn("_request_id", result)

    def test_malformed_success_body_fails_as_provider_error(self):
        for payload in (b"not-json", b"null", b"[]", b'{"answers": null}', b'{}'):
            with self.subTest(payload=payload):
                response = io.BytesIO(payload)
                response.headers = {}
                with patch.object(self.providers, "_open", return_value=response):
                    with self.assertRaises(self.providers.ProviderError):
                        self.providers.decision_call("perplexity", self.state, self.questions, retries=0)

    def test_legacy_jev_wrapper_remains_callable(self):
        with patch.object(router, "decision_call", return_value={"answers": {}}) as call:
            result = router.jev_call(self.state, self.questions, retries=1)
        self.assertEqual(result, {"answers": {}})
        self.assertEqual(call.call_args.args[0], "jev")
        self.assertEqual(call.call_args.kwargs["retries"], 1)

    def test_malformed_http_response_does_not_echo_private_fragments(self):
        for error in (http.client.BadStatusLine("private-response-fragment"),
                      http.client.IncompleteRead(b"private-response-fragment", 100)):
            with self.subTest(error=type(error).__name__):
                with patch.object(self.providers, "_open", side_effect=error):
                    with self.assertRaises(self.providers.ProviderError) as caught:
                        self.providers.decision_call("perplexity", self.state, self.questions, retries=0)
                self.assertNotIn("private-response-fragment", str(caught.exception))

    def test_excessively_nested_json_fails_without_a_request_or_retry(self):
        nested = {"text": "nested"}
        for _ in range(10000):
            nested = {"nested": nested}
        with patch.object(self.providers, "_open") as call:
            with self.assertRaises(self.providers.ProviderError):
                self.providers.decision_call("perplexity", nested, self.questions)
        call.assert_not_called()
        response = io.BytesIO(b'{"answers":{},"extra":' + b'[' * 10000 + b'0' + b']' * 10000 + b'}')
        with patch.object(self.providers, "_open", return_value=response) as call:
            with self.assertRaises(self.providers.ProviderError):
                self.providers.decision_call("perplexity", self.state, self.questions)
        self.assertEqual(call.call_count, 1)


class RouteCLITests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db = Path(self.directory.name) / "skills.db"
        self.output = Path(self.directory.name) / "ranking.json"
        with contextlib.closing(sqlite3.connect(self.db)) as db:
            db.executescript(router.SCHEMA)
            db.execute("INSERT INTO skills(id,name,desc,tags,tier,repo,url) VALUES"
                       "(1,'react-dashboard','Build accessible React dashboards','react','vendor',"
                       "'example/skills','https://example.test/dashboard')")
            db.execute("INSERT INTO skills_fts(rowid,name,desc,tags) VALUES"
                       "(1,'react-dashboard','Build accessible React dashboards','react')")
            db.commit()

    def route(self, arguments, environment=None):
        argv = ["router.py", "route", "React dashboard", "--db", str(self.db),
                "--out", str(self.output)] + arguments
        calls = []

        def decide(provider, state, questions, **kwargs):
            calls.append((provider, kwargs))
            return response_for(questions)

        keys = {"TYPESAFE_API_KEY": "jev-test-key", "PERPLEXITY_API_KEY": "pplx-test-key"}
        with patch.dict(os.environ, {**keys, **(environment or {})}, clear=True):
            with patch.object(sys, "argv", argv), patch.object(router, "decision_call", side_effect=decide):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(router.main(), 0)
        return calls, json.loads(self.output.read_text(encoding="utf-8"))

    def test_original_route_command_defaults_to_jev(self):
        calls, result = self.route([])
        self.assertEqual([provider for provider, _ in calls], ["jev"])
        self.assertEqual(result["provider"], "jev")
        self.assertEqual([row["name"] for row in result["ranked"]], ["react-dashboard"])

    def test_combined_console_output_explains_confidence_and_disagreement(self):
        argv = ["router.py", "route", "React dashboard", "--db", str(self.db), "--provider", "both"]
        output = io.StringIO()
        def decide(provider, state, questions, **kwargs):
            return response_for(questions, 0 if provider == "jev" else 3, 1)
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "jev-test-key", "PERPLEXITY_API_KEY": "pplx-test-key"}, clear=True):
            with patch.object(sys, "argv", argv), patch.object(router, "decision_call", side_effect=decide):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(router.main(), 0)
        self.assertIn("minimum provider confidence", output.getvalue())
        self.assertIn("disagreement", output.getvalue())
        self.assertIn("3.00", output.getvalue())

    def test_degraded_both_console_identifies_the_survivor_and_provider_reported_confidence(self):
        providers = importlib.import_module("decision_providers")
        argv = ["router.py", "route", "React dashboard", "--db", str(self.db),
                "--provider", "both", "--out", str(self.output)]
        output = io.StringIO()

        def decide(provider, state, questions, **kwargs):
            if provider == "perplexity":
                raise providers.ProviderError("perplexity request failed (network or timeout).")
            return response_for(questions)

        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "jev-test-key", "PERPLEXITY_API_KEY": "pplx-test-key"}, clear=True):
            with patch.object(sys, "argv", argv), patch.object(router, "decision_call", side_effect=decide):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(router.main(), 0)
        rendered = output.getvalue().lower()
        self.assertIn("fallback", rendered)
        self.assertIn("jev", rendered)
        self.assertRegex(rendered, r"provider.?reported confidence")
        self.assertRegex(rendered, r"2\.40\s+0\.80\s+-+\s+react-dashboard")
        result = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["used_providers"], ["jev"])

    def test_both_total_failure_returns_nonzero_and_writes_an_unavailable_artifact(self):
        providers = importlib.import_module("decision_providers")
        argv = ["router.py", "route", "React dashboard", "--db", str(self.db),
                "--provider", "both", "--out", str(self.output)]
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "jev-test-key", "PERPLEXITY_API_KEY": "pplx-test-key"}, clear=True):
            with patch.object(sys, "argv", argv), patch.object(router, "decision_call",
                                      side_effect=providers.ProviderError("Provider unavailable")):
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    status = router.main()
        self.assertNotEqual(status, 0)
        self.assertTrue(self.output.exists(), "Failed routing must remain inspectable in its output artifact")
        result = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["provider"], "both")
        self.assertEqual(result["used_providers"], [])
        self.assertEqual(result["ranked"], [])
        self.assertEqual([row["id"] for row in result["rejected"]], [1])
        self.assertTrue(result["rejected"][0]["error"])

    def test_provider_option_and_model_options_are_forwarded(self):
        calls, result = self.route(["--provider", "both", "--jev-model", "jev-custom",
                                   "--perplexity-model", "pplx-custom"])
        self.assertEqual(result["provider"], "both")
        self.assertEqual({provider: kwargs["model"] for provider, kwargs in calls},
                         {"jev": "jev-custom", "perplexity": "pplx-custom"})

    def test_environment_selects_provider_but_explicit_option_wins(self):
        calls, result = self.route([], {"SKILL_ROUTER_PROVIDER": "perplexity"})
        self.assertEqual(result["provider"], "perplexity")
        self.assertEqual([provider for provider, _ in calls], ["perplexity"])
        calls, result = self.route(["--provider", "jev"], {"SKILL_ROUTER_PROVIDER": "perplexity"})
        self.assertEqual(result["provider"], "jev")
        self.assertEqual([provider for provider, _ in calls], ["jev"])

    def test_invalid_provider_is_rejected_before_any_request(self):
        with patch.object(sys, "argv", ["router.py", "route", "React", "--provider", "other"]):
            with patch.object(router, "decision_call") as call, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    router.main()
        self.assertEqual(caught.exception.code, 2)
        call.assert_not_called()

    def test_zero_accepted_candidates_returns_failure_and_preserves_rejections(self):
        argv = ["router.py", "route", "React dashboard", "--db", str(self.db),
                "--out", str(self.output)]
        with patch.dict(os.environ, {"TYPESAFE_API_KEY": "jev-test-key"}, clear=True):
            with patch.object(sys, "argv", argv), patch.object(router, "decision_call",
                                                               return_value={"answers": {}}):
                with contextlib.redirect_stdout(io.StringIO()):
                    status = router.main()
        self.assertNotEqual(status, 0)
        result = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(result["ranked"], [])
        self.assertEqual([row["id"] for row in result["rejected"]], [1])
        self.assertTrue(result["rejected"][0]["error"])

    def test_nonpositive_candidate_and_display_limits_fail_before_any_request(self):
        for option in ("--top", "--show"):
            for value in ("-1", "0"):
                with self.subTest(option=option, value=value):
                    argv = ["router.py", "route", "React dashboard", "--db", str(self.db), option, value]
                    with patch.object(sys, "argv", argv), patch.object(router, "decision_call") as call:
                        with contextlib.redirect_stderr(io.StringIO()):
                            with self.assertRaises(SystemExit) as caught:
                                router.main()
                    self.assertEqual(caught.exception.code, 2)
                    call.assert_not_called()

    def test_invalid_environment_provider_fails_before_any_request(self):
        argv = ["router.py", "route", "React dashboard", "--db", str(self.db)]
        with patch.dict(os.environ, {"SKILL_ROUTER_PROVIDER": "other"}, clear=True):
            with patch.object(sys, "argv", argv), patch.object(router, "decision_call") as call:
                with contextlib.redirect_stderr(io.StringIO()):
                    status = router.main()
        self.assertNotEqual(status, 0)
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()

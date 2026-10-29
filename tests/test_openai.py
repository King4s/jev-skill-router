"""Offline contracts for explicit OpenAI Decisions selection."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import decision_providers as providers
import router


class OpenAIDecisionsTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"OPENAI_API_KEY": "synthetic-openai-key"}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.questions = {
            f"skill_{i:03}": {"type": "score", "instructions": {"candidate_skill": {"name": f"skill-{i}"}},
                             "criteria": router.LEVELS} for i in range(2)
        }
        self.response = {"model": "gpt-6-luna", "usage": {"input_tokens": 100, "output_tokens": 0},
                         "answers": [self.answer(name) for name in self.questions]}

    def answer(self, name):
        return {"name": name, "type": "score", "score": 2.4, "confidence": 0.8,
                "probabilities": [{"value": i, "label": label, "probability": p}
                                  for i, (label, p) in enumerate(zip(router.LEVELS, [0, 0, 0.6, 0.4]))]}

    def call(self, response=None):
        reply = io.BytesIO(json.dumps(response if response is not None else self.response).encode())
        with patch.object(providers, "_open", return_value=reply) as call:
            result = providers.decision_call("openai", {"project": {"spec": "Build a dashboard"}},
                                             self.questions, retries=0)
        return result, call.call_args.args[0]

    def test_request_uses_openai_schema_and_only_its_credential(self):
        result, request = self.call()
        self.assertEqual(request.full_url, "https://api.openai.com/v1/decisions")
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-openai-key")
        body = json.loads(request.data)
        self.assertEqual(set(body), {"model", "input", "questions"})
        self.assertEqual(body["model"], "gpt-6-luna")
        self.assertEqual(body["input"][0]["content"][0]["data"]["project"]["spec"], "Build a dashboard")
        for question in body["questions"]:
            self.assertIn(question["name"], self.questions)
            self.assertIsInstance(question["instructions"], str)
            self.assertEqual(question["levels"], [{"label": level} for level in router.LEVELS])
        self.assertEqual(result["usage"], self.response["usage"])
        self.assertIsNone(router.validate_score(result["answers"]["skill_000"], 4))

    def test_answers_match_names_even_when_reordered_and_refusals_stay_rejected(self):
        response = copy.deepcopy(self.response)
        response["answers"] = [{"name": "skill_001", "type": "refusal"}, response["answers"][0]]
        result, _ = self.call(response)
        self.assertIsNone(router.validate_score(result["answers"]["skill_000"], 4))
        self.assertIsNotNone(router.validate_score(result["answers"]["skill_001"], 4))

    def test_duplicate_unknown_or_unnamed_answers_fail_without_retry(self):
        for bad in (self.answer("unknown"), self.answer(None), self.answer("skill_000")):
            response = {"answers": [self.answer("skill_000"), bad]}
            with self.subTest(name=bad["name"]), self.assertRaises(providers.ProviderError):
                self.call(response)

    def test_malformed_distribution_rejects_only_affected_candidate(self):
        for probabilities in (None, {}, [], [{"value": True, "label": "bad", "probability": 1}],
                              [self.answer("skill_000")["probabilities"][0]] * 4):
            response = copy.deepcopy(self.response)
            response["answers"][0]["probabilities"] = probabilities
            with self.subTest(probabilities=probabilities):
                result, _ = self.call(response)
                self.assertIsNotNone(router.validate_score(result["answers"]["skill_000"], 4))
                self.assertIsNone(router.validate_score(result["answers"]["skill_001"], 4))

    def test_explicit_openai_routes_end_to_end_without_other_providers(self):
        candidate = {"id": 1, "name": "dashboard", "desc": "Build dashboard", "repo": "example/skills"}
        reply = {**self.response, "answers": [self.answer("skill_000")]}
        with patch.object(providers, "_open", return_value=io.BytesIO(json.dumps(reply).encode())) as call:
            result = router.score_candidates("Build dashboard", [candidate], provider="openai")
        self.assertEqual(call.call_count, 1)
        self.assertEqual(result["used_providers"], ["openai"])
        self.assertEqual(result["providers"]["openai"]["usage"], self.response["usage"])
        self.assertEqual(len(result["ranked"]), 1)

    def test_cli_exposes_optional_provider_and_model(self):
        with patch.object(sys, "argv", ["router.py", "route", "Build dashboard", "--provider", "openai",
                                       "--openai-model", "gpt-6-luna"]), \
             patch.object(router, "cmd_route", return_value=0) as command, \
             contextlib.redirect_stdout(io.StringIO()):
            router.main()
        self.assertEqual(command.call_args.args[0].provider, "openai")
        self.assertEqual(command.call_args.args[0].openai_model, "gpt-6-luna")

    def test_missing_openai_key_and_unsupported_model_fail_before_transport(self):
        for environment, model in (({}, None), ({"OPENAI_API_KEY": "test"}, "other-model")):
            with self.subTest(model=model), patch.dict(os.environ, environment, clear=True), \
                 patch.object(providers, "_open") as call:
                with self.assertRaises(providers.ProviderError):
                    providers.decision_call("openai", {}, self.questions, model=model)
                call.assert_not_called()


if __name__ == "__main__":
    unittest.main()

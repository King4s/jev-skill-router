"""Owner-selected default policy: Jev first, OpenAI only for unresolved answers."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import router
from decision_providers import ProviderError
from provider_priority import provider_order


def answer():
    return {'type':'score','score':2.4,'confidence':0,
            'probabilities':{'0':0,'1':0,'2':0.6,'3':0.4}}


class DefaultFallbackTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {'TYPESAFE_API_KEY':'synthetic-jev',
                                              'OPENAI_API_KEY':'synthetic-openai'}, clear=True)
        environment.start()
        self.addCleanup(environment.stop)
        self.candidates = [{'id':1,'name':'review','desc':'Review code','repo':'test/skills'},
                           {'id':2,'name':'tests','desc':'Test code','repo':'test/skills'}]

    def test_default_is_jev_first_and_healthy_low_confidence_never_calls_openai(self):
        with patch.object(router,'decision_call',side_effect=lambda provider,state,questions,**kwargs:
                          {'answers':{key:answer() for key in questions}}) as call:
            result=router.score_candidates('Review code',self.candidates)
        self.assertEqual(result['provider'],'both')
        self.assertEqual(result['priority']['order'],['jev','openai'])
        self.assertEqual([args.args[0] for args in call.call_args_list],['jev'])
        self.assertEqual(call.call_args.kwargs['retries'],0)
        self.assertEqual(call.call_args.kwargs['timeout'],30)

    def test_failure_uses_openai_without_retries_or_perplexity(self):
        def decide(provider,state,questions,**kwargs):
            if provider=='jev':
                raise ProviderError('Synthetic transport failure')
            return {'answers':{key:answer() for key in questions}}
        with patch.object(router,'decision_call',side_effect=decide) as call:
            result=router.score_candidates('Review code',self.candidates,provider='both')
        self.assertEqual([args.args[0] for args in call.call_args_list],['jev','openai'])
        self.assertTrue(all(args.kwargs['retries']==0 for args in call.call_args_list))
        self.assertEqual(result['used_providers'],['openai'])
        self.assertEqual(len(result['ranked']),2)

    def test_partial_fallback_only_receives_unresolved_candidate(self):
        def decide(provider,state,questions,**kwargs):
            if provider=='jev':
                return {'answers':{'skill_000':answer()}}
            self.assertEqual(set(questions),{'skill_001'})
            return {'answers':{'skill_001':answer()}}
        with patch.object(router,'decision_call',side_effect=decide) as call:
            result=router.score_candidates('Review code',self.candidates)
        self.assertEqual(call.call_count,2)
        self.assertEqual(len(result['ranked']),2)
        self.assertEqual(result['ranked'][0]['used_providers'],['jev'])

    def test_single_provider_selection_stays_strict(self):
        with patch.object(router,'decision_call',side_effect=ProviderError('Synthetic outage')) as call:
            with self.assertRaises(ProviderError):
                router.score_candidates('Review code',self.candidates,provider='jev')
        self.assertEqual(call.call_count,1)

    def test_priority_records_the_explicit_owner_policy(self):
        result=provider_order({'jev':'jev-latest','openai':'gpt-6-luna'})
        self.assertEqual(result['order'],['jev','openai'])
        self.assertEqual(result['basis'],'user_selected_order')

    def test_explicit_owner_order_is_not_replaced_by_quality_estimates(self):
        profile={'schema_version':1,'order':['jev','openai'],'providers':{
            'jev':{'models':['jev-test'],'accuracy':0.1,'cost_per_candidate_usd':1},
            'openai':{'models':['gpt-6-luna'],'accuracy':1,'cost_per_candidate_usd':0}}}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'priority.json'
            path.write_text(json.dumps(profile),encoding='utf-8')
            result=provider_order({'jev':'jev-test','openai':'gpt-6-luna'},profile_path=path)
        self.assertEqual(result['order'],['jev','openai'])
        self.assertEqual(result['basis'],'user_selected_order')

    def test_invalid_explicit_orders_fail_before_any_provider_request(self):
        source=Path(router.__file__).with_name('provider-priority.json')
        for order in (['jev','jev'],['jev'],['jev','unknown'],[True,'openai']):
            with self.subTest(order=order), tempfile.TemporaryDirectory() as folder:
                profile=json.loads(source.read_text(encoding='utf-8'))
                profile['order']=order
                path=Path(folder)/'priority.json'
                path.write_text(json.dumps(profile),encoding='utf-8')
                with patch.object(router,'decision_call') as call:
                    with self.assertRaises(ProviderError):
                        router.score_candidates('Review code',self.candidates,priority_profile=path)
                    call.assert_not_called()

    def test_invalid_timeouts_are_rejected_before_transport(self):
        import decision_providers
        for timeout in (0,181,True,float('nan')):
            with self.subTest(timeout=timeout), patch.object(decision_providers,'_open') as call:
                with self.assertRaises(ProviderError):
                    decision_providers.decision_call('openai',{}, {'skill':{}},timeout=timeout)
                call.assert_not_called()


if __name__=='__main__':
    unittest.main()

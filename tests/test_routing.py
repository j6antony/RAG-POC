"""Offline checks for conversation routing; no models or cloud calls."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('routing_under_test', Path(__file__).resolve().parents[1] / 'src' / 'rag.py')
rag = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {name: Mock() for name in ('services', 'retrieval', 'web')}):
    spec.loader.exec_module(rag)


class RoutingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        rag.get_conversation_state.cache_clear()

    def test_state_is_scoped_and_keeps_five_turns(self):
        state = rag.get_conversation_state('user-a', 'chat-a')
        for score in range(7):
            state.update(score, 'WEB')
        self.assertEqual(list(state.scores), [2, 3, 4, 5, 6])
        self.assertEqual(len(state.routes), 5)
        self.assertIs(state, rag.get_conversation_state('user-a', 'chat-a'))
        self.assertEqual(list(rag.get_conversation_state('user-b', 'chat-a').scores), [])
        self.assertEqual(list(rag.get_conversation_state('user-a', 'chat-b').scores), [])

    def test_router_uses_previous_state_and_validates_response(self):
        state = rag.ConversationState()
        state.update(.4, 'WEB')
        matches = [{'score': .9, 'metadata': {'text': 'Internal excerpt'}}]
        history = [SimpleNamespace(role='user', text='Previous question')]
        with patch.object(rag.genai, 'Client') as client:
            generate = client.return_value.__enter__.return_value.models.generate_content
            generate.return_value.text = 'BOTH'
            self.assertEqual(rag.decide_route('Question', matches, history, state), 'BOTH')
            prompt = rag.json.loads(generate.call_args.kwargs['contents'])
            self.assertEqual(prompt['previous_scores'], [.4])
            self.assertEqual(prompt['previous_routes'], ['WEB'])
            self.assertEqual(prompt['history'][0]['text'], 'Previous question')
            generate.return_value.text = 'INVALID'
            with self.assertLogs(level='WARNING'):
                self.assertEqual(rag.decide_route('Question', matches, history, state), 'INTERNAL')
            generate.side_effect = RuntimeError('Unavailable')
            matches[0]['score'] = .2
            with self.assertLogs(level='ERROR'):
                self.assertEqual(rag.decide_route('Question', matches, history, state), 'WEB')

    def test_no_matches_routes_to_web_without_router_call(self):
        with patch.object(rag.genai, 'Client') as client:
            self.assertEqual(rag.decide_route('Question', [], [], rag.ConversationState()), 'WEB')
            client.assert_not_called()

    async def test_all_routes_use_correct_context_and_update_state(self):
        for route, expected in [('INTERNAL', 'Internal'), ('WEB', 'External'), ('BOTH', 'Internal\n\nExternal')]:
            with self.subTest(route=route):
                embedder, retrieval, web = Mock(), Mock(), Mock()
                embedder.embed_request.return_value.tolist.return_value = [.1]
                retrieval.retrieve.return_value = {'matches': [{'score': .8, 'metadata': {'text': 'Internal'}}]}
                web.search.return_value = [{'text': 'External'}]
                with patch.object(rag, 'rewrite_query', return_value='Question'), patch.object(rag, 'get_embedder', return_value=embedder), patch.object(rag, 'get_vectorDB', return_value=Mock()), patch.object(rag, 'Retrieval', return_value=retrieval), patch.object(rag, 'Web', return_value=web) as web_class, patch.object(rag, 'decide_route', return_value=route), patch.object(rag, 'feedtoai', return_value='Answer') as feed:
                    result = await rag.answer_request('Question', [], 'user', 'Alex', route)
                    self.assertEqual(result, 'Answer')
                    feed.assert_called_once_with('Alex', expected, 'Question')
                    self.assertEqual(web_class.call_count, 0 if route == 'INTERNAL' else 1)
                    self.assertEqual(list(rag.get_conversation_state('user', route).routes), [route])

    async def test_failed_answer_does_not_record_successful_turn(self):
        embedder, retrieval = Mock(), Mock()
        embedder.embed_request.return_value.tolist.return_value = [.1]
        retrieval.retrieve.return_value = {'matches': [{'score': .8, 'metadata': {'text': 'Internal'}}]}
        with patch.object(rag, 'rewrite_query', return_value='Question'), patch.object(rag, 'get_embedder', return_value=embedder), patch.object(rag, 'get_vectorDB', return_value=Mock()), patch.object(rag, 'Retrieval', return_value=retrieval), patch.object(rag, 'decide_route', return_value='INTERNAL'), patch.object(rag, 'feedtoai', side_effect=RuntimeError('Unavailable')):
            with self.assertRaises(RuntimeError):
                await rag.answer_request('Question', [], 'user', 'Alex', 'chat')
        self.assertEqual(list(rag.get_conversation_state('user', 'chat').scores), [])


if __name__ == '__main__':
    unittest.main()

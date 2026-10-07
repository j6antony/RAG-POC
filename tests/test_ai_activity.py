"""Offline checks for model attempts and metadata-only retrieval logging."""
import asyncio
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from guardrail_audit import begin_audit, end_audit, persist_hits, record_event
from google import genai
from google.genai import errors


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).resolve().parents[1] / 'src' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.token, self.events = begin_audit(SimpleNamespace(id='alice', email='alice@example.com', user_metadata={}), 'chat', 2)
        self.addCleanup(end_audit, self.token)

    def test_event_defaults_and_new_table(self):
        record_event(event_type='request_started')
        self.assertEqual(self.events[0]['status'], 'success')
        self.assertIsNone(self.events[0]['document_id'])
        db = Mock()
        persist_hits(db, self.events)
        db.table.assert_called_once_with('ai_audit_events')

    def test_model_retry_records_each_attempt_without_exception_text(self):
        with patch.dict(sys.modules, {name: Mock() for name in ('tools', 'web', 'analysis_agent')}):
            controller = load('audit_controller', 'controller.py')
        client = Mock()
        client.models.generate_content.side_effect = [errors.APIError(503, {'error': {'message': 'private text'}}), SimpleNamespace(text='Done')]
        with patch.object(controller.asyncio, 'sleep', new=AsyncMock()):
            result = asyncio.run(controller.call_gemini_with_retry(client, [], None))
        self.assertEqual(result.text, 'Done')
        self.assertEqual([e['status'] for e in self.events], ['started', 'failed', 'started', 'success'])
        self.assertNotIn('private text', str(self.events))

    def test_retrieval_deduplicates_documents_and_excludes_text(self):
        with patch.dict(sys.modules, {name: Mock() for name in ('services', 'vectordb', 'web')}):
            tools = load('audit_tools', 'tools.py')
        handler = tools.Tools.__new__(tools.Tools)
        handler.embedder = Mock()
        handler.embedder.embed_request.return_value.tolist.return_value = [0.1]
        handler.vectorDB = Mock()
        handler.vectorDB.query.return_value.matches = [SimpleNamespace(id=str(i), score=0.9, metadata={
            'document_id': doc, 'filename': doc + '.pdf', 'text': 'private document contents',
            'access_level': 1, 'classification': 'internal',
        }) for i, doc in enumerate(['a', 'a', 'b'])]
        handler.namespace, handler.access, handler.user_id = 'company', 2, 'alice'
        handler.supabase, handler.images = Mock(), {}
        with patch.object(tools, 'image_references', return_value=[]):
            asyncio.run(handler.search_internal('company policy'))
        self.assertEqual([e['document_id'] for e in self.events], ['a', 'b'])
        self.assertEqual(self.events[0]['details']['classification'], 'internal')
        self.assertNotIn('private document contents', str(self.events))

    def test_analysis_model_failure_is_recorded(self):
        module = load('audit_analysis', 'analysis_agent.py')
        with patch.object(genai, 'Client', return_value=Mock()):
            agent = module.AnalysisAgent()
        agent.client.models.generate_content.side_effect = RuntimeError('private text')
        with self.assertRaises(RuntimeError):
            asyncio.run(agent.run('analyze policies', 'alice', 2))
        self.assertEqual([e['status'] for e in self.events], ['started', 'failed'])
        self.assertNotIn('private text', str(self.events))

"""Offline access-policy checks; no cloud or model calls."""
import importlib.util
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import document_images
from PIL import Image
Image.init()

spec = importlib.util.spec_from_file_location('knowledge_api', Path(__file__).resolve().parents[1] / 'src/api.py')
api = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {name: Mock() for name in ('controller', 'services', 'authentification', 'supabase')}):
    spec.loader.exec_module(api)

class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.db = Mock()
        self.db.auth.get_user.return_value.user = SimpleNamespace(id='me')
        self.query = self.db.table.return_value
        for method in ('select', 'in_', 'order', 'insert'):
            getattr(self.query, method).return_value = self.query
        patcher = patch.object(api, 'supabase', self.db)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.headers = {'Autherization': 'Bearer test-token'}

    def test_listing_matches_retrieval_at_every_level(self):
        for level in (1, 2, 3):
            self.query.execute.return_value.data = [dict(id=f'{name}-{owner}', filename='test.md', visibility=name, uploaded_by=owner)
                for name, minimum in api.VISIBILITY_LEVELS.items() if minimum <= level for owner in ('me', 'other')]
            with patch.object(api, 'get_user_access', return_value=level):
                response = self.client.get('/knowledge', headers=self.headers)
            self.assertEqual(response.status_code, 200)
            result = response.json()
            self.assertEqual(result['access_level'], level)
            self.assertEqual(len(result['documents']), (level - 1) * 2 + 1)
            self.assertTrue(all(d['access_level'] < level or d['uploaded_by'] == 'me' for d in result['documents']))
            self.query.in_.assert_called_with('visibility', [name for name, minimum in api.VISIBILITY_LEVELS.items() if minimum <= level])

    def test_invalid_access_denied(self):
        with patch.object(api, 'get_user_access', return_value=None):
            self.assertEqual(self.client.get('/knowledge', headers=self.headers).status_code, 403)
        self.db.table.assert_not_called()

    def test_invalid_uploads_do_not_insert(self):
        for filename, content, level, status in [('test.md', b'text', 2, 403), ('test.pdf', b'%PDF', 1, 400), ('test.txt', b' ', 1, 400), ('test.txt', b'\xff', 1, 400)]:
            with patch.object(api, 'get_user_access', return_value=1):
                response = self.client.post('/upload', headers=self.headers, data={'access_level': level}, files={'file': (filename, content)})
            self.assertEqual(response.status_code, status)
        self.db.table.assert_not_called()

    def test_upload_visibility_and_document_id(self):
        self.query.execute.return_value.data = [{'id': 'document-id'}]
        embedder, vectors = Mock(), Mock()
        with patch.object(api, 'get_user_access', return_value=2), patch.object(api, 'get_embedder', return_value=embedder), patch.object(api, 'get_vectorDB', return_value=vectors):
            response = self.client.post('/upload', headers=self.headers, data={'access_level': 2}, files={'file': ('test.md', b'Hello')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['visibility'], 'manager')
        self.query.insert.assert_called_once_with({'filename': 'test.md', 'uploaded_by': 'me', 'visibility': 'manager'})
        embedder.embed.assert_called_once_with('test.md', b'Hello', 'me', vectors, 2, 'document-id')


    def test_pdf_upload_passes_page_and_image_mapping_into_embedder(self):
        from test_document_images import sample_pdf
        self.query.execute.return_value.data = [{'id': 'document-id'}]
        embedder, vectors = Mock(), Mock()
        with patch.object(api, 'get_user_access', return_value=2), patch.object(api, 'get_embedder', return_value=embedder), patch.object(api, 'get_vectorDB', return_value=vectors):
            response = self.client.post('/upload', headers=self.headers, data={'access_level': 2}, files={'file': ('manual.pdf', sample_pdf())})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['image_count'], 2)
        chunks = embedder.embed.call_args.kwargs['chunks']
        self.assertEqual({c.metadata['page'] for c in chunks}, {1, 2})
        self.assertTrue(all(c.metadata['image_ids'] for c in chunks))
        self.assertEqual(self.db.storage.from_.return_value.upload.call_count, 2)

    def test_image_endpoint_checks_parent_document_before_download(self):
        image_id = '00000000-0000-0000-0000-000000000001'
        images, documents = Mock(), Mock()
        self.db.table.side_effect = lambda name: images if name == 'knowledge_images' else documents
        images.select.return_value.eq.return_value.execute.return_value.data = [{'document_id': 'doc', 'image_path': 'doc/image.png'}]
        documents.select.return_value.eq.return_value.execute.return_value.data = [{'visibility': 'manager', 'uploaded_by': 'other'}]
        self.db.storage.from_.return_value.download.return_value = b'png'
        with patch.object(api, 'get_user_access', return_value=2):
            response = self.client.get(f'/knowledge/images/{image_id}', headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.db.storage.from_.assert_not_called()
        with patch.object(api, 'get_user_access', return_value=3):
            response = self.client.get(f'/knowledge/images/{image_id}', headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'png')
        self.assertEqual(response.headers['cache-control'], 'private, no-store')

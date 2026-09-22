"""Offline regression tests: no model download or external API calls."""
from threading import RLock
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from src import api, embedding, rag
from src.chunk import Chunk
from src.vectordb import VectorDB


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.auth = Mock()
        api.app.dependency_overrides[api.get_supabase] = lambda: SimpleNamespace(auth=self.auth)
        self.client = TestClient(api.app)
        self.user = SimpleNamespace(id='user-a', email='alex@example.com', user_metadata={'name': 'Alex'})
        self.auth.get_user.return_value = SimpleNamespace(user=self.user)
        self.session = SimpleNamespace(access_token='test-token', expires_at=2000000000)

    def tearDown(self):
        api.app.dependency_overrides.clear()
        self.client.close()

    def test_login_and_signup_have_same_session_contract(self):
        result = SimpleNamespace(user=self.user, session=self.session)
        self.auth.sign_in_with_password.return_value = result
        self.auth.sign_up.return_value = result
        body = {'email': 'alex@example.com', 'password': 'long-password'}
        login = self.client.post('/login', json=body)
        signup = self.client.post('/signup', json={**body, 'name': 'Alex'})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json(), signup.json())
        self.assertEqual(login.json()['access_token'], 'test-token')
        self.assertEqual(login.json()['user']['id'], 'user-a')

    def test_signup_confirmation_does_not_return_session(self):
        self.auth.sign_up.return_value = SimpleNamespace(user=self.user, session=None)
        response = self.client.post('/signup', json={'name': 'Alex', 'email': 'alex@example.com', 'password': 'long-password'})
        self.assertTrue(response.json()['requires_confirmation'])
        self.assertNotIn('access_token', response.json())

    def test_auth_rejects_missing_misspelled_and_invalid_headers(self):
        for headers in ({}, {'Autherization': 'Bearer test-token'}, {'Authorization': 'Basic test-token'}, {'Authorization': 'Bearer '}):
            response = self.client.post('/chat', headers=headers, json={'message': 'Hello'})
            self.assertEqual(response.status_code, 401)
        self.auth.get_user.assert_not_called()
        self.auth.get_user.return_value = SimpleNamespace(user=None)
        self.assertEqual(self.client.post('/chat', headers={'Authorization': 'Bearer bad'}, json={'message': 'Hello'}).status_code, 401)

    def test_chat_uses_verified_user_and_rejects_blank_question(self):
        with patch.object(api, 'answer_request', return_value={'answer': 'Answer', 'sources': []}) as answer:
            response = self.client.post('/chat', headers={'Authorization': 'Bearer test-token'}, json={'message': ' Question ', 'user_id': 'attacker'})
            self.assertEqual(response.status_code, 200)
            self.auth.get_user.assert_called_with('test-token')
            answer.assert_called_once_with('Question', 'user-a')
            response = self.client.post('/chat', headers={'Authorization': 'Bearer test-token'}, json={'message': '   '})
            self.assertEqual(response.status_code, 422)

    def test_upload_bytes_and_namespace(self):
        embedder = Mock()
        embedder.embed.return_value = 2
        with patch.object(api, 'get_embedder', return_value=embedder):
            response = self.client.post('/upload', headers={'Authorization': 'Bearer test-token'}, files={'file': ('policy.md', b'# Policy\nRemote work allowed.', 'text/markdown')})
        self.assertEqual(response.status_code, 200)
        embedder.embed.assert_called_once_with('policy.md', b'# Policy\nRemote work allowed.', 'user-a')
        self.assertEqual(response.json()['chunks'], 2)

    def test_invalid_uploads_and_removed_file_listing(self):
        for name, contents, status in [('a.pdf', b'pdf', 415), ('a.md', b'\xff', 415), ('a.txt', b'  ', 422), ('a.md', b'a' * (5 * 1024 * 1024 + 1), 413)]:
            response = self.client.post('/upload', headers={'Authorization': 'Bearer token'}, files={'file': (name, contents)})
            self.assertEqual(response.status_code, status)
        self.assertEqual(self.client.get('/files').status_code, 404)


class IndexingTests(unittest.TestCase):
    def test_chunk_bytes_preserve_filename_and_do_not_accumulate(self):
        splitter = Chunk()
        content = b'# Policy\n\n' + b'Remote work. ' * 100
        first = splitter.get_chunks_file(content, 'policy.md')
        second = splitter.get_chunks_file(content, 'policy.md')
        self.assertGreater(len(first), 1)
        self.assertEqual(len(first), len(second))
        self.assertTrue(all(chunk.metadata['source'] == 'policy.md' for chunk in first))
        self.assertIn('# Policy', first[0].page_content)

    def test_embedding_uses_namespace_and_serializable_values(self):
        embedder = embedding.Embed.__new__(embedding.Embed)
        embedder.chunk = Chunk()
        embedder.lock = RLock()
        vector = Mock()
        vector.tolist.return_value = [1., 2., 3.]
        embedder.model = Mock()
        embedder.model.encode.return_value = [vector]
        db = Mock()
        with patch.object(embedding, 'get_vector_db', return_value=db):
            self.assertEqual(embedder.embed('policy.md', b'# Policy\nHello.', 'user-b'), 1)
            vectors = db.replace_document.call_args.args[0]
            self.assertEqual(vectors[0]['values'], [1., 2., 3.])
            self.assertEqual(vectors[0]['metadata']['filename'], 'policy.md')
            self.assertEqual(db.replace_document.call_args.kwargs['namespace'], 'user-b')
            with self.assertRaises(ValueError):
                embedder.embed('empty.md', b'', 'user-b')
            self.assertEqual(db.replace_document.call_count, 1)

    def test_shorter_reupload_removes_only_old_chunks_after_success(self):
        db = VectorDB.__new__(VectorDB)
        db.index = Mock()
        db.index.list.return_value = [SimpleNamespace(vectors=[SimpleNamespace(id=id) for id in ['policy.md-0', 'policy.md-1', 'policy.md-other-0']])]
        db.replace_document([{'id': 'policy.md-0'}], 'policy.md', 'user-a')
        db.index.delete.assert_called_once_with(ids=['policy.md-1'], namespace='user-a')
        self.assertEqual([call[0] for call in db.index.method_calls], ['list', 'upsert', 'delete'])
        db.index.reset_mock()
        db.index.upsert.side_effect = RuntimeError('Pinecone unavailable')
        with self.assertRaises(RuntimeError):
            db.replace_document([{'id': 'policy.md-0'}], 'policy.md', 'user-a')
        db.index.delete.assert_not_called()

    def test_pinecone_batches_and_requires_namespace(self):
        db = VectorDB.__new__(VectorDB)
        db.index = Mock()
        db.upsert([{'id': str(i)} for i in range(205)], 'user-a')
        self.assertEqual([len(call.kwargs['vectors']) for call in db.index.upsert.call_args_list], [100, 100, 5])
        self.assertTrue(all(call.kwargs['namespace'] == 'user-a' for call in db.index.upsert.call_args_list))
        db.query([1.], 'user-b')
        self.assertEqual(db.index.query.call_args.kwargs['namespace'], 'user-b')
        with self.assertRaises(ValueError):
            db.query([1.], '')

    def test_empty_namespace_skips_gemini(self):
        db, embedder = Mock(), Mock()
        db.query.return_value = {'matches': []}
        embedder.embed_request.return_value.tolist.return_value = [1.]
        with patch.object(rag, 'get_vector_db', return_value=db), patch.object(rag, 'get_embedder', return_value=embedder), patch.object(rag.genai, 'Client') as client:
            result = rag.answer_request('Question', 'user-c')
        db.query.assert_called_once_with([1.], namespace='user-c', top_k=5)
        client.assert_not_called()
        self.assertEqual(result['sources'], [])

    def test_chat_returns_real_sources(self):
        db, embedder = Mock(), Mock()
        db.query.return_value = {'matches': [{'metadata': {'filename': 'policy.md', 'header 1': 'Policy', 'text': 'Remote work allowed.'}}]}
        with patch.object(rag, 'get_vector_db', return_value=db), patch.object(rag, 'get_embedder', return_value=embedder), patch.object(rag.genai, 'Client') as client:
            client.return_value.__enter__.return_value.models.generate_content.return_value.text = 'You can work remotely.'
            result = rag.answer_request('Remote work?', 'user-a')
        self.assertEqual(result['answer'], 'You can work remotely.')
        self.assertEqual(result['sources'], [{'title': 'policy.md', 'section': 'Policy', 'text': 'Remote work allowed.'}])


if __name__ == '__main__':
    unittest.main()

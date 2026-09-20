"""Run with: .venv/bin/python -m unittest discover -s tests"""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import embedding
import retrieval
from chunk import Chunk
from storage import CHROMA_DIR


class Model:
    def encode(self, text):
        return np.array([len(text), 1.0, 2.0])


class IndexingTests(unittest.TestCase):
    def test_reindex_and_retrieve_across_working_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "docs"
            data.mkdir()
            first = data / "a.md"
            second = data / "b.md"
            first.write_text("# A\n\n" + "Original policy. " * 100)
            second.write_text("# B\n\nOther document.")
            embedder = embedding.Embed.__new__(embedding.Embed)
            embedder.folder = data
            embedder.model = Model()
            with patch.object(embedding, "CHROMA_DIR", root / "db"), patch.object(retrieval, "CHROMA_DIR", root / "db"):
                collection = embedder.embed_data()
                count = collection.count()
                embedder.embed_data()
                self.assertEqual(collection.count(), count)
                # Simulate an ID produced by the old global bulk counter.
                collection.add(ids=["a.md_999"], embeddings=[[1., 1., 2.]], documents=["Legacy"], metadatas=[{"source": "a.md"}])
                first.write_text("# A\n\nUpdated policy.")
                embedder.embed_data_file("a.md")
                result = collection.get(where={"source": "a.md"})
                self.assertEqual(result["ids"], ["a.md_0"])
                self.assertEqual(result["documents"], ["Updated policy."])
                self.assertEqual(collection.get(where={"source": "b.md"})["documents"], ["Other document."])
                embedder.embed_data()
                self.assertEqual(collection.count(), 2)
                with patch.object(embedder.model, "encode", side_effect=RuntimeError("Model failed")):
                    with self.assertRaises(RuntimeError):
                        embedder.embed_data_file(first)
                self.assertEqual(collection.count(), 2)
                original_cwd = Path.cwd()
                try:
                    os.chdir(root)
                    embedder.embed_data_file(second)
                    result = retrieval.Retrieval(np.array([1., 1., 2.])).score_list_chroma(2)
                    self.assertEqual(len(result["documents"][0]), 2)
                finally:
                    os.chdir(original_cwd)
                first.write_text("")
                embedder.embed_data_file(first)
                self.assertEqual(collection.get(where={"source": "a.md"})["ids"], [])
                self.assertEqual(collection.count(), 1)
                splitter = Chunk(data)
                self.assertEqual(len(splitter.get_chunks()), len(splitter.get_chunks()))
        self.assertTrue(CHROMA_DIR.is_absolute())


if __name__ == "__main__":
    unittest.main()

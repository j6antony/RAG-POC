"""In-memory PDF fixtures test extraction without cloud services or models."""
import sys
from pathlib import Path
from io import BytesIO
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject
from PIL import Image
from document_images import extract_pdf, can_view_document, image_references, store_images


def sample_pdf(text=True):
    writer = PdfWriter()
    for number in (1, 2):
        page = writer.add_blank_page(width=300, height=300)
        image = DecodedStreamObject()
        image.set_data(bytes([255, 0, 0] if number == 1 else [0, 0, 255]))
        image.update({NameObject('/Type'): NameObject('/XObject'), NameObject('/Subtype'): NameObject('/Image'),
                      NameObject('/Width'): NumberObject(1), NameObject('/Height'): NumberObject(1),
                      NameObject('/ColorSpace'): NameObject('/DeviceRGB'), NameObject('/BitsPerComponent'): NumberObject(8)})
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({
            NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)}),
            NameObject('/XObject'): DictionaryObject({NameObject('/Im1'): writer._add_object(image)})})
        stream = DecodedStreamObject()
        content = f'BT /F1 12 Tf 20 250 Td (Page {number} architecture description.) Tj ET ' if text else ''
        stream.set_data((content + 'q 100 0 0 100 20 20 cm /Im1 Do Q').encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class ImageMappingTests(unittest.TestCase):
    def test_page_chunks_map_only_to_images_on_their_page(self):
        chunks, images = extract_pdf(sample_pdf(), 'manual.pdf')
        self.assertEqual(len(images), 2)
        self.assertEqual({c.metadata['page'] for c in chunks}, {1, 2})
        for chunk in chunks:
            expected = [i['id'] for i in images if i['page_number'] == chunk.metadata['page']]
            self.assertEqual(chunk.metadata['image_ids'], expected)
            self.assertIn(f"Page {chunk.metadata['page']}", chunk.page_content)
        for item in images:
            with Image.open(BytesIO(item['contents'])) as image:
                self.assertEqual(image.format, 'PNG')

    def test_scanned_pdf_does_not_report_success(self):
        with self.assertRaisesRegex(ValueError, 'OCR'):
            extract_pdf(sample_pdf(text=False), 'scanned.pdf')

    def test_image_access_matches_level_and_owner_policy(self):
        for user_level in (1, 2, 3):
            for name, level in [('user', 1), ('manager', 2), ('admin', 3)]:
                for owner in ('me', 'other'):
                    self.assertEqual(can_view_document({'visibility': name, 'uploaded_by': owner}, 'me', user_level),
                                     level < user_level or (level == user_level and owner == 'me'))
        self.assertFalse(can_view_document({'visibility': 'private'}, 'me', 3))

    def test_references_are_deduplicated_and_checked_against_document_page(self):
        db, docs, images = Mock(), Mock(), Mock()
        db.table.side_effect = lambda name: docs if name == 'knowledge_documents' else images
        docs.select.return_value.eq.return_value.execute.return_value.data = [{'visibility': 'user', 'uploaded_by': 'me', 'filename': 'manual.pdf'}]
        query = images.select.return_value
        query.eq.return_value = query
        query.in_.return_value = query
        query.execute.return_value.data = [{'id': 'image', 'document_id': 'doc', 'page_number': 2}]
        match = {'metadata': {'document_id': 'doc', 'page': 2, 'image_ids': ['image']}}
        result = image_references(db, [match, match], 'me', 1)
        self.assertEqual(len(result), 1)
        query.eq.assert_any_call('page_number', 2)
        query.eq.assert_any_call('document_id', 'doc')
        docs.select.return_value.eq.return_value.execute.return_value.data[0]['uploaded_by'] = 'other'
        self.assertEqual(image_references(db, [match], 'me', 1), [])

    def test_storage_upload_is_cleaned_up_if_registry_insert_fails(self):
        db = Mock()
        db.table.return_value.insert.return_value.execute.side_effect = RuntimeError('failed')
        with self.assertRaises(RuntimeError):
            store_images(db, 'doc', [{'id': 'image', 'page_number': 1, 'contents': b'png'}])
        db.storage.from_.return_value.remove.assert_called_once_with(['doc/image.png'])

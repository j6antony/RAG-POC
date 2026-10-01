"""Page-based PDF mapping. Bytes stay in private Storage, references in Pinecone."""
from io import BytesIO
from uuid import uuid4

from pypdf import PdfReader
from PIL import Image
from langchain_text_splitters import RecursiveCharacterTextSplitter

import pytesseract

BUCKET = 'knowledge-images'

def run_ocr(image_bytes):
    with Image.open(BytesIO(image_bytes)) as image:
        text = pytesseract.image_to_string(image)
    return text

def extract_pdf(contents, filename):
    chunks, images = [], []
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    try:
        reader = PdfReader(BytesIO(contents))
        if reader.is_encrypted:
            raise ValueError('Password-protected PDFs are not supported.')
        for page_number, page in enumerate(reader.pages, 1):
            image_ids = []
            for embedded in page.images:
                image_id = str(uuid4())
                # Normalize to PNG so the browser can display every extracted image.
                output = BytesIO()
                with Image.open(BytesIO(embedded.data)) as image:
                    image.convert('RGBA').save(output, format='PNG')
                image_bytes = output.getvalue()
                ocr_text = run_ocr(image_bytes)
                images.append({'id': image_id, 'page_number': page_number, 'contents': image_bytes})
                image_ids.append(image_id)
                if ocr_text.strip():
                    chunks.extend(
                        splitter.create_documents([ocr_text],
                                                  metadatas=[{
                                                    'source': filename,
                                                    'page': page_number,
                                                    'image_ids': [image_id],
                                                    'source_type': 'image_ocr',
                                                    'image_id': image_id,
                                                  }])
                    )
            text = page.extract_text() or ''
            if text.strip():
                chunks.extend(splitter.create_documents([text], metadatas=[{
                    'source': filename, 'page': page_number, 'image_ids': image_ids, 'source_type': 'pdf_text',
                }]))
    except ValueError:
        raise
    except Exception as error:
        raise ValueError('Could not read this PDF. Upload a valid, unencrypted PDF.') from error
    if not chunks:
        raise ValueError('No readable text could be extracted from this PDF.')
    return chunks, images


def store_images(supabase, document_id, images):
    bucket = supabase.storage.from_(BUCKET)
    paths = []
    try:
        for image in images:
            path = f'{document_id}/{image["id"]}.png'
            bucket.upload(path, image['contents'], file_options={'content-type': 'image/png'})
            paths.append(path)
            supabase.table('knowledge_images').insert({
                'id': image['id'], 'document_id': str(document_id),
                'page_number': image['page_number'], 'image_path': path,
            }).execute()
    except Exception:
        if paths:
            bucket.remove(paths)
        raise
    return paths


def can_view_document(document, user_id, user_access):
    level = {'user': 1, 'manager': 2, 'admin': 3}.get(document.get('visibility'))
    return level is not None and (level < user_access or (
        level == user_access and str(document.get('uploaded_by')) == str(user_id)))


def image_references(supabase, matches, user_id, user_access):
    """Only return mappings whose document AND page match an authorized hit."""
    references = {}
    for match in matches:
        metadata = match['metadata'] or {}
        document_id = metadata.get('document_id')
        image_ids = metadata.get('image_ids') or []
        if not document_id or not image_ids:
            continue
        documents = supabase.table('knowledge_documents').select('*').eq('id', document_id).execute().data
        if not documents or not can_view_document(documents[0], user_id, user_access):
            continue
        rows = (supabase.table('knowledge_images').select('id,document_id,page_number')
                .eq('document_id', document_id).eq('page_number', metadata.get('page'))
                .in_('id', image_ids).execute().data)
        for row in rows or []:
            references[row['id']] = {**row, 'filename': documents[0]['filename']}
    return list(references.values())

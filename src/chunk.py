"""Split uploaded UTF-8 text without writing temporary files."""
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


class Chunk:
    def get_chunks_file(self, contents: bytes, filename: str):
        headings = MarkdownHeaderTextSplitter(
            headers_to_split_on=[('#', 'header 1'), ('##', 'header 2'), ('###', 'header 3')],
            strip_headers=False,
        )
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        sections = headings.split_text(contents.decode('utf-8'))
        for section in sections:
            section.metadata['source'] = filename
        return splitter.split_documents(sections)

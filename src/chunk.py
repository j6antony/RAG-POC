"""
Basic structure for how the chunking will be done:
    - First split the document headers into chunks
    - Then go through those individual chunks and split it into chunks of about 500 tokens
    - ensure that when these are split that it will have an overlap of about 50 tokens
How to do:
- reading: use pathlib to read the md files
- recognizing headers: use langChains markdown-aware splitter to split the headers
- for splitting into 500 tokens use tiktoken to split (note that this means we will be using openAI style models)
Issues:
- The class setup here is just stupid likley probably want to provide more customizability like move the splitter setups
    into the init and allow the options there to be provided as perameters
"""
from pathlib import Path
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter
class Chunk:
    def __init__(self):
        #master collection of all chunks
        self.all_chunks = []

    def get_chunks(self):
        print("getting chunks")
        self.all_chunks = []
        #loading the files into the reader
        folder_path = Path(self.folder).glob("*.md")

        headers_to_split_on = [
            ('#', "header 1"),
            ('##', "header 2"),
            ('###', "header 3")
        ]

        heading_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on = headers_to_split_on,
            strip_headers=True # do we want to strip the headers?
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 500,
            chunk_overlap = 50
        )

        #split each individual file in the folder
        for file in folder_path:
            text = file.read_text(encoding="utf-8")
            sections = heading_splitter.split_text(text)
            # add the file name to the individual splits
            for section in sections:
                section.metadata["source"] = file.name
            #break the splits into smaller pieces
            chunks = text_splitter.split_documents(sections)
            #save all the chunks
            self.all_chunks.extend(chunks)
        print("got chunks")
        return self.all_chunks
    # this is not really neccessary in later edit probably want to clean this object up
    def get_chunks_file(self, file, filename):
        print("chunking file")
        headers_to_split_on = [
                    ('#', "header 1"),
                    ('##', "header 2"),
                    ('###', "header 3")
        ]
        heading_splitter = MarkdownHeaderTextSplitter(
                headers_to_split_on = headers_to_split_on,
                strip_headers=True # do we want to strip the headers?
        )
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = 500,
            chunk_overlap = 50
        )
        text = file.decode("utf-8")
        sections = heading_splitter.split_text(text)
        # add the file name to the individual splits
        for section in sections:
            section.metadata["source"] = filename
        #break the splits into smaller pieces
        chunks = text_splitter.split_documents(sections)
        #save all the chunks
        self.all_chunks.extend(chunks)
        print("file chunked")
        print(f"Chunks: {len(self.all_chunks)}")
        return chunks





from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate
from langchain.docstore.document import Document
from langchain_core.output_parsers import StrOutputParser
from PyPDF2 import PdfReader
from typing import List, Dict, Any
from dotenv import load_dotenv
import uuid
import io
import os
from config import LLMConfig


load_dotenv()

class EmbeddingService:
    def __init__(
        self,
        prompt_messages: list = [],
        embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2", 
        chat_model_name: str = "gpt-3.5-turbo",
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        persist_directory: str = os.getenv("CHROMA_DB_DIRECTORY_PATH", "chroma_db"),
        collection_name: str = "default_collection"
    ):
        self.embedding_model_name = embedding_model_name
        self.chat_model_name = chat_model_name
        
        # Instantiate HuggingFaceEmbeddings for embedding
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.embedding_model_name,
            model_kwargs={'device': 'cpu'}
        )
        
        # Instantiate the OpenAI chat model for generation
        self.llm = LLMConfig.LLM_PROVIDER

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        os.makedirs(self.persist_directory, exist_ok=True)

        self.db = Chroma(
            collection_name=self.collection_name,
            persist_directory=self.persist_directory,
            embedding_function=self.embeddings,
        )

        self.retriever = self.db.as_retriever()
        
        if prompt_messages:
            self.prompt = ChatPromptTemplate.from_messages(prompt_messages)
        else:
            self.prompt = ChatPromptTemplate.from_template("Context : {context} | prd_text: {prd_text}")

        self.chain = (
            {"context": self.retriever, "prd_text": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def _create_chunks(self, text: str) -> List[str]:
        return self.text_splitter.split_text(text)

    def _store_in_chroma(self, chunks: List[str], metadatas: List[Dict[str, Any]]):
        """Append documents into Chroma collection"""
        documents = [
            Document(page_content=text, metadata=meta)
            for text, meta in zip(chunks, metadatas)
        ]
        self.db.add_documents(documents)

    def embed_text(self, text: str, source: str) -> Dict[str, Any]:
        chunks = self._create_chunks(text)
        metadatas = [{"id": str(uuid.uuid4()), "source": source} for _ in chunks]
        self._store_in_chroma(chunks, metadatas)
        
        return {
            "num_chunks": len(chunks),
            "persist_directory": self.persist_directory,
            "collection_name": self.collection_name,
        }

    def embed_pdf(self, pdf_bytes: bytes, source: str) -> Dict[str, Any]:
        pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
        text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
        
        chunks = self._create_chunks(text)
        metadatas = [{"id": str(uuid.uuid4()), "source": source} for _ in chunks]
        self._store_in_chroma(chunks, metadatas)
        
        return {
            "num_chunks": len(chunks),
            "persist_directory": self.persist_directory,
            "collection_name": self.collection_name,
        }

    async def get_response(self, prompt_text: str) -> str:
        response = await self.chain.ainvoke(prompt_text)
        return response

def get_embedding_service():
    return EmbeddingService()

import requests
from docx import Document
from dotenv import load_dotenv
import io
import os
import logging

logger = logging.getLogger(__name__)

load_dotenv()

class SupabaseService:
    SUPABASE_URL = os.getenv("SUPABASE_URL")

    @staticmethod
    async def download_file_content(file_url: str) -> str:
        try:
            logger.info(f"Downloading file content from {file_url}")
            if not file_url.startswith(SupabaseService.SUPABASE_URL):
                raise Exception("Invalid Supabase URL provided.")
            
            response = requests.get(file_url)
            response.raise_for_status()

            file_content = response.content

            if file_url.endswith(".docx"):
                doc_file = io.BytesIO(file_content)
                doc = Document(doc_file)
                full_text = []
                for para in doc.paragraphs:
                    full_text.append(para.text)
                return "\n".join(full_text)
                
            else:
                return file_content.decode('utf-8')

        except Exception as e:
            print(f"An error occurred: {e}")
            return None
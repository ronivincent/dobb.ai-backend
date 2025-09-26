import os
from enum import Enum
from typing import Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


class LLMProvider(Enum):
    GPT = ("GPT", ChatOpenAI, "OPENAI_API_KEY")
    GEMINI = ("GEMINI", ChatGoogleGenerativeAI, "GOOGLE_API_KEY")
    GROQ = ("GROQ", ChatGroq, "GROQ_API_KEY")

    @property
    def provider_name(self) -> str:
        return self.value[0]

    @property
    def model(self) -> str:
        return self.value[1]
    
    @property
    def api_key_tag(self) -> str:
        return self.value[2]
    

class LLMFactory:
    @staticmethod
    def create(provider: LLMProvider = LLMProvider.GPT, model_name: str = "gpt-3.5-turbo", **kwargs) -> Any:
        load_dotenv()
        api_key = os.getenv(provider.api_key_tag)
        return provider.model(model=model_name, api_key=api_key, **kwargs)
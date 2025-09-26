from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv

from config import LLMConfig

load_dotenv()

class PRDResponseService:
    def __init__(
        self,
        system_prompt: str = "You are an expert assistant. Answer concisely and clearly.",
    ):
        self.system_prompt = system_prompt
        self.llm = LLMConfig.LLM_PROVIDER

        self.prompt = ChatPromptTemplate.from_template(
            "SYSTEM: {system_prompt}\nPRD: {prd_text}"
        )

        self.chain = (
            {"system_prompt": RunnablePassthrough(), "prd_text": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    async def generate_response(self, prd_text: str) -> str:
        response = await self.chain.ainvoke({"system_prompt": self.system_prompt, "prd_text": prd_text})
        return response
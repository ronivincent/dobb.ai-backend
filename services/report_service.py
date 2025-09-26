import json
import re
import asyncio
from typing import Dict
from pydantic import BaseModel

from services.embedding_service import EmbeddingService
from services.prd_response_service import PRDResponseService
from data.templates.prompt import (
    PRD_SUMMARIZER_SYSTEM_PROMPT, 
    PRD_REFINER_SYSTEM_PROMPT, 
    IMPACTED_MODULES_SYSTEM_PROMPT, 
    TECH_IMPACT_SYSTEM_PROMPT,
    IDENTIFIED_GAPS_SYSTEM_PROMPT
)

from common.utils import parse_llm_json_response
from services.supabase_service import SupabaseService

class ReportRequest(BaseModel):
    prd_url: str

class ReportService:
    async def generate_report(self, prd_url: str) -> Dict:
        prd_text = await SupabaseService.download_file_content(prd_url)
        
        if not prd_text:
            return {"error": "PRD file empty"}

        tasks = {
            "summary": self._generate_prd_summary(prd_text),
            "refined_prd": self._generate_refined_prd(prd_text),
            "impacted_modules": self._generate_impacted_modules_report(prd_text),
            "technical_impacts": self._generate_technical_impact_report(prd_text),
            "identified_gaps": self._generate_identified_gaps_report(prd_text)
        }

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        results_dict = {}
        for key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                results_dict[key] = {"error": str(result)}
            else:
                results_dict[key] = result

        final_result = {
            **results_dict.get("summary"),
            "refined_prd": results_dict.get("refined_prd"),
            **results_dict.get("impacted_modules"),
            **results_dict.get("technical_impacts"),
            **results_dict.get("identified_gaps")
        }

        return final_result


    async def _generate_prd_summary(self, prd_text: str) -> Dict:
        response_service = PRDResponseService(PRD_SUMMARIZER_SYSTEM_PROMPT)
        llm_response = await response_service.generate_response(prd_text)
        json_response = parse_llm_json_response(llm_response)
        return json_response

    async  def _generate_refined_prd(self, prd_text: str) -> str:
        response_service = PRDResponseService(PRD_REFINER_SYSTEM_PROMPT)
        response = await response_service.generate_response(prd_text)
        return response

    async def _generate_impacted_modules_report(self, prd_text: str) -> Dict:
        embedding_service = EmbeddingService(prompt_messages=[
            ("system", IMPACTED_MODULES_SYSTEM_PROMPT),
            ("user", "Analyze the impact of the PRD."),
        ])
        llm_response = await embedding_service.get_response(prd_text)
        json_response = parse_llm_json_response(llm_response)
        return json_response 

    async def _generate_technical_impact_report(self, prd_text: str) -> Dict:
        embedding_service = EmbeddingService(prompt_messages=[
            ("system", TECH_IMPACT_SYSTEM_PROMPT),
            ("user", "Analyze the technical impacts of the PRD."),
        ])
        llm_response = await embedding_service.get_response(prd_text)
        json_response = parse_llm_json_response(llm_response)
        return json_response
    
    async def _generate_identified_gaps_report(self, prd_text: str) -> Dict:
        embedding_service = EmbeddingService(prompt_messages=[
            ("system", IDENTIFIED_GAPS_SYSTEM_PROMPT),
            ("user", "Identify the gaps of the PRD."),
        ])
        llm_response = await embedding_service.get_response(prd_text)
        json_response = parse_llm_json_response(llm_response)
        return json_response

    def _parse_llm_json(self, response: str) -> Dict:
        try:
            cleaned = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE).strip()
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            try:
                match = re.search(r"\[.*\]|\{.*\}", response, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
            except Exception:
                pass
            return {}


def get_report_service():
    return ReportService()
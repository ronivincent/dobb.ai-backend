from typing import Dict
import json
import re

def parse_llm_json_response(response: str) -> Dict:
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
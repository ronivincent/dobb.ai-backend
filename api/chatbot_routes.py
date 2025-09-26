# api/chatbot_routes.py
from fastapi import APIRouter, HTTPException
from chatbot.agent import chatbot_graph
from chatbot.models import ChatRequest, ChatResponse
from agents.refiner import refine_tool_result
from agents.orchestrator import orchestrate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        logger.info("Received chat request: %s", request.message)
        logger.info("Conversation history length: %d", len(request.history or []))
        
        # Convert history to the format expected by the agent
        conversation_history = []
        if request.history:
            for msg in request.history:
                conversation_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Add the current message
        conversation_history.append({
            "role": "user", 
            "content": request.message
        })
        
        # Try tool-orchestrated workflow first (Jira/GitHub MCP). If present, refine and append as context.
        tool_result = await orchestrate(request.message)
        logger.debug("Tool orchestrator result keys: %s", list(tool_result.keys()) if isinstance(tool_result, dict) else type(tool_result))
        extra_context = ""
        if tool_result and tool_result.get("output"):
            refined = refine_tool_result(tool_result, request.message)
            extra_context = refined or ""
            logger.info("Refined tool context: %s", extra_context)
            logger.info("Appended refined tool context length=%d", len(extra_context))

        # Pass the full conversation to the chatbot with refined extra context
        result = chatbot_graph.invoke({
            "input": request.message,
            "messages": conversation_history,
            "extra_context": extra_context
        })
        
        logger.info("Graph result: %s", result)
        
        if result is None:
            raise HTTPException(status_code=500, detail="Chatbot returned no response")
        
        if "output" not in result:
            raise HTTPException(status_code=500, detail="Chatbot response missing output field")
        
        # Extract sources if available
        sources = result.get("sources", [])
        logger.info("Returning response with %d sources", len(sources))
            
        return ChatResponse(reply=result["output"], sources=sources)
    except HTTPException:
        raise  # Re-raise HTTPExceptions as-is
    except Exception as e:
        logger.error("Error in chatbot: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}") from e

# chatbot/agent.py
from .prompt import chatbot_chain
import logging
from typing import Dict, Any, List
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


class ChatState(TypedDict):
    input: str
    output: str
    messages: List[Dict[str, Any]]


class SimpleChatbotGraph:
    """
    RAG-based chatbot that uses ChromaDB retriever and chain pattern.
    Similar to embedding service but for Q&A instead of report generation.
    """
    
    def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke the chatbot with RAG context using the chain pattern.
        """
        try:
            user_message = state.get("input", "")
            
            if not user_message:
                logger.warning("No input message provided")
                return {
                    "output": "Sorry, I didn't receive any message to respond to."
                }
            
            logger.info("Processing user message: %s", user_message[:100] + "..." if len(user_message) > 100 else user_message)
            
            # Use the chain to get response with RAG context from ChromaDB
            extra_context = state.get("extra_context", "")
            result = chatbot_chain(user_message, extra_context)
            
            if not result or not result.get("answer"):
                logger.error("Chain response is None or missing answer")
                return {
                    "output": "Sorry, I'm having trouble generating a response right now.",
                    "sources": []
                }
            
            logger.info("Chain response: %s", result["answer"][:100] + "..." if len(result["answer"]) > 100 else result["answer"])
            logger.info("Retrieved %d sources", len(result.get("sources", [])))
            
            return {
                "output": result["answer"],
                "sources": result.get("sources", [])
            }
        
        except Exception as e:  # pylint: disable=broad-except
            logger.error("Error in chatbot: %s", str(e))
            return {
                "output": f"Sorry, I encountered an error: {str(e)}",
                "sources": []
            }


# Create simplified chatbot graph using chain pattern
chatbot_graph = SimpleChatbotGraph()

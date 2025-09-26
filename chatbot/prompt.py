# chatbot/prompt.py
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
# Removed unused imports - using custom RAG function instead of chain
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from config import settings, LLMConfig
import logging

logger = logging.getLogger(__name__)

# Validate Google API key
if not settings.GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY not found in environment variables. Please set it in your .env file.")
    raise ValueError("GOOGLE_API_KEY is required for the chatbot to function")

def initialize_rag_components():
    """
    Initialize ChromaDB retriever and LLM for RAG-based chatbot.
    Similar to embedding service but for Q&A.
    """
    try:
        # Initialize embeddings (same as embedding service)
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )
        
        # Initialize ChromaDB (same configuration as embedding service)
        persist_directory = os.getenv("CHROMA_DB_DIRECTORY_PATH", "./data/db")
        collection_name = "default_collection"
        
        db = Chroma(
            collection_name=collection_name,
            persist_directory=persist_directory,
            embedding_function=embeddings,
        )
        
        # Create retriever
        db_retriever = db.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}  # Retrieve top 3 most relevant chunks
        )
        
        # Initialize LLM
        # gemini_llm = ChatGoogleGenerativeAI(
        #     model="gemini-1.5-flash",
        #     temperature=0.3,  # Lower temperature for more focused responses
        #     max_output_tokens=2048,  # Increased for detailed explanations
        #     google_api_key=settings.GOOGLE_API_KEY,
        # )

        groq_llm = LLMConfig.LLM_PROVIDER
        
        logger.info("RAG components initialized successfully")
        logger.info("ChromaDB path: %s, Collection: %s", persist_directory, collection_name)
        
        return db_retriever, groq_llm
    
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Failed to initialize RAG components: %s", str(e))
        raise

# Initialize RAG components
retriever, llm = initialize_rag_components()

# Create prompt template for RAG-based Q&A
chat_prompt = ChatPromptTemplate.from_template("""You are an AI assistant for TechStore, a modern e-commerce platform that sells gadgets and technical items. Your role is to help onboard new team members by answering any questions related to the product, including its features, functionality, user experience, and business value.

Overview: TechStore is a complete online shopping solution where customers can browse and purchase gadgets and other technical items. The platform provides a smooth, responsive, and secure shopping experience, with fully implemented features up to Phase 3 development.

Key Capabilities:
- Browsable product catalog with images, prices, stock status, and detailed descriptions
- Shopping cart with item addition/removal, quantity updates, real-time totals, and order placement
- User accounts with sign-up, login, profile management, and order history tracking
- Seamless design across mobile and desktop devices
- Secure order management ensuring users can only access their own data
- Features and workflows fully implemented through Phase 3, including product display, account management, and core shopping functions

RETRIEVED CONTEXT:
{context}

Your Goal:
- Provide clear, accurate, and detailed answers to any question about TechStore based on the retrieved context
- Explain features, workflows, and business value in simple terms for new team members
- Highlight how the platform benefits customers and improves the shopping experience
- Use the retrieved context to provide specific and accurate information about the platform
- Avoid unnecessary deep technical details unless specifically asked
- Always answer in a helpful, professional, and easy-to-understand tone

Instructions:
1. Base your answers ONLY on the retrieved context from the knowledge base
2. If the retrieved context doesn't contain enough information, say "I don't have enough information in my knowledge base to answer that specific question about TechStore."
3. Focus on explaining features, workflows, and business benefits for team members and end users
4. For technical questions, provide explanations that are understandable for new team members unless deep technical details are specifically requested
5. If the user asked to create a ticket in jira, check the retrieved context to know the whether the ticket is already created or not. If it is already created, then say that the ticket/bug/task is already created. If it is not created, then say that the ticket/bug/task is not created.

User Question: {user_input}

Answer based on the retrieved context about TechStore:""")


def format_docs_with_sources(docs):
    """Format documents and extract source information"""
    formatted_context = "\n\n".join([doc.page_content for doc in docs])
    sources = []
    for i, doc in enumerate(docs):
        source_info = {
            "chunk_id": i + 1,
            "source": doc.metadata.get("source", "Unknown"),
            "content_preview": doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
        }
        sources.append(source_info)
    return formatted_context, sources

def rag_with_sources(query: str, extra_context: str = ""):
    """RAG function that returns both answer and sources"""
    try:
        # Retrieve documents
        docs = retriever.get_relevant_documents(query)
        
        # Format context and extract sources
        context, sources = format_docs_with_sources(docs)
        if extra_context:
            context = context + "\n\n" + extra_context
        
        # Generate response using the prompt template
        formatted_prompt = chat_prompt.format(context=context, user_input=query)
        response = llm.invoke(formatted_prompt)
        
        return {
            "answer": response.content,
            "sources": sources,
            "context": context
        }
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error in RAG with sources: %s", str(e))
        return {
            "answer": f"Sorry, I encountered an error: {str(e)}",
            "sources": [],
            "context": ""
        }

# Create the RAG chain with sources
chatbot_chain = rag_with_sources
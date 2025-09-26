from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from services.embedding_service import EmbeddingService, get_embedding_service


router = APIRouter(prefix="/embedding", tags=["Embeddings"])


@router.post("/text")
async def create_text_embedding(
    file: UploadFile = File(...),
    service: EmbeddingService = Depends(get_embedding_service),
):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported")

    content = await file.read()
    text = content.decode("utf-8")

    result = service.embed_text(text, source=file.filename)
    return {"filename": file.filename, **result}


@router.post("/pdf")
async def create_pdf_embedding(
    file: UploadFile = File(...),
    service: EmbeddingService = Depends(get_embedding_service),
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are supported")

    pdf_bytes = await file.read()
    result = service.embed_pdf(pdf_bytes, source=file.filename)
    return {"filename": file.filename, **result}

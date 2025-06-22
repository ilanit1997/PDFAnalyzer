from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from uuid import uuid4
import shutil
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from core.document_pipeline import DocumentPipelineManager
from core.action_generator import ACTION_GENERATORS, actions_for_other

###### Load shared components and initialize FastAPI app ######
app = FastAPI()
documents_db = {}

# Load shared components
LABELS_WITH_DESCRIPTIONS = {
    "Invoice": "A bill for goods or services, typically including vendor, amount, due date, and line items.",
    "Contract": "A legal agreement between parties, containing terms, dates, and responsibilities.",
    "Earnings": "A financial or business report summarizing revenue, profits, expenses, and other key metrics.",
    "Other": "Any other type of document that does not fit the above categories."
}
pipeline = DocumentPipelineManager()


class DocumentEntry(BaseModel):
    id: str = Field(..., description="A unique identifier for the uploaded document.")

    classification: Dict[str, Any] = Field(
        ...,
        description="""
The classification for the document, including:
- 'type': the predicted document type ('Invoice', 'Contract', 'Earnings' or 'Other')
- 'confidence': a score between 0 and 1 indicating model certainty
"""
    )

    metadata: Dict[str, Any] = Field(
        ...,
        description="""
Structured metadata fields extracted from the document, tailored to the document type.
For example:
- Invoice → vendor, amount, due date, line items
- Contract → parties, effective/termination dates, key terms
- Earnings Report → reporting period, key metrics, executive summary
- Other → summary
"""
    )

class DocumentAction(BaseModel):
    type: str
    description: str
    deadline: str | None = None
    priority: str | None = "medium"

@app.post("/documents/analyze")
async def analyze_document(file: UploadFile = File(...)):
    try:
        tmp_path = Path("tmp") / file.filename
        tmp_path.parent.mkdir(exist_ok=True)
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        pages = pipeline.load_document(str(tmp_path))
        classification_result = pipeline.classify(pages)
        metadata_result = pipeline.extract_metadata(pages, classification_result["type"])

        doc_id = str(uuid4())
        entry = DocumentEntry(
            id=doc_id,
            classification=classification_result,
            metadata=metadata_result.model_dump() if hasattr(metadata_result, "model_dump") else metadata_result,
        )
        documents_db[doc_id] = entry

        return {
            "status": "success",
            "document_id": doc_id,
            "classification": entry.classification,
            "metadata": entry.metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")

@app.get("/documents/{id}", response_model=DocumentEntry)
def get_document(id: str):
    doc = documents_db.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@app.get("/documents/{id}/actions", response_model=List[DocumentAction])
def get_actions(
    id: str,
    priority: Optional[str] = Query(None, description="Filter actions by priority (e.g., high, medium, low)"),
):
    doc = documents_db.get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_type = doc.classification.get("type")
    generator = ACTION_GENERATORS.get(doc_type, actions_for_other)
    actions = generator(doc.metadata)

    # Apply optional filters
    if priority:
        actions = [a for a in actions if a.get("priority") == priority]

    return actions

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)

from pydantic import BaseModel

class SparesUploadResponse(BaseModel):
    message: str
    total_records: int
    processed: int
    inserted_or_updated: int

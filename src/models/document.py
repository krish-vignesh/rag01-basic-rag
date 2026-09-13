import uuid #universally unique identifier
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class document(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4())) #Creates a unique identifier for each document instance
    company_id: str 
    file_name: str
    file_type: str
    version: int
    source: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) #Sets the creation time of the document instance to the current UTC time
    #default_factory is a callable that generates a default value for the field when an instance of the model is created. In this case, it generates a unique identifier for each document instance using the uuid.uuid4() function, and sets the creation time to the current UTC time using datetime.now(timezone.utc).
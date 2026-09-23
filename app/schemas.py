from pydantic import BaseModel, Field


class PromptIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=20000)
    tags: str = ""
    remark: str = ""


class PromptOut(PromptIn):
    id: int

    class Config:
        from_attributes = True

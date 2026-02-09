from pydantic import BaseModel

class CS2DemoUrlResponse(BaseModel):
    match_code: str
    match_id: int
    outcome_id: int
    token: int
    demo_url: str | None = None
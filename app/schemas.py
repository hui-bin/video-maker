from pydantic import BaseModel

class VideoRequest(BaseModel):
    input_content: str
    is_url: bool = False
    schedule_time: str = "2025-02-26 22:00:00"

class SceneScript(BaseModel):
    description: str
    narration: str
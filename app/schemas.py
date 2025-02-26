from pydantic import BaseModel

class VideoRequest(BaseModel):
    input_content: str
    is_url: bool = False
    # schedule_time: str = None

class SceneScript(BaseModel):
    description: str
    narration: str
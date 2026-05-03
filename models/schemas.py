from pydantic import BaseModel
from datetime import datetime


class TZData(BaseModel):
    goal: str
    audience: str
    features: str
    tech_constraints: str
    desired_result: str


class UserProfile(BaseModel):
    user_id: int
    username: str | None
    first_seen: datetime
    last_activity: datetime
    total_tzs: int = 0

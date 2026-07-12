from pydantic import BaseModel, Field, field_validator


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    age: int = Field(ge=5, le=100)
    gender: str = Field(min_length=1, max_length=30)
    state: str = Field(min_length=2, max_length=100)
    sport: str = Field(min_length=2, max_length=100)
    experience: int = Field(ge=0, le=80)

    @field_validator("name", "gender", "state", "sport")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Field must not be blank")
        return normalized


class ProfileResponse(BaseModel):
    name: str
    age: int
    gender: str
    state: str
    sport: str
    experience: int

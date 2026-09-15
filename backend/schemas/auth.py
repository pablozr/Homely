from pydantic import BaseModel, field_validator


class LoginRequestModel(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


def user_from_row(row) -> dict:
    created_at = row["created_at"]

    return {
        "id": row["id"],
        "fullname": row["fullname"],
        "email": row["email"],
        "role": row["role"],
        "created_at": created_at.isoformat() if created_at else None,
    }

from pydantic import BaseModel, Field, field_validator


class MagicLinkRequestModel(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        local, separator, domain = email.partition("@")

        if not separator or not local or not domain or " " in email:
            raise ValueError("Invalid email")

        return email


class ExchangeRequestModel(BaseModel):
    auth_code: str = Field(min_length=1)


class RefreshTokenRequestModel(BaseModel):
    refresh_token: str = Field(min_length=1)


def user_from_row(row) -> dict:
    created_at = row["created_at"]

    return {
        "id": row["id"],
        "fullname": row["fullname"],
        "email": row["email"],
        "role": row["role"],
        "profile_completed": row["profile_completed_at"] is not None,
        "created_at": created_at.isoformat() if created_at else None,
    }

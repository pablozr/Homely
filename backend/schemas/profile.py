from pydantic import BaseModel, Field, field_validator


class ProfileUpdateRequestModel(BaseModel):
    fullname: str = Field(min_length=1, max_length=255)

    @field_validator("fullname", mode="before")
    @classmethod
    def normalize_fullname(cls, value):
        if not isinstance(value, str):
            return value

        return value.strip()


def initials_from_fullname(fullname: str) -> str:
    parts = fullname.split()

    if len(parts) == 1:
        return parts[0][0].upper()

    return (parts[0][0] + parts[-1][0]).upper()


def profile_from_row(row) -> dict:
    created_at = row["created_at"]
    fullname = row["fullname"]

    return {
        "id": row["id"],
        "fullname": fullname,
        "initials": initials_from_fullname(fullname),
        "role": row["role"],
        "profile_completed": row["profile_completed_at"] is not None,
        "created_at": created_at.isoformat() if created_at else None,
    }

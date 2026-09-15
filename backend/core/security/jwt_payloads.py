import asyncpg


def auth_jwt_payload_from_row(row: asyncpg.Record) -> dict:
    return {
        "userId": str(row["id"]),
        "email": row["email"],
        "fullname": row["fullname"],
        "role": row["role"],
        "type": "auth",
    }

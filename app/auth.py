import jwt
from jwt import PyJWTError

from app.config import settings


def decode_token(token: str) -> dict:
    """解码并验证 JWT token，返回 payload。"""
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def get_user_id_from_payload(payload: dict) -> str | None:
    """从 JWT payload 中提取用户标识。

    根据你另一个项目的 token 结构调整这里的 key，常见如 sub / user_id / id。
    """
    return payload.get("sub") or payload.get("user_id") or payload.get("id")

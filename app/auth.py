import logging

import jwt
from jwt import PyJWTError

from app.config import settings

logger = logging.getLogger(__name__)


def decode_token(token: str) -> dict:
    """解码并验证 JWT token，返回 payload。

    JWT 的受众声明（RFC 8707 Resource Indicators）：
    - 令牌带 aud 时必须等于本 MCP 服务的 resource 标识，否则拒绝；
    - 令牌不带 aud 说明是存量令牌，过渡期记录日志后放行，等自然过期后收紧。

    注意：PyJWT 在 audience 参数缺省、而令牌自带 aud 时会直接判定失败，
    因此这里关闭内置校验（verify_aud=False），转为显式处理。
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_aud": False},
        )
    except PyJWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    audience = payload.get("aud")
    if isinstance(audience, str):
        audience = [audience]

    if audience:
        if settings.mcp_resource not in audience:
            raise ValueError("Invalid token audience")
    else:
        # 过渡期：存量令牌尚未携带 aud（详见 decode_token 文档字符串）
        logger.warning(
            "accepted legacy token without aud claim (sub=%s)", payload.get("sub")
        )

    return payload


def get_user_id_from_payload(payload: dict) -> str | None:
    """从 JWT payload 中提取用户标识。

    根据你另一个项目的 token 结构调整这里的 key，常见如 sub / user_id / id。
    """
    return payload.get("sub") or payload.get("user_id") or payload.get("id")

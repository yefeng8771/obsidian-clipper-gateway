"""
Local REST API 兼容层
============================================================

让任何使用 obsidian-local-rest-api 协议的客户端（如
greasyfork/561785：Linux.do → Obsidian）直接指向本服务，
无需在本地安装 Obsidian + Local REST API 插件。

协议参考：https://coddingtonbear.github.io/obsidian-local-rest-api/

写入路径：所有内容透传给 fast-note-sync-service（唯一存储 + 同步）。
            本地不再落盘，避免与 FNS 形成 split-brain。
"""
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import CONFIG

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

FNS_URL    = (CONFIG.get("fns_url") or "").rstrip("/")
FNS_TOKEN  = CONFIG.get("fns_token") or ""
FNS_VAULT  = CONFIG.get("fns_vault", "Inbox")

# ---------- 鉴权（与 web_clipper.verify_token 等价，避免循环 import） ----------
async def verify_token(creds: HTTPAuthorizationCredentials = Depends(security)):
    if creds.credentials != CONFIG.get("api_key"):
        raise HTTPException(401, "Invalid token", {"WWW-Authenticate": "Bearer"})
    return creds.credentials


# ---------- 工具函数 ----------
def _is_markdown(ctype: str) -> bool:
    if not ctype:
        return False
    main = ctype.split(";")[0].strip().lower()
    return main in ("text/markdown", "text/plain", "application/markdown")


def _ensure_fns_configured():
    if not FNS_URL or not FNS_TOKEN:
        raise HTTPException(503, "fast-note-sync 未配置：请检查 FNS_URL / FNS_TOKEN")


async def _list_from_fns() -> list[str]:
    _ensure_fns_configured()
    headers = {"Authorization": f"Bearer {FNS_TOKEN}"}
    async with httpx.AsyncClient(headers=headers, timeout=15) as c:
        r = await c.get(
            f"{FNS_URL}/api/notes",
            params={"vault": FNS_VAULT},
        )
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return r.json().get("files", [])


# ---------- 端点：Local REST API 兼容 ----------
@router.get("/")
async def server_status(_: str = Depends(verify_token)):
    """脚本通常会先 ping / 看看是不是活着"""
    return {
        "authenticated": True,
        "ok":      "true",
        "service": "obsidian-clipper-gateway",
        "versions": {"obsidian-local-rest-api": "1.0.0-compat"},
    }


@router.get("/vault/")
async def vault_list(_: str = Depends(verify_token)):
    files = await _list_from_fns()
    return {"files": files}

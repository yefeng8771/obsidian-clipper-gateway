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
import asyncio
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import CONFIG

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

FNS_URL    = (CONFIG.get("fns_url") or "").rstrip("/")
FNS_TOKEN  = CONFIG.get("fns_token") or ""
FNS_VAULT  = CONFIG.get("fns_vault", "Inbox")
AI_ENRICH  = bool(CONFIG.get("vault_ai_enrich"))
NOTIFY     = bool(CONFIG.get("vault_notify"))


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


async def _enrich_frontmatter(md: bytes) -> bytes:
    """可选 AI 富化：在无 frontmatter 的 markdown 顶部注入 summary+tags"""
    if not AI_ENRICH:
        return md
    import web_clipper as wc  # 延迟引用，避免循环
    if wc.handler is None:
        return md
    text = md.decode("utf-8", errors="replace")
    if text.lstrip().startswith("---"):
        return md
    try:
        loop = asyncio.get_running_loop()
        summary, tags = await loop.run_in_executor(
            None, wc.handler.generate_summary_tags, text
        )
        fm = (
            "---\n"
            f"summary: {summary}\n"
            f"tags: [{', '.join(tags)}]\n"
            "---\n\n"
        )
        return fm.encode("utf-8") + md
    except Exception as e:
        logger.warning(f"AI 富化失败，按原文保存: {e}")
        return md


async def _write_to_fns(filepath: str, body: bytes, ctype: str, append: bool):
    """转发到 fast-note-sync。失败抛 HTTPException 让客户端重试。"""
    _ensure_fns_configured()
    headers = {"Authorization": f"Bearer {FNS_TOKEN}"}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=30) as c:
            if _is_markdown(ctype):
                r = await c.put(
                    f"{FNS_URL}/api/note",
                    json={
                        "vault":     FNS_VAULT,
                        "path":      filepath,
                        "content":   body.decode("utf-8"),
                        "append":    append,
                        "overwrite": not append,
                    },
                )
            else:
                r = await c.post(
                    f"{FNS_URL}/api/attachment",
                    files={
                        "file": (
                            Path(filepath).name,
                            body,
                            ctype or "application/octet-stream",
                        )
                    },
                    data={"vault": FNS_VAULT, "path": filepath},
                )
            r.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"FNS 写入失败 {filepath}: {e}")
        raise HTTPException(502, f"fast-note-sync 写入失败: {e}")


async def _read_from_fns(filepath: str) -> tuple[bytes, str] | None:
    """从 FNS 读笔记内容，404 返回 None"""
    _ensure_fns_configured()
    headers = {"Authorization": f"Bearer {FNS_TOKEN}"}
    async with httpx.AsyncClient(headers=headers, timeout=15) as c:
        r = await c.get(
            f"{FNS_URL}/api/note",
            params={"vault": FNS_VAULT, "path": filepath},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        content = data.get("content", "")
        return content.encode("utf-8"), "text/markdown"


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


async def _maybe_notify(filepath: str, action: str):
    if not NOTIFY:
        return
    import web_clipper as wc
    if wc.handler is None:
        return
    try:
        await wc.handler.send_telegram_notification(f"📝 vault {action}: {filepath}")
    except Exception as e:
        logger.warning(f"Telegram 通知失败: {e}")


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


@router.get("/vault/{filepath:path}")
async def vault_get(filepath: str, _: str = Depends(verify_token)):
    result = await _read_from_fns(filepath)
    if result is None:
        raise HTTPException(404, "Not found")
    body, ctype = result
    if ctype.startswith("text/"):
        return PlainTextResponse(body.decode("utf-8"), media_type=ctype)
    return Response(body, media_type=ctype)


@router.put("/vault/{filepath:path}")
async def vault_put(
    filepath: str, request: Request, _: str = Depends(verify_token)
):
    body  = await request.body()
    ctype = request.headers.get("content-type", "")
    if _is_markdown(ctype):
        body = await _enrich_frontmatter(body)
    await _write_to_fns(filepath, body, ctype, append=False)
    await _maybe_notify(filepath, "PUT")
    return Response(status_code=204)


@router.post("/vault/{filepath:path}")
async def vault_post(
    filepath: str, request: Request, _: str = Depends(verify_token)
):
    """Local REST API 语义：文件存在则追加 markdown，不存在则等价于 PUT"""
    body  = await request.body()
    ctype = request.headers.get("content-type", "")

    is_append = False
    if _is_markdown(ctype):
        existing = await _read_from_fns(filepath)
        is_append = existing is not None
        if not is_append:
            body = await _enrich_frontmatter(body)

    await _write_to_fns(filepath, body, ctype, append=is_append)
    await _maybe_notify(filepath, "POST/append" if is_append else "POST/create")
    return Response(status_code=204)


@router.delete("/vault/{filepath:path}")
async def vault_delete(filepath: str, _: str = Depends(verify_token)):
    _ensure_fns_configured()
    headers = {"Authorization": f"Bearer {FNS_TOKEN}"}
    async with httpx.AsyncClient(headers=headers, timeout=15) as c:
        r = await c.delete(
            f"{FNS_URL}/api/note",
            params={"vault": FNS_VAULT, "path": filepath},
        )
        if r.status_code not in (200, 204, 404):
            r.raise_for_status()
    await _maybe_notify(filepath, "DELETE")
    return Response(status_code=204)

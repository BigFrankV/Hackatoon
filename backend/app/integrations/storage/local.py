from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path, PurePosixPath
from uuid import uuid4

from app.integrations.contracts import StoredObject


class LocalPrivateDocumentStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, object_key: str) -> Path:
        relative = PurePosixPath(object_key)
        if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
            raise ValueError("Invalid private object key")
        path = (self.root.joinpath(*relative.parts)).resolve()
        if os.path.commonpath((str(self.root), str(path))) != str(self.root):
            raise ValueError("Object key escapes private storage root")
        return path

    async def put(self, object_key: str, content: bytes, media_type: str) -> StoredObject:
        return await asyncio.to_thread(self._put, object_key, content, media_type)

    def _put(self, object_key: str, content: bytes, media_type: str) -> StoredObject:
        if not content:
            raise ValueError("Private files cannot be empty")
        destination = self._resolve(object_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        try:
            temporary.write_bytes(content)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return StoredObject(
            object_key=object_key,
            sha256=hashlib.sha256(content).hexdigest(),
            byte_size=len(content),
            media_type=media_type,
        )

    async def get(self, object_key: str) -> bytes:
        return await asyncio.to_thread(self._resolve(object_key).read_bytes)

    async def delete(self, object_key: str) -> None:
        await asyncio.to_thread(self._resolve(object_key).unlink, missing_ok=True)

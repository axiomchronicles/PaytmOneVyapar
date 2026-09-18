from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    async def put(self, key: str, content: bytes, *, content_type: str) -> str: ...


class LocalDevelopmentObjectStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    async def put(self, key: str, content: bytes, *, content_type: str) -> str:
        destination = (self.root / key).resolve()
        if self.root not in destination.parents:
            raise ValueError("Object key escapes the configured storage root")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return str(destination)

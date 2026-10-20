"""Replace text only after writing it completely; no locking or transaction guarantees."""

import os
import tempfile
from pathlib import Path


def write_text(path: Path, text: str) -> None:
    # Same-directory staging keeps replacement on one filesystem.
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)

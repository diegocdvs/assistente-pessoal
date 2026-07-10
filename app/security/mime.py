from __future__ import annotations

EXECUTABLE_MIME_TYPES = {
    "application/x-msdownload",
    "application/x-msdos-program",
    "application/x-ms-installer",
    "application/x-sh",
    "application/javascript",
    "text/javascript",
}


def is_executable_mime(value: str) -> bool:
    return value.lower().split(";", 1)[0].strip() in EXECUTABLE_MIME_TYPES

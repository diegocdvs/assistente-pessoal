from __future__ import annotations

from pathlib import Path
from typing import Any

from app.security.mime import is_executable_mime
from app.security.models import AttachmentAssessment

EXECUTABLE_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".scr", ".ps1", ".vbs", ".js", ".jar", ".msi", ".com", ".pif", ".lnk"
}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv"}


class AttachmentAnalyzer:
    def analyze_many(self, attachments: list[dict[str, Any]]) -> list[AttachmentAssessment]:
        return [self.analyze(attachment) for attachment in attachments]

    def analyze(self, attachment: dict[str, Any]) -> AttachmentAssessment:
        filename = str(attachment.get("filename") or attachment.get("name") or "")
        mime_type = attachment.get("mime_type") or attachment.get("mimeType") or attachment.get("content_type")
        size_bytes = attachment.get("size_bytes") or attachment.get("size") or attachment.get("sizeEstimate")
        suffixes = [suffix.lower() for suffix in Path(filename).suffixes]
        extension = suffixes[-1] if suffixes else None
        reasons: list[str] = []

        has_double_extension = len(suffixes) > 1 and suffixes[-2] in DOCUMENT_EXTENSIONS
        if has_double_extension:
            reasons.append("double_extension")

        is_executable = bool(extension in EXECUTABLE_EXTENSIONS or is_executable_mime(str(mime_type or "")))
        if is_executable:
            reasons.append("executable_attachment")

        if not filename:
            reasons.append("missing_filename")

        return AttachmentAssessment(
            filename=filename,
            extension=extension,
            mime_type=str(mime_type) if mime_type else None,
            size_bytes=int(size_bytes) if str(size_bytes or "").isdigit() else None,
            suspicious=bool(reasons),
            risk_reasons=reasons,
            has_double_extension=has_double_extension,
            is_executable=is_executable,
        )

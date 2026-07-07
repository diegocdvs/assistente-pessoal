from __future__ import annotations

from google.cloud import secretmanager


class SecretReader:
    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()

    def read_text(self, name: str) -> str:
        resource = f"projects/{self.project_id}/secrets/{name}/versions/latest"
        response = self.client.access_secret_version(request={"name": resource})
        return response.payload.data.decode("utf-8")

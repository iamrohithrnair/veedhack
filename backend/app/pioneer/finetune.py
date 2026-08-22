import asyncio
from email.utils import parsedate_to_datetime
from typing import Any

import httpx


class PioneerError(RuntimeError):
    """Raised when Pioneer rejects or fails an operation."""


class PioneerClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.pioneer.ai",
        timeout: float = 120,
    ) -> None:
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    async def __aenter__(self) -> "PioneerClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.client.aclose()

    @staticmethod
    def _retry_seconds(value: str | None, attempt: int) -> float:
        if value:
            try:
                return max(0, float(value))
            except ValueError:
                try:
                    from datetime import UTC, datetime

                    return max(0, (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds())
                except (TypeError, ValueError):
                    return min(2 ** attempt, 60)
        return min(2 ** attempt, 60)

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        retries: int = 6,
    ) -> dict[str, Any]:
        for attempt in range(retries + 1):
            response = await self.client.request(method, path, json=json)
            if response.status_code in {402, 403}:
                raise PioneerError(f"Pioneer rejected the request ({response.status_code}): {response.text}")
            if response.status_code in {429, 502, 503, 504} and attempt < retries:
                await asyncio.sleep(self._retry_seconds(response.headers.get("Retry-After"), attempt))
                continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise PioneerError(
                    f"Pioneer request failed ({response.status_code}) at {path}: {response.text}"
                ) from error
            payload = response.json()
            if not isinstance(payload, dict):
                raise PioneerError(f"Pioneer returned non-object JSON at {path}")
            return payload
        raise PioneerError("Pioneer rate limit retry budget exhausted")

    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "/generate", json=payload)

    async def inference(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "/inference", json=payload)

    async def get_generation_job(self, job_id: str) -> dict[str, Any]:
        return await self.request("GET", f"/generate/jobs/{job_id}")

    async def poll_job(
        self,
        job_id: str,
        *,
        interval: float = 3,
        timeout: float = 1800,
    ) -> dict[str, Any]:
        terminal_success = {"completed", "succeeded", "ready", "finished", "complete"}
        terminal_failure = {"failed", "cancelled", "canceled", "error", "errored"}
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            job = await self.get_generation_job(job_id)
            state = str(job.get("status") or job.get("state") or "").lower()
            if state in terminal_success:
                return job
            if state in terminal_failure:
                raise PioneerError(f"Pioneer job {job_id} ended with status {state}: {job}")
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Timed out waiting for Pioneer job {job_id}")
            await asyncio.sleep(interval)

    async def dataset(self, dataset_name: str) -> dict[str, Any]:
        return await self.request("GET", f"/felix/datasets/{dataset_name}")

    async def launch_training(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "/felix/training-jobs", json=payload)

    async def poll_training(
        self, job_id: str, *, interval: float = 5, timeout: float = 7200
    ) -> dict[str, Any]:
        return await self._poll_path(
            f"/felix/training-jobs/{job_id}",
            job_id,
            success={"complete", "completed", "succeeded"},
            failure={"failed", "stopped", "errored", "error"},
            interval=interval,
            timeout=timeout,
        )

    async def launch_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "/felix/evaluations", json=payload)

    async def poll_evaluation(
        self, evaluation_id: str, *, interval: float = 5, timeout: float = 3600
    ) -> dict[str, Any]:
        return await self._poll_path(
            f"/felix/evaluations/{evaluation_id}",
            evaluation_id,
            success={"complete", "completed", "succeeded"},
            failure={"failed", "errored", "error"},
            interval=interval,
            timeout=timeout,
        )

    async def label_existing_ner(
        self,
        labels: list[str],
        inputs: list[str],
        **extra: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"labels": labels, "inputs": inputs}
        payload.update({key: value for key, value in extra.items() if value is not None})
        return await self.request("POST", "/generate/ner/label-existing", json=payload)

    async def upload_ner_jsonl(self, dataset_name: str, jsonl: str) -> dict[str, Any]:
        meta = await self.request(
            "POST",
            "/felix/datasets/upload/url",
            json={
                "dataset_name": dataset_name,
                "dataset_type": "ner",
                "format": "jsonl",
                "filename": f"{dataset_name}.jsonl",
                "generation_type": "upload",
                "type": "training",
                "column_mapping": {"text": "text", "entities": "entities"},
            },
        )
        url = meta.get("presigned_url")
        if not isinstance(url, str) or not url:
            raise PioneerError(f"Pioneer upload URL response missing presigned_url: {meta}")
        async with httpx.AsyncClient(timeout=120) as raw:
            put = await raw.put(
                url,
                content=jsonl.encode("utf-8"),
                headers={"Content-Type": "application/octet-stream"},
            )
            try:
                put.raise_for_status()
            except httpx.HTTPStatusError as error:
                raise PioneerError(
                    f"Pioneer dataset upload PUT failed ({put.status_code}): {put.text}"
                ) from error
        processed = await self.request(
            "POST",
            "/felix/datasets/upload/process",
            json={"dataset_id": str(meta.get("dataset_id") or "")},
        )
        processed.setdefault("dataset_name", meta.get("dataset_name") or dataset_name)
        processed.setdefault("version_number", meta.get("version_number"))
        return processed

    async def label_existing_classification(
        self,
        labels: list[str],
        inputs: list[str],
        **extra: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"labels": labels, "inputs": inputs}
        payload.update({key: value for key, value in extra.items() if value is not None})
        return await self.request(
            "POST",
            "/generate/classification/label-existing",
            json=payload,
        )

    async def _poll_path(
        self,
        path: str,
        resource_id: str,
        *,
        success: set[str],
        failure: set[str],
        interval: float,
        timeout: float,
    ) -> dict[str, Any]:
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            result = await self.request("GET", path)
            state = str(result.get("status") or result.get("state") or "").lower()
            if state in success:
                return result
            if state in failure:
                raise PioneerError(f"Pioneer resource {resource_id} ended with {state}: {result}")
            if asyncio.get_running_loop().time() >= deadline:
                raise TimeoutError(f"Timed out waiting for Pioneer resource {resource_id}")
            await asyncio.sleep(interval)

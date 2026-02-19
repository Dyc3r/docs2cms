import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SyncFailure:
    doc_path: str
    content_type: str | None
    wordpress_id: int | None
    error_summary: str


class SyncReport:
    def __init__(self) -> None:
        self._failures: list[SyncFailure] = []

    def record_failure(
        self,
        doc_path: str,
        content_type: str | None,
        wordpress_id: int | None,
        error: Exception,
    ) -> None:
        self._failures.append(
            SyncFailure(
                doc_path=doc_path,
                content_type=content_type,
                wordpress_id=wordpress_id,
                error_summary=str(error),
            )
        )

    @property
    def has_failures(self) -> bool:
        return bool(self._failures)

    @property
    def failure_count(self) -> int:
        return len(self._failures)

    def write_csv(self, output_path: Path) -> None:
        with output_path.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["doc_path", "content_type", "wordpress_id", "error_summary"],
            )
            writer.writeheader()
            for failure in self._failures:
                writer.writerow({
                    "doc_path": failure.doc_path,
                    "content_type": failure.content_type or "",
                    "wordpress_id": failure.wordpress_id if failure.wordpress_id is not None else "",
                    "error_summary": failure.error_summary,
                })

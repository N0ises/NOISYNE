from __future__ import annotations


class ProgressPrinter:

    def update(
        self,
        index: int,
        total: int,
        filename: str,
    ) -> None:

        print(
            f"[{index}/{total}] {filename}"
        )
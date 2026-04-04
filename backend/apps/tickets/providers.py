from __future__ import annotations

from pathlib import Path

from apps.tickets.services.generation_service import (
    GenerationConfig,
    GenerationResult,
    generate_dataset,
)


class GeneratedTicketProvider:
    def __init__(self, *, data_dir: Path):
        self.data_dir = Path(data_dir)

    def generate(self, config: GenerationConfig) -> GenerationResult:
        return generate_dataset(config, data_dir=self.data_dir)

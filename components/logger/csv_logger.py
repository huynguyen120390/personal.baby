class CsvLogger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "timestamp_utc",
                    "source",
                    "people_count",
                    "person_present",
                    "prompt",
                    "gpt_model",
                    "detail",
                    "description",
                ])

    def append(self, *, source: str, people_count: int, person_present: bool,
               prompt: str, gpt_model: str, detail: str, description: str):
        with self.path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                utc_now_iso(),
                source,
                people_count,
                int(person_present),
                prompt.strip().replace("\r\n", "\n"),
                gpt_model,
                detail,
                description.strip().replace("\r\n", "\n"),
            ])

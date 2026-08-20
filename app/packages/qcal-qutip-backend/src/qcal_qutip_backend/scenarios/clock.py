from dataclasses import dataclass


@dataclass(slots=True)
class VirtualClock:
    elapsed_s: float = 0.0

    def advance(self, duration_s: float) -> None:
        if duration_s < 0.0:
            raise ValueError("duration_s must not be negative.")
        self.elapsed_s += duration_s

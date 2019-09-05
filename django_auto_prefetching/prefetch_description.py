from dataclasses import dataclass
from typing import Set


@dataclass
class PrefetchDescription:
    prefetch_related: Set
    select_related: Set
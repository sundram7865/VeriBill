"""Synthetic GSTINs with a computed (never guessed) check character."""

from __future__ import annotations

import random
import string

from extractor.validators.gstin import CHARSET, check_character

_PAN_ENTITY_TYPES = "CFPH"  # 4th PAN letter: company, firm, person, HUF


def random_gstin(rng: random.Random, state_code: str) -> str:
    letters = string.ascii_uppercase
    pan = (
        "".join(rng.choice(letters) for _ in range(3))
        + rng.choice(_PAN_ENTITY_TYPES)
        + rng.choice(letters)
        + "".join(rng.choice(string.digits) for _ in range(4))
        + rng.choice(letters)
    )
    first14 = f"{state_code}{pan}{rng.choice('123456789')}Z"
    return first14 + check_character(first14)


def corrupt_check_character(gstin: str, rng: random.Random) -> str:
    """Same GSTIN with a different, therefore wrong, check character."""
    wrong = rng.choice([c for c in CHARSET if c != gstin[14]])
    return gstin[:14] + wrong

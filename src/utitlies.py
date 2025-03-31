from typing import Tuple


def get_last_month(month: int, year: int) -> Tuple[int, int]:
    """
    Get the last month of the given date
    """
    if month == 1:
        return 12, year - 1
    return month - 1, year

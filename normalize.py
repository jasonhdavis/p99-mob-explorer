import re

def normalize_int(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    s = s.replace(",", "")
    m = re.search(r"-?\d+", s)
    return int(m.group(0)) if m else None

def parse_level_range(val):
    """
    Accepts: "12", "12-14", "12 to 14", "12–14"
    Returns: (min, max)
    """
    if val is None:
        return (None, None)
    s = str(val).strip()
    if not s:
        return (None, None)

    s = s.replace("–", "-").replace("to", "-")
    parts = re.findall(r"\d+", s)
    if not parts:
        return (None, None)
    nums = list(map(int, parts))
    if len(nums) == 1:
        return (nums[0], nums[0])
    return (min(nums), max(nums))

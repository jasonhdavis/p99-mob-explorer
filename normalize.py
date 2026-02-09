import re

def normalize_int(val):
    if val is None:
        return None
    s = str(val).strip().lower()
    if not s:
        return None
    s = s.replace(",", "")
    
    # Find the first number (integer or decimal) and optional k/m suffix
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*([km])?", s)
    if not m:
        return None
    
    num_str = m.group(1)
    suffix = m.group(2)
    
    try:
        num = float(num_str)
        if suffix == "k":
            num *= 1000
        elif suffix == "m":
            num *= 1000000
        return int(num)
    except ValueError:
        return None

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

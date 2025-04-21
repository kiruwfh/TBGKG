from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)

def parse_duration(duration_str):
    """
    Parse a duration string into seconds.
    
    Formats:
    - Nd: N days
    - Nh: N hours
    - Nm: N minutes
    - Ns: N seconds
    - Nw: N weeks
    
    Examples:
    - 1d: 1 day
    - 12h: 12 hours
    - 30m: 30 minutes
    - 2w: 2 weeks
    """
    duration_str = duration_str.lower().strip()
    
    # Regular expression to match the format
    pattern = r'^(\d+)([dhmsw])$'
    match = re.match(pattern, duration_str)
    
    if not match:
        raise ValueError("Invalid duration format. Use formats like '1d', '12h', '30m', '45s', '2w'")
    
    value, unit = match.groups()
    value = int(value)
    
    if value <= 0:
        raise ValueError("Duration must be positive")
    
    # Convert to seconds based on unit
    if unit == 'd':
        seconds = value * 86400  # days to seconds
    elif unit == 'h':
        seconds = value * 3600   # hours to seconds
    elif unit == 'm':
        seconds = value * 60     # minutes to seconds
    elif unit == 's':
        seconds = value          # already in seconds
    elif unit == 'w':
        seconds = value * 604800 # weeks to seconds
    else:
        raise ValueError(f"Unknown time unit: {unit}")
    
    return seconds

def format_duration(seconds):
    """Convert seconds to a human-readable duration string."""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"
    else:
        weeks = seconds // 604800
        return f"{weeks} week{'s' if weeks != 1 else ''}"

def format_timestamp(dt):
    """Format a datetime object to a human-readable string."""
    now = datetime.now()
    delta = dt - now
    
    if delta.days < 0:
        return f"{dt.strftime('%Y-%m-%d %H:%M')} (Expired)"
    elif delta.days == 0:
        hours = delta.seconds // 3600
        if hours == 0:
            minutes = (delta.seconds % 3600) // 60
            return f"{dt.strftime('%H:%M')} (in {minutes} minute{'s' if minutes != 1 else ''})"
        else:
            return f"{dt.strftime('%H:%M')} (in {hours} hour{'s' if hours != 1 else ''})"
    elif delta.days == 1:
        return f"{dt.strftime('%Y-%m-%d %H:%M')} (tomorrow)"
    elif delta.days < 7:
        return f"{dt.strftime('%Y-%m-%d %H:%M')} (in {delta.days} days)"
    else:
        return dt.strftime('%Y-%m-%d %H:%M')

def get_duration_str(seconds):
    """Convert seconds to a short duration string (for database storage)."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    elif seconds < 604800:
        return f"{seconds // 86400}d"
    else:
        return f"{seconds // 604800}w"

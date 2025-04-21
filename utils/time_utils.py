from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)

def parse_duration(duration_str):
    """
    Parse a duration string into seconds with enhanced format flexibility.
    
    Formats:
    - Nd, ND: N days
    - Nh, NH: N hours
    - Nm, NM: N minutes
    - Ns, NS: N seconds
    - Nw, NW: N weeks
    
    Examples:
    - 1d, 1D: 1 day
    - 12h, 12H: 12 hours
    - 30m, 30M: 30 minutes
    - 2w, 2W: 2 weeks
    - Complex expressions like 1w3d4h: 1 week, 3 days, 4 hours
    """
    duration_str = duration_str.lower().strip()
    
    # Check for complex duration (e.g., "1w3d4h")
    complex_pattern = r'(\d+[dhmsw])'
    complex_matches = re.findall(complex_pattern, duration_str)
    
    if len(complex_matches) > 1:
        # Handle complex duration with multiple parts
        total_seconds = 0
        for part in complex_matches:
            # Extract value and unit from each part
            # Парсим число из строки
            digits = ''.join(filter(str.isdigit, part))
            if digits:
                value = int(digits)
                unit = part[-1]  # Последний символ - это единица измерения
            else:
                continue
            
            # Convert to seconds based on unit
            if unit == 'd':
                total_seconds += value * 86400  # days to seconds
            elif unit == 'h':
                total_seconds += value * 3600   # hours to seconds
            elif unit == 'm':
                total_seconds += value * 60     # minutes to seconds
            elif unit == 's':
                total_seconds += value          # already in seconds
            elif unit == 'w':
                total_seconds += value * 604800 # weeks to seconds
        
        return total_seconds
    else:
        # Handle simple duration (e.g., "7d")
        # Regular expression to match the format - more flexible with uppercase allowed
        pattern = r'^(\d+)([dhmsw])$'
        match = re.match(pattern, duration_str)
        
        if not match:
            raise ValueError("Invalid duration format. Use formats like '1d', '12h', '30m', '45s', '2w' or combinations like '1w3d'")
        
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

from datetime import datetime


def convert_to_24hr_format(time_str):
    try:
        time_str = time_str.strip().lower().replace(".", "")  # normalize "a.m." → "am"
        
        if "am" in time_str or "pm" in time_str:
            # Try parsing with hour + minute
            try:
                return datetime.strptime(time_str, "%I:%M %p").time()
            except ValueError:
                # Try parsing without minutes, e.g., "7 pm"
                return datetime.strptime(time_str, "%I %p").time()
        else:
            # Already 24-hour format
            return datetime.strptime(time_str, "%H:%M").time()
    except Exception:
        return None
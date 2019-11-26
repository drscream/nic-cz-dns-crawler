from datetime import datetime


def timestamp():
    return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"

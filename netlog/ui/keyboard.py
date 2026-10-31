import os
import sys
import select
from typing import Optional

try:
    import termios
    import tty
    TERMIOS_AVAILABLE = True
except ImportError:
    TERMIOS_AVAILABLE = False


class KeyboardInput:
    """Non-blocking keyboard reader for interactive terminal navigation."""

    def __init__(self):
        self._is_tty = TERMIOS_AVAILABLE and sys.stdin.isatty()
        self._old_settings = None

    def __enter__(self):
        if self._is_tty:
            try:
                self._old_settings = termios.tcgetattr(sys.stdin.fileno())
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                self._old_settings = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._is_tty and self._old_settings:
            try:
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old_settings)
            except Exception:
                pass

    def get_key(self, timeout: float = 0.0) -> Optional[str]:
        """Poll for a single key press or arrow sequence without blocking.
        
        Returns the character/symbol ('up', 'down', etc.) or None if timeout.
        """
        if not self._is_tty:
            return None

        try:
            r, _, _ = select.select([sys.stdin], [], [], timeout)
            if r:
                ch = sys.stdin.read(1)
                if ch == "\x1b":
                    # Check for ANSI escape sequences (e.g. arrow keys)
                    r_esc, _, _ = select.select([sys.stdin], [], [], 0.02)
                    if r_esc:
                        seq = sys.stdin.read(2)
                        if seq == "[A":
                            return "up"
                        elif seq == "[B":
                            return "down"
                        elif seq == "[C":
                            return "right"
                        elif seq == "[D":
                            return "left"
                        return f"\x1b{seq}"
                return ch
        except (OSError, select.error):
            return None

        return None

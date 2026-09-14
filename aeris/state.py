from __future__ import annotations

from typing import Any, Callable

class Store:
    """A centralized state store using a simple pub/sub pattern."""
    
    def __init__(self, initial_state: dict[str, Any] | None = None) -> None:
        self._state: dict[str, Any] = initial_state or {}
        self._listeners: dict[str, list[Callable[[Any], None]]] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a value and notify listeners if it changed."""
        old_value = self._state.get(key)
        if old_value != value:
            self._state[key] = value
            self._notify(key, value)
            
    def update(self, **kwargs: Any) -> None:
        """Update multiple values and notify listeners."""
        for key, value in kwargs.items():
            self.set(key, value)
            
    def subscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """Subscribe to changes for a specific key."""
        if key not in self._listeners:
            self._listeners[key] = []
        self._listeners[key].append(callback)
        
    def unsubscribe(self, key: str, callback: Callable[[Any], None]) -> None:
        """Unsubscribe from changes for a specific key."""
        if key in self._listeners:
            try:
                self._listeners[key].remove(callback)
            except ValueError:
                pass
                
    def _notify(self, key: str, value: Any) -> None:
        if key in self._listeners:
            for callback in self._listeners[key]:
                try:
                    callback(value)
                except Exception:
                    # Don't let one failing listener break the loop
                    pass

# Global singleton store for the application
app_store = Store({
    "is_listening": False,
    "is_speaking": False,
    "last_command": "",
    "last_response": "",
    "kill_switch_active": False,
    "status_message": "Ready"
})

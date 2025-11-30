import threading
from enum import Enum, auto
from typing import Set, Dict, Any
from dataclasses import dataclass
from collections import defaultdict

class EventType(Enum):

    TEMPERATURE_ALERT = auto()
    TEMPERATURE_FAULT = auto()
    ELECTRICAL_FAULT = auto()
    HYDRAULIC_FAULT = auto()
    FAULT_CLEARED = auto()
    
    MODE_CHANGED = auto()
    EMERGENCY_STOP = auto()
    EMERGENCY_RESET = auto()
    TARGET_REACHED = auto()
    
    SHUTDOWN = auto()
    NEW_ROUTE = auto()

@dataclass
class Event:
    event_type: EventType
    data: Dict[str, Any] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}

class EventManager:
    
    def __init__(self):
        self._events = defaultdict(list)
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._shutdown = False
    
    def emit(self, event_type: EventType, data: Dict[str, Any] = None) -> None:
        import time
        event = Event(
            event_type=event_type,
            data=data or {},
            timestamp=time.time()
        )
        
        with self._condition:
            self._events[event_type].append(event)

            self._condition.notify_all()
    
    def wait_for_event(self, event_types: Set[EventType], timeout: float = None) -> Event:
        with self._condition:
            while not self._shutdown:

                for event_type in event_types:
                    if self._events[event_type]:
                        return self._events[event_type].pop(0)
                
                if not self._condition.wait(timeout=timeout):
                    return None
            
            return None
    
    def check_event(self, event_type: EventType) -> Event:
        with self._lock:
            if self._events[event_type]:
                return self._events[event_type].pop(0)
            return None
    
    def clear_events(self, event_type: EventType = None) -> None:
        with self._lock:
            if event_type is None:
                self._events.clear()
            else:
                self._events[event_type].clear()
    
    def has_event(self, event_type: EventType) -> bool:
        with self._lock:
            return len(self._events[event_type]) > 0
    
    def shutdown(self) -> None:
        with self._condition:
            self._shutdown = True
            self._condition.notify_all()
    
    def is_shutdown(self) -> bool:
        with self._lock:
            return self._shutdown

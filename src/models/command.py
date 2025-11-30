from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

class CommandType(Enum):

    ENABLE_AUTOMATIC = auto()
    DISABLE_AUTOMATIC = auto()
    
    ACCELERATE = auto()
    BRAKE = auto()
    STEER_LEFT = auto()
    STEER_RIGHT = auto()
    MOVE_FORWARD = auto()
    MOVE_BACKWARD = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()
    STOP = auto()
    
    EMERGENCY_STOP = auto()
    RESET_EMERGENCY = auto()
    RESET_FAULT = auto()
    
    SHUTDOWN = auto()

@dataclass
class Command:
    command_type: CommandType
    value: Optional[float] = None
    truck_id: Optional[int] = None
    timestamp: Optional[float] = None
    source: str = "local"
    
    def __str__(self):
        if self.value is not None:
            return f"{self.command_type.name} (value={self.value:.2f})"
        return self.command_type.name

KEYBOARD_MAPPING = {
    'a': CommandType.ENABLE_AUTOMATIC,
    'm': CommandType.DISABLE_AUTOMATIC,
    'w': CommandType.ACCELERATE,
    's': CommandType.BRAKE,
    'q': CommandType.STEER_LEFT,
    'e': CommandType.STEER_RIGHT,
    'x': CommandType.STOP,
    'space': CommandType.EMERGENCY_STOP,
    'r': CommandType.RESET_EMERGENCY,
    'f': CommandType.RESET_FAULT,
    'esc': CommandType.SHUTDOWN,
}

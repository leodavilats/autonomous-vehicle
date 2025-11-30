from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

class OperationMode(Enum):
    MANUAL_LOCAL = auto()
    AUTOMATIC_REMOTE = auto()

class VehicleStatus(Enum):
    STOPPED = auto()
    RUNNING = auto()
    FAULT = auto()
    EMERGENCY = auto()

@dataclass
class VehicleState:

    truck_id: int
    
    position_x: float = 0.0
    position_y: float = 0.0
    theta: float = 0.0
    velocity: float = 0.0
    
    mode: OperationMode = OperationMode.MANUAL_LOCAL
    status: VehicleStatus = VehicleStatus.STOPPED
    
    acceleration_cmd: float = 0.0
    steering_cmd: float = 0.0
    
    velocity_setpoint: float = 0.0
    angular_setpoint: float = 0.0
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    
    saved_route: Optional[list] = None
    saved_waypoint_idx: int = 0
    
    temperature: float = 0.0
    electrical_fault: bool = False
    hydraulic_fault: bool = False
    emergency_stop: bool = False
    
    def has_fault(self) -> bool:
        return (self.electrical_fault or 
                self.hydraulic_fault or 
                self.temperature > 120.0 or
                self.emergency_stop)
    
    def is_automatic(self) -> bool:
        return self.mode == OperationMode.AUTOMATIC_REMOTE
    
    def is_manual(self) -> bool:
        return self.mode == OperationMode.MANUAL_LOCAL

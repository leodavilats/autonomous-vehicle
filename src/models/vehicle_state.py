"""
Estados e modos de operação do veículo
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class OperationMode(Enum):
    """Modos de operação do veículo"""
    MANUAL_LOCAL = auto()  # Modo manual local (operador no caminhão)
    AUTOMATIC_REMOTE = auto()  # Modo automático remoto (controlado pela central)


class VehicleStatus(Enum):
    """Status do veículo"""
    STOPPED = auto()  # Parado
    RUNNING = auto()  # Em operação normal
    FAULT = auto()  # Com defeito
    EMERGENCY = auto()  # Emergência acionada


@dataclass
class VehicleState:
    """
    Estado completo do veículo
    Compartilhado entre tarefas com sincronização
    """
    # Identificação
    truck_id: int
    
    # Posição e velocidade
    position_x: float = 0.0
    position_y: float = 0.0
    theta: float = 0.0  # Orientação (radianos)
    velocity: float = 0.0
    
    # Modo e status
    mode: OperationMode = OperationMode.MANUAL_LOCAL
    status: VehicleStatus = VehicleStatus.STOPPED
    
    # Atuadores
    acceleration_cmd: float = 0.0
    steering_cmd: float = 0.0
    
    # Setpoints (para controle automático)
    velocity_setpoint: float = 0.0
    angular_setpoint: float = 0.0
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    
    # Falhas
    temperature: float = 0.0
    electrical_fault: bool = False
    hydraulic_fault: bool = False
    emergency_stop: bool = False
    
    def has_fault(self) -> bool:
        """Verifica se há alguma falha ativa"""
        return (self.electrical_fault or 
                self.hydraulic_fault or 
                self.temperature > 100.0 or  # Temperatura crítica
                self.emergency_stop)
    
    def is_automatic(self) -> bool:
        """Verifica se está em modo automático"""
        return self.mode == OperationMode.AUTOMATIC_REMOTE
    
    def is_manual(self) -> bool:
        """Verifica se está em modo manual"""
        return self.mode == OperationMode.MANUAL_LOCAL

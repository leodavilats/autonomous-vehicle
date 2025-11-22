"""
Estado compartilhado do veículo com sincronização
Usado por todas as tarefas para ler/escrever o estado do sistema
"""

import threading
import copy
from src.models.vehicle_state import VehicleState, OperationMode, VehicleStatus


class SharedState:
    """
    Estado compartilhado do veículo com proteção por mutex
    Todas as tarefas acessam este objeto para ler/modificar o estado
    """
    
    def __init__(self, truck_id: int):
        """
        Args:
            truck_id: Identificação do caminhão
        """
        self._state = VehicleState(truck_id=truck_id)
        self._lock = threading.Lock()  # Mutex para proteção
    
    def get_state(self) -> VehicleState:
        """
        Obtém cópia do estado atual (thread-safe)
        
        Returns:
            Cópia do estado do veículo
        """
        with self._lock:
            return copy.deepcopy(self._state)
    
    def update_state(self, **kwargs) -> None:
        """
        Atualiza campos específicos do estado (thread-safe)
        
        Args:
            **kwargs: Campos a serem atualizados
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
    
    def set_position(self, x: float, y: float, theta: float, velocity: float) -> None:
        """Atualiza posição e velocidade"""
        with self._lock:
            self._state.position_x = x
            self._state.position_y = y
            self._state.theta = theta
            self._state.velocity = velocity
    
    def set_actuators(self, acceleration: float, steering: float) -> None:
        """Atualiza comandos dos atuadores"""
        with self._lock:
            self._state.acceleration_cmd = acceleration
            self._state.steering_cmd = steering
    
    def set_mode(self, mode: OperationMode) -> None:
        """Altera modo de operação"""
        with self._lock:
            self._state.mode = mode
    
    def set_status(self, status: VehicleStatus) -> None:
        """Altera status do veículo"""
        with self._lock:
            self._state.status = status
    
    def set_setpoints(self, velocity_sp: float = None, angular_sp: float = None) -> None:
        """Atualiza setpoints para controle automático"""
        with self._lock:
            if velocity_sp is not None:
                self._state.velocity_setpoint = velocity_sp
            if angular_sp is not None:
                self._state.angular_setpoint = angular_sp
    
    def set_target(self, target_x: float = None, target_y: float = None) -> None:
        """Define posição alvo"""
        with self._lock:
            if target_x is not None:
                self._state.target_x = target_x
            if target_y is not None:
                self._state.target_y = target_y
    
    def set_faults(self, temperature: float = None, 
                   electrical: bool = None, 
                   hydraulic: bool = None,
                   emergency: bool = None) -> None:
        """Atualiza estado de falhas"""
        with self._lock:
            if temperature is not None:
                self._state.temperature = temperature
            if electrical is not None:
                self._state.electrical_fault = electrical
            if hydraulic is not None:
                self._state.hydraulic_fault = hydraulic
            if emergency is not None:
                self._state.emergency_stop = emergency
    
    def is_automatic(self) -> bool:
        """Verifica se está em modo automático"""
        with self._lock:
            return self._state.is_automatic()
    
    def is_manual(self) -> bool:
        """Verifica se está em modo manual"""
        with self._lock:
            return self._state.is_manual()
    
    def has_fault(self) -> bool:
        """Verifica se há alguma falha"""
        with self._lock:
            return self._state.has_fault()
    
    def get_position(self) -> tuple:
        """Retorna (x, y, theta, velocity)"""
        with self._lock:
            return (self._state.position_x, 
                    self._state.position_y, 
                    self._state.theta, 
                    self._state.velocity)
    
    def get_actuators(self) -> tuple:
        """Retorna (acceleration, steering)"""
        with self._lock:
            return (self._state.acceleration_cmd, 
                    self._state.steering_cmd)
    
    def get_setpoints(self) -> tuple:
        """Retorna (velocity_setpoint, angular_setpoint)"""
        with self._lock:
            return (self._state.velocity_setpoint, 
                    self._state.angular_setpoint)

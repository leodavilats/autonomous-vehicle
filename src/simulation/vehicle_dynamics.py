"""
Dinâmica do veículo com modelo de inércia simplificado
Simula a física do caminhão de mineração
"""

import math
from dataclasses import dataclass
from typing import Tuple


@dataclass
class VehicleParameters:
    """Parâmetros físicos do veículo"""
    max_velocity: float = 10.0  # Velocidade máxima (m/s)
    max_angular_velocity: float = 1.0  # Velocidade angular máxima (rad/s)
    tau_velocity: float = 0.5  # Constante de tempo para velocidade (inércia)
    tau_angular: float = 0.3  # Constante de tempo para rotação
    dt: float = 0.1  # Passo de tempo da simulação (s)


class VehicleDynamics:
    """
    Modelo dinâmico simplificado do veículo
    
    Usa modelo cinemático com inércia (filtro de primeira ordem)
    para simular aceleração e frenagem suaves
    """
    
    def __init__(self, params: VehicleParameters = None):
        """
        Args:
            params: Parâmetros do veículo (usa padrão se None)
        """
        self.params = params or VehicleParameters()
        
        # Estado atual do veículo
        self.x = 0.0  # Posição X (m)
        self.y = 0.0  # Posição Y (m)
        self.theta = 0.0  # Orientação (rad)
        self.velocity = 0.0  # Velocidade linear (m/s)
        self.angular_velocity = 0.0  # Velocidade angular (rad/s)
    
    def set_position(self, x: float, y: float, theta: float) -> None:
        """Define posição inicial do veículo"""
        self.x = x
        self.y = y
        self.theta = theta
    
    def update(self, accel_cmd: float, steer_cmd: float) -> Tuple[float, float, float, float]:
        """
        Atualiza estado do veículo baseado nos comandos
        
        Args:
            accel_cmd: Comando de aceleração [-1.0, 1.0]
            steer_cmd: Comando de direção [-1.0, 1.0]
            
        Returns:
            Tupla (x, y, theta, velocity)
        """
        dt = self.params.dt
        
        # Limita comandos
        accel_cmd = max(-1.0, min(1.0, accel_cmd))
        steer_cmd = max(-1.0, min(1.0, steer_cmd))
        
        # Calcula velocidades alvo
        target_velocity = accel_cmd * self.params.max_velocity
        target_angular = steer_cmd * self.params.max_angular_velocity
        
        # Aplica inércia (filtro de primeira ordem)
        # v_new = v_old + (v_target - v_old) * dt / tau
        self.velocity += (target_velocity - self.velocity) * dt / self.params.tau_velocity
        self.angular_velocity += (target_angular - self.angular_velocity) * dt / self.params.tau_angular
        
        # Atualiza posição usando modelo cinemático
        self.x += self.velocity * math.cos(self.theta) * dt
        self.y += self.velocity * math.sin(self.theta) * dt
        self.theta += self.angular_velocity * dt
        
        # Normaliza ângulo para [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))
        
        return self.x, self.y, self.theta, self.velocity
    
    def get_state(self) -> Tuple[float, float, float, float]:
        """
        Retorna estado atual
        
        Returns:
            Tupla (x, y, theta, velocity)
        """
        return self.x, self.y, self.theta, self.velocity
    
    def reset(self) -> None:
        """Reseta veículo para posição inicial"""
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.velocity = 0.0
        self.angular_velocity = 0.0
    
    def emergency_stop(self) -> None:
        """Para o veículo imediatamente (emergência)"""
        self.velocity = 0.0
        self.angular_velocity = 0.0

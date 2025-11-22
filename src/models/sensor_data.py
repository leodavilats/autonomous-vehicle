"""
Modelos de dados dos sensores e atuadores
Baseado na Tabela 1 do trabalho
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SensorData:
    """
    Dados dos sensores do veículo (Tabela 1 - Entradas)
    """
    # Sensores de posicionamento
    position_x: float  # Posição X (metros)
    position_y: float  # Posição Y (metros)
    theta: float  # Ângulo de orientação (radianos)
    velocity: float  # Velocidade linear (m/s)
    
    # Sensores de falha
    temperature: float  # Temperatura do motor (°C)
    electrical_fault: bool  # Falha elétrica (True/False)
    hydraulic_fault: bool  # Falha hidráulica (True/False)
    
    # Timestamp da leitura
    timestamp: Optional[float] = None


@dataclass
class ActuatorData:
    """
    Dados dos atuadores do veículo (Tabela 1 - Saídas)
    """
    acceleration: float  # Comando de aceleração [-1.0, 1.0]
    steering: float  # Comando de direção/ângulo [-1.0, 1.0]
    
    # Timestamp do comando
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        """Valida os valores dos atuadores"""
        self.acceleration = max(-1.0, min(1.0, self.acceleration))
        self.steering = max(-1.0, min(1.0, self.steering))


@dataclass
class FilteredSensorData:
    """
    Dados dos sensores após filtragem (média móvel)
    Usado no buffer circular compartilhado
    """
    position_x: float
    position_y: float
    theta: float
    velocity: float
    temperature: float
    electrical_fault: bool
    hydraulic_fault: bool
    timestamp: float
    
    @classmethod
    def from_sensor_data(cls, sensor_data: SensorData):
        """Cria FilteredSensorData a partir de SensorData"""
        return cls(
            position_x=sensor_data.position_x,
            position_y=sensor_data.position_y,
            theta=sensor_data.theta,
            velocity=sensor_data.velocity,
            temperature=sensor_data.temperature,
            electrical_fault=sensor_data.electrical_fault,
            hydraulic_fault=sensor_data.hydraulic_fault,
            timestamp=sensor_data.timestamp or 0.0
        )

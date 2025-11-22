"""
Comandos do operador
Baseado na Tabela 2 do trabalho
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional


class CommandType(Enum):
    """
    Tipos de comandos do operador (Tabela 2)
    Cada comando é ativado por uma tecla do teclado
    """
    # Controle de modo
    ENABLE_AUTOMATIC = auto()  # Ativar modo automático
    DISABLE_AUTOMATIC = auto()  # Desativar modo automático (volta para manual)
    
    # Controle manual
    ACCELERATE = auto()  # Acelerar
    BRAKE = auto()  # Frear
    STEER_LEFT = auto()  # Virar à esquerda
    STEER_RIGHT = auto()  # Virar à direita
    STOP = auto()  # Parar
    
    # Emergência
    EMERGENCY_STOP = auto()  # Parada de emergência
    RESET_EMERGENCY = auto()  # Resetar emergência
    
    # Sistema
    SHUTDOWN = auto()  # Desligar sistema


@dataclass
class Command:
    """
    Comando do operador ou sistema central
    """
    command_type: CommandType
    value: Optional[float] = None  # Valor opcional (ex: velocidade desejada)
    truck_id: Optional[int] = None  # ID do caminhão (para comandos da central)
    timestamp: Optional[float] = None
    source: str = "local"  # "local" ou "remote"
    
    def __str__(self):
        if self.value is not None:
            return f"{self.command_type.name} (value={self.value:.2f})"
        return self.command_type.name


# Mapeamento de teclas para comandos (para Interface Local)
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
    'esc': CommandType.SHUTDOWN,
}

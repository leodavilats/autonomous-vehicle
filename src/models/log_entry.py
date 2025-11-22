"""
Estrutura de log de eventos
Baseado na Tabela 3 do trabalho
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any
import json


@dataclass
class LogEntry:
    """
    Estrutura de log de eventos (Tabela 3)
    Cada evento deve conter:
    - Timestamp
    - Identificação (número) do caminhão
    - Estado do caminhão
    - Posição
    - Descrição do evento
    """
    timestamp: float  # Timestamp Unix (segundos desde epoch)
    truck_id: int  # Identificação do caminhão
    status: str  # Estado do caminhão (RUNNING, STOPPED, FAULT, etc.)
    mode: str  # Modo de operação (MANUAL_LOCAL, AUTOMATIC_REMOTE)
    position_x: float  # Posição X (metros)
    position_y: float  # Posição Y (metros)
    theta: float  # Orientação (radianos)
    velocity: float  # Velocidade (m/s)
    event_description: str  # Descrição do evento
    
    # Dados adicionais opcionais
    temperature: float = 0.0
    electrical_fault: bool = False
    hydraulic_fault: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return asdict(self)
    
    def to_json(self) -> str:
        """Converte para JSON"""
        return json.dumps(self.to_dict())
    
    def to_csv_line(self) -> str:
        """
        Converte para linha CSV (para armazenamento em disco)
        Formato: timestamp,truck_id,status,mode,x,y,theta,v,temp,e_fault,h_fault,description
        """
        return (f"{self.timestamp:.3f},"
                f"{self.truck_id},"
                f"{self.status},"
                f"{self.mode},"
                f"{self.position_x:.2f},"
                f"{self.position_y:.2f},"
                f"{self.theta:.4f},"
                f"{self.velocity:.2f},"
                f"{self.temperature:.1f},"
                f"{int(self.electrical_fault)},"
                f"{int(self.hydraulic_fault)},"
                f'"{self.event_description}"\n')
    
    @staticmethod
    def csv_header() -> str:
        """Retorna cabeçalho CSV"""
        return ("timestamp,truck_id,status,mode,position_x,position_y,theta,"
                "velocity,temperature,electrical_fault,hydraulic_fault,"
                "event_description\n")
    
    def get_datetime_str(self) -> str:
        """Retorna timestamp formatado como string legível"""
        return datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    def __str__(self):
        return (f"[{self.get_datetime_str()}] Truck {self.truck_id} - "
                f"{self.status}/{self.mode} - "
                f"Pos({self.position_x:.1f}, {self.position_y:.1f}) - "
                f"{self.event_description}")

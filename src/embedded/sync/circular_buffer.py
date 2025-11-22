"""
Buffer circular thread-safe para dados dos sensores filtrados
Usado pela tarefa Tratamento Sensores para alimentar outras tarefas
"""

import threading
from typing import Optional, List
from collections import deque
from src.models.sensor_data import FilteredSensorData


class CircularBuffer:
    """
    Buffer circular thread-safe para armazenar dados dos sensores filtrados
    Implementa proteção com mutex para acesso concorrente
    """
    
    def __init__(self, size: int = 100):
        """
        Args:
            size: Tamanho máximo do buffer circular
        """
        self._buffer = deque(maxlen=size)
        self._lock = threading.Lock()  # Mutex para proteção
        self._size = size
    
    def write(self, data: FilteredSensorData) -> None:
        """
        Escreve dados no buffer (thread-safe)
        Se o buffer estiver cheio, o elemento mais antigo é descartado
        
        Args:
            data: Dados dos sensores filtrados
        """
        with self._lock:
            self._buffer.append(data)
    
    def read_latest(self) -> Optional[FilteredSensorData]:
        """
        Lê o dado mais recente do buffer sem removê-lo
        
        Returns:
            Dados mais recentes ou None se buffer vazio
        """
        with self._lock:
            if len(self._buffer) > 0:
                return self._buffer[-1]
            return None
    
    def read_last_n(self, n: int) -> List[FilteredSensorData]:
        """
        Lê os últimos N elementos do buffer
        
        Args:
            n: Número de elementos a ler
            
        Returns:
            Lista com até N elementos mais recentes
        """
        with self._lock:
            # Retorna os últimos n elementos
            return list(self._buffer)[-n:] if len(self._buffer) > 0 else []
    
    def read_all(self) -> List[FilteredSensorData]:
        """
        Lê todos os dados do buffer
        
        Returns:
            Lista com todos os elementos
        """
        with self._lock:
            return list(self._buffer)
    
    def clear(self) -> None:
        """Limpa o buffer"""
        with self._lock:
            self._buffer.clear()
    
    def size(self) -> int:
        """Retorna o número de elementos no buffer"""
        with self._lock:
            return len(self._buffer)
    
    def is_empty(self) -> bool:
        """Verifica se o buffer está vazio"""
        with self._lock:
            return len(self._buffer) == 0
    
    def is_full(self) -> bool:
        """Verifica se o buffer está cheio"""
        with self._lock:
            return len(self._buffer) >= self._size

"""
Gerenciador de eventos para comunicação entre tarefas
Usa condition variables para notificar múltiplas tarefas sobre eventos
"""

import threading
from enum import Enum, auto
from typing import Set, Dict, Any
from dataclasses import dataclass
from collections import defaultdict


class EventType(Enum):
    """Tipos de eventos do sistema"""
    # Eventos de falha
    TEMPERATURE_FAULT = auto()
    ELECTRICAL_FAULT = auto()
    HYDRAULIC_FAULT = auto()
    FAULT_CLEARED = auto()
    
    # Eventos de operação
    MODE_CHANGED = auto()
    EMERGENCY_STOP = auto()
    EMERGENCY_RESET = auto()
    TARGET_REACHED = auto()
    
    # Eventos de sistema
    SHUTDOWN = auto()
    NEW_ROUTE = auto()


@dataclass
class Event:
    """Representa um evento do sistema"""
    event_type: EventType
    data: Dict[str, Any] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}


class EventManager:
    """
    Gerenciador de eventos usando condition variables
    Permite que tarefas aguardem por eventos específicos e sejam notificadas
    """
    
    def __init__(self):
        """Inicializa o gerenciador de eventos"""
        self._events = defaultdict(list)  # Fila de eventos por tipo
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._shutdown = False
    
    def emit(self, event_type: EventType, data: Dict[str, Any] = None) -> None:
        """
        Emite um evento para todas as tarefas interessadas
        
        Args:
            event_type: Tipo do evento
            data: Dados associados ao evento
        """
        import time
        event = Event(
            event_type=event_type,
            data=data or {},
            timestamp=time.time()
        )
        
        with self._condition:
            self._events[event_type].append(event)
            # Notifica todas as threads aguardando (broadcasting)
            self._condition.notify_all()
    
    def wait_for_event(self, event_types: Set[EventType], timeout: float = None) -> Event:
        """
        Aguarda por um dos eventos especificados
        
        Args:
            event_types: Conjunto de tipos de eventos a aguardar
            timeout: Timeout em segundos (None = espera indefinida)
            
        Returns:
            Evento recebido ou None se timeout
        """
        with self._condition:
            while not self._shutdown:
                # Verifica se há algum evento dos tipos especificados
                for event_type in event_types:
                    if self._events[event_type]:
                        return self._events[event_type].pop(0)
                
                # Aguarda notificação
                if not self._condition.wait(timeout=timeout):
                    return None  # Timeout
            
            return None  # Shutdown
    
    def check_event(self, event_type: EventType) -> Event:
        """
        Verifica se há evento do tipo especificado (non-blocking)
        
        Args:
            event_type: Tipo do evento a verificar
            
        Returns:
            Evento se disponível, None caso contrário
        """
        with self._lock:
            if self._events[event_type]:
                return self._events[event_type].pop(0)
            return None
    
    def clear_events(self, event_type: EventType = None) -> None:
        """
        Limpa eventos
        
        Args:
            event_type: Tipo específico a limpar (None = todos)
        """
        with self._lock:
            if event_type is None:
                self._events.clear()
            else:
                self._events[event_type].clear()
    
    def has_event(self, event_type: EventType) -> bool:
        """Verifica se há evento pendente do tipo especificado"""
        with self._lock:
            return len(self._events[event_type]) > 0
    
    def shutdown(self) -> None:
        """Sinaliza shutdown para todas as threads aguardando"""
        with self._condition:
            self._shutdown = True
            self._condition.notify_all()
    
    def is_shutdown(self) -> bool:
        """Verifica se shutdown foi solicitado"""
        with self._lock:
            return self._shutdown

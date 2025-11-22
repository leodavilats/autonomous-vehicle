"""
Tarefa de Monitoramento de Falhas
Monitora sensores de falha e dispara eventos para outras tarefas
"""

import threading
import time
from typing import Callable
from src.models.sensor_data import SensorData
from src.embedded.sync.event_manager import EventManager, EventType


class FaultMonitoringTask(threading.Thread):
    """
    Tarefa de Monitoramento de Falhas
    
    Responsabilidades:
    - Ler sensores de falha (temperatura, elétrica, hidráulica)
    - Detectar condições de falha
    - Disparar eventos para: Lógica de Comando, Controle de Navegação, Coletor de Dados
    """
    
    def __init__(self,
                 sensor_reader: Callable[[], SensorData],
                 event_manager: EventManager,
                 check_period: float = 0.5,
                 temp_threshold: float = 100.0):
        """
        Args:
            sensor_reader: Função que retorna SensorData
            event_manager: Gerenciador de eventos
            check_period: Período de verificação (segundos)
            temp_threshold: Temperatura crítica (°C)
        """
        super().__init__(name="FaultMonitoring", daemon=True)
        
        self.sensor_reader = sensor_reader
        self.event_manager = event_manager
        self.check_period = check_period
        self.temp_threshold = temp_threshold
        self._stop_event = threading.Event()
        
        # Estado anterior para detectar mudanças
        self._prev_temp_fault = False
        self._prev_elec_fault = False
        self._prev_hydr_fault = False
    
    def run(self):
        """Loop principal da tarefa"""
        print(f"[{self.name}] Tarefa iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                # Lê sensores
                sensor_data = self.sensor_reader()
                
                # Verifica temperatura
                temp_fault = sensor_data.temperature > self.temp_threshold
                if temp_fault and not self._prev_temp_fault:
                    # Nova falha de temperatura
                    print(f"[{self.name}] FALHA: Temperatura crítica ({sensor_data.temperature:.1f}°C)")
                    self.event_manager.emit(
                        EventType.TEMPERATURE_FAULT,
                        {"temperature": sensor_data.temperature}
                    )
                    self._prev_temp_fault = True
                elif not temp_fault and self._prev_temp_fault:
                    # Falha resolvida
                    print(f"[{self.name}] Temperatura normalizada")
                    self.event_manager.emit(EventType.FAULT_CLEARED, {"type": "temperature"})
                    self._prev_temp_fault = False
                
                # Verifica falha elétrica
                if sensor_data.electrical_fault and not self._prev_elec_fault:
                    print(f"[{self.name}] FALHA: Sistema elétrico")
                    self.event_manager.emit(EventType.ELECTRICAL_FAULT, {})
                    self._prev_elec_fault = True
                elif not sensor_data.electrical_fault and self._prev_elec_fault:
                    print(f"[{self.name}] Sistema elétrico normalizado")
                    self.event_manager.emit(EventType.FAULT_CLEARED, {"type": "electrical"})
                    self._prev_elec_fault = False
                
                # Verifica falha hidráulica
                if sensor_data.hydraulic_fault and not self._prev_hydr_fault:
                    print(f"[{self.name}] FALHA: Sistema hidráulico")
                    self.event_manager.emit(EventType.HYDRAULIC_FAULT, {})
                    self._prev_hydr_fault = True
                elif not sensor_data.hydraulic_fault and self._prev_hydr_fault:
                    print(f"[{self.name}] Sistema hidráulico normalizado")
                    self.event_manager.emit(EventType.FAULT_CLEARED, {"type": "hydraulic"})
                    self._prev_hydr_fault = False
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            # Aguarda próximo ciclo
            elapsed = time.time() - start_time
            sleep_time = max(0, self.check_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def stop(self):
        """Para a tarefa"""
        self._stop_event.set()

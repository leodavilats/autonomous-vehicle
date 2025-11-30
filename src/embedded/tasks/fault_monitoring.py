import threading
import time
from typing import Callable
from src.models.sensor_data import SensorData
from src.embedded.sync.event_manager import EventManager, EventType

class FaultMonitoringTask(threading.Thread):
    
    def __init__(self,
                 sensor_reader: Callable[[], SensorData],
                 event_manager: EventManager,
                 check_period: float = 0.5,
                 temp_alert_threshold: float = 95.0,
                 temp_fault_threshold: float = 120.0):
        super().__init__(name="FaultMonitoring", daemon=True)
        
        self.sensor_reader = sensor_reader
        self.event_manager = event_manager
        self.check_period = check_period
        self.temp_alert_threshold = temp_alert_threshold
        self.temp_fault_threshold = temp_fault_threshold
        self._stop_event = threading.Event()
        
        self._prev_temp_alert = False
        self._prev_temp_fault = False
        self._prev_elec_fault = False
        self._prev_hydr_fault = False
    
    def run(self):
        print(f"[{self.name}] Tarefa iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:

                sensor_data = self.sensor_reader()
                
                temp_fault = sensor_data.temperature > self.temp_fault_threshold
                if temp_fault and not self._prev_temp_fault:
                    print(f"[{self.name}] FALHA: Temperatura crítica ({sensor_data.temperature:.1f}°C > {self.temp_fault_threshold}°C)")
                    self.event_manager.emit(
                        EventType.TEMPERATURE_FAULT,
                        {"temperature": sensor_data.temperature}
                    )
                    self._prev_temp_fault = True
                elif not temp_fault and self._prev_temp_fault:
                    print(f"[{self.name}] Falha de temperatura normalizada")
                    self.event_manager.emit(EventType.FAULT_CLEARED, {"type": "temperature_fault"})
                    self._prev_temp_fault = False
                
                temp_alert = sensor_data.temperature > self.temp_alert_threshold and not temp_fault
                if temp_alert and not self._prev_temp_alert:
                    print(f"[{self.name}] ALERTA: Temperatura elevada ({sensor_data.temperature:.1f}°C > {self.temp_alert_threshold}°C)")
                    self.event_manager.emit(
                        EventType.TEMPERATURE_ALERT,
                        {"temperature": sensor_data.temperature}
                    )
                    self._prev_temp_alert = True
                elif not temp_alert and self._prev_temp_alert:
                    print(f"[{self.name}] Alerta de temperatura normalizado")
                    self.event_manager.emit(EventType.FAULT_CLEARED, {"type": "temperature_alert"})
                    self._prev_temp_alert = False
                
                if sensor_data.electrical_fault and not self._prev_elec_fault:
                    print(f"[{self.name}] FALHA: Sistema elétrico")
                    self.event_manager.emit(EventType.ELECTRICAL_FAULT, {})
                    self._prev_elec_fault = True
                elif not sensor_data.electrical_fault and self._prev_elec_fault:
                    print(f"[{self.name}] Sistema elétrico normalizado")
                    self.event_manager.emit(EventType.FAULT_CLEARED, {"type": "electrical"})
                    self._prev_elec_fault = False
                
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
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.check_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def stop(self):
        self._stop_event.set()

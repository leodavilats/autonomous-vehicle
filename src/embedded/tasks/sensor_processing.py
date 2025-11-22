"""
Tarefa de Tratamento de Sensores
Lê dados dos sensores, aplica filtro de média móvel e escreve no buffer circular
"""

import threading
import time
from typing import Callable, Optional
from src.models.sensor_data import SensorData, FilteredSensorData
from src.embedded.filters.moving_average import MovingAverageFilter
from src.embedded.sync.circular_buffer import CircularBuffer


class SensorProcessingTask(threading.Thread):
    """
    Tarefa de Tratamento de Sensores
    
    Responsabilidades:
    - Ler dados dos sensores (com ruído)
    - Aplicar filtro de média móvel de ordem M
    - Escrever dados filtrados no buffer circular
    """
    
    def __init__(self,
                 sensor_reader: Callable[[], SensorData],
                 circular_buffer: CircularBuffer,
                 filter_order: int = 5,
                 sample_period: float = 0.1):
        """
        Args:
            sensor_reader: Função que retorna SensorData (leitura dos sensores)
            circular_buffer: Buffer circular compartilhado
            filter_order: Ordem M do filtro de média móvel
            sample_period: Período de amostragem (segundos)
        """
        super().__init__(name="SensorProcessing", daemon=True)
        
        self.sensor_reader = sensor_reader
        self.circular_buffer = circular_buffer
        self.sample_period = sample_period
        self._stop_event = threading.Event()
        
        # Filtros de média móvel para cada sensor
        self.filter_x = MovingAverageFilter(filter_order)
        self.filter_y = MovingAverageFilter(filter_order)
        self.filter_theta = MovingAverageFilter(filter_order)
        self.filter_velocity = MovingAverageFilter(filter_order)
        self.filter_temperature = MovingAverageFilter(filter_order)
    
    def run(self):
        """Loop principal da tarefa"""
        print(f"[{self.name}] Tarefa iniciada (filtro ordem {self.filter_x.get_order()})")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                # 1. Lê dados dos sensores (com ruído)
                sensor_data = self.sensor_reader()
                
                # 2. Aplica filtro de média móvel
                filtered_x = self.filter_x.filter(sensor_data.position_x)
                filtered_y = self.filter_y.filter(sensor_data.position_y)
                filtered_theta = self.filter_theta.filter(sensor_data.theta)
                filtered_velocity = self.filter_velocity.filter(sensor_data.velocity)
                filtered_temp = self.filter_temperature.filter(sensor_data.temperature)
                
                # 3. Cria dados filtrados
                filtered_data = FilteredSensorData(
                    position_x=filtered_x,
                    position_y=filtered_y,
                    theta=filtered_theta,
                    velocity=filtered_velocity,
                    temperature=filtered_temp,
                    electrical_fault=sensor_data.electrical_fault,
                    hydraulic_fault=sensor_data.hydraulic_fault,
                    timestamp=time.time()
                )
                
                # 4. Escreve no buffer circular (thread-safe)
                self.circular_buffer.write(filtered_data)
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            # Aguarda próximo período de amostragem
            elapsed = time.time() - start_time
            sleep_time = max(0, self.sample_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def stop(self):
        """Para a tarefa"""
        self._stop_event.set()

"""
Simulação da Mina
Gera dados dos sensores a partir dos atuadores
"""

import threading
import time
from typing import Callable
from src.simulation.vehicle_dynamics import VehicleDynamics, VehicleParameters
from src.simulation.noise_generator import MultiChannelNoise
from src.models.sensor_data import SensorData, ActuatorData
from src.embedded.sync.shared_state import SharedState


class MineSimulatorTask(threading.Thread):
    """
    Tarefa de Simulação da Mina
    
    Responsabilidades:
    - Gerar dados dos sensores a partir dos atuadores
    - Simular dinâmica do veículo (EDO/diferenças)
    - Adicionar ruído aos sensores
    - Permitir injeção de falhas
    """
    
    def __init__(self,
                 shared_state: SharedState,
                 simulation_period: float = 0.05,
                 enable_noise: bool = True):
        """
        Args:
            shared_state: Estado compartilhado (para ler atuadores)
            simulation_period: Período de simulação (segundos)
            enable_noise: Se True, adiciona ruído aos sensores
        """
        super().__init__(name="MineSimulator", daemon=True)
        
        self.shared_state = shared_state
        self.simulation_period = simulation_period
        self.enable_noise = enable_noise
        self._stop_event = threading.Event()
        
        # Dinâmica do veículo
        params = VehicleParameters(
            max_velocity=10.0,
            max_angular_velocity=1.0,
            tau_velocity=0.5,
            tau_angular=0.3,
            dt=simulation_period
        )
        self.dynamics = VehicleDynamics(params)
        
        # Posição inicial no centro do mapa (50m, 37.5m)
        self.dynamics.set_position(50.0, 37.5, 0.0)
        
        # Gerador de ruído
        self.noise = MultiChannelNoise({
            'position_x': 0.05,      # 5cm de ruído
            'position_y': 0.05,
            'theta': 0.02,           # ~1 grau
            'velocity': 0.1,         # 0.1 m/s
            'temperature': 2.0       # 2°C
        })
        
        # Sensores de falha (simulados)
        self.temperature = 25.0  # Temperatura inicial
        self.electrical_fault = False
        self.hydraulic_fault = False
        
        # Estado da simulação - posição inicial no centro do mapa (50m, 37.5m)
        self.current_sensor_data = SensorData(
            position_x=50.0,
            position_y=37.5,
            theta=0.0,
            velocity=0.0,
            temperature=25.0,
            electrical_fault=False,
            hydraulic_fault=False,
            timestamp=time.time()
        )
    
    def run(self):
        """Loop principal da simulação"""
        print(f"[{self.name}] Simulação iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                # 1. Lê comandos dos atuadores
                accel_cmd, steer_cmd = self.shared_state.get_actuators()
                
                # 2. Atualiza dinâmica do veículo
                x, y, theta, velocity = self.dynamics.update(accel_cmd, steer_cmd)
                
                # 3. Simula temperatura (aumenta com velocidade)
                self.temperature = 25.0 + abs(velocity) * 2.0 + abs(accel_cmd) * 5.0
                
                # 4. Gera dados dos sensores
                sensor_values = {
                    'position_x': x,
                    'position_y': y,
                    'theta': theta,
                    'velocity': velocity,
                    'temperature': self.temperature
                }
                
                # 5. Adiciona ruído
                if self.enable_noise:
                    sensor_values = self.noise.add_noise_dict(sensor_values)
                
                # 6. Cria SensorData
                self.current_sensor_data = SensorData(
                    position_x=sensor_values['position_x'],
                    position_y=sensor_values['position_y'],
                    theta=sensor_values['theta'],
                    velocity=sensor_values['velocity'],
                    temperature=sensor_values['temperature'],
                    electrical_fault=self.electrical_fault,
                    hydraulic_fault=self.hydraulic_fault,
                    timestamp=time.time()
                )
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            # Aguarda próximo ciclo
            elapsed = time.time() - start_time
            sleep_time = max(0, self.simulation_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Simulação finalizada")
    
    def get_sensor_data(self) -> SensorData:
        """Retorna dados atuais dos sensores"""
        return self.current_sensor_data
    
    def inject_electrical_fault(self, fault: bool = True):
        """Injeta/remove falha elétrica"""
        self.electrical_fault = fault
        print(f"[{self.name}] Falha elétrica {'INJETADA' if fault else 'REMOVIDA'}")
    
    def inject_hydraulic_fault(self, fault: bool = True):
        """Injeta/remove falha hidráulica"""
        self.hydraulic_fault = fault
        print(f"[{self.name}] Falha hidráulica {'INJETADA' if fault else 'REMOVIDA'}")
    
    def set_position(self, x: float, y: float, theta: float = 0.0):
        """Define posição inicial do veículo"""
        self.dynamics.set_position(x, y, theta)
    
    def emergency_stop(self):
        """Para o veículo imediatamente"""
        self.dynamics.emergency_stop()
    
    def stop(self):
        """Para a simulação"""
        self._stop_event.set()

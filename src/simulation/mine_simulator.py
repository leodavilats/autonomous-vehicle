import threading
import time
import random
from typing import Callable
from src.simulation.vehicle_dynamics import VehicleDynamics, VehicleParameters
from src.simulation.noise_generator import MultiChannelNoise
from src.models.sensor_data import SensorData, ActuatorData
from src.embedded.sync.shared_state import SharedState

class MineSimulatorTask(threading.Thread):
    
    def __init__(self,
                 shared_state: SharedState,
                 simulation_period: float = 0.05,
                 enable_noise: bool = True):
        super().__init__(name="MineSimulator", daemon=True)
        
        self.shared_state = shared_state
        self.simulation_period = simulation_period
        self.enable_noise = enable_noise
        self._stop_event = threading.Event()
        
        params = VehicleParameters(
            max_velocity=10.0,
            max_angular_velocity=1.0,
            tau_velocity=0.5,
            tau_angular=0.3,
            dt=simulation_period
        )
        self.dynamics = VehicleDynamics(params)
        
        self.dynamics.set_position(50.0, 37.5, 0.0)
        
        self.noise = MultiChannelNoise({
            'position_x': 0.05,
            'position_y': 0.05,
            'theta': 0.02,
            'velocity': 0.1,
            'temperature': 2.0
        })
        
        self.temperature = 25.0
        self.electrical_fault = False
        self.hydraulic_fault = False
        
        self.random_heating = False
        self.target_temp = 25.0
        self.last_heating_check = time.time()
        self.heating_check_interval = 10.0
        
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
        print(f"[{self.name}] Simulação iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:

                accel_cmd, steer_cmd = self.shared_state.get_actuators()
                
                x, y, theta, velocity = self.dynamics.update(accel_cmd, steer_cmd)
                
                current_time = time.time()
                if current_time - self.last_heating_check >= self.heating_check_interval:
                    self.last_heating_check = current_time
                    if random.random() < 0.03 and not self.random_heating:
                        self.random_heating = True
                        self.target_temp = random.uniform(95.0, 150.0)
                        print(f"[{self.name}] 🔥 Aquecimento aleatório iniciado (alvo: {self.target_temp:.1f}°C)")
                
                base_temp = 25.0 + abs(velocity) * 2.0 + abs(accel_cmd) * 5.0
                
                if self.random_heating:
                    self.temperature += (self.target_temp - self.temperature) * 0.05
                else:
                    self.temperature = base_temp
                
                sensor_values = {
                    'position_x': x,
                    'position_y': y,
                    'theta': theta,
                    'velocity': velocity,
                    'temperature': self.temperature
                }
                
                if self.enable_noise:
                    sensor_values = self.noise.add_noise_dict(sensor_values)
                
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
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.simulation_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Simulação finalizada")
    
    def get_sensor_data(self) -> SensorData:
        return self.current_sensor_data
    
    def inject_electrical_fault(self, fault: bool = True):
        self.electrical_fault = fault
        print(f"[{self.name}] Falha elétrica {'INJETADA' if fault else 'REMOVIDA'}")
    
    def inject_hydraulic_fault(self, fault: bool = True):
        self.hydraulic_fault = fault
        print(f"[{self.name}] Falha hidráulica {'INJETADA' if fault else 'REMOVIDA'}")
    
    def reset_temperature(self):
        self.random_heating = False
        self.temperature = 25.0
        self.target_temp = 25.0
        print(f"[{self.name}] 🌡️ Temperatura resetada para normal")
    
    def set_position(self, x: float, y: float, theta: float = 0.0):
        self.dynamics.set_position(x, y, theta)
    
    def emergency_stop(self):
        self.dynamics.emergency_stop()
    
    def stop(self):
        self._stop_event.set()

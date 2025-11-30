import threading
import time
import math
from typing import Dict, Tuple, Optional
from src.embedded.sync.shared_state import SharedState
from src.embedded.sync.event_manager import EventManager, EventType

class CollisionAvoidanceTask(threading.Thread):
    def __init__(self,
                 shared_state: SharedState,
                 event_manager: EventManager,
                 check_period: float = 0.1,
                 safety_distance: float = 5.0,
                 warning_distance: float = 10.0):
        super().__init__(name="CollisionAvoidance", daemon=True)
        
        self.shared_state = shared_state
        self.event_manager = event_manager
        self.check_period = check_period
        self.safety_distance = safety_distance 
        self.warning_distance = warning_distance
        self._stop_event = threading.Event()
        
        self.avoidance_active = False
        self.closest_truck_id = None
        self.closest_distance = float('inf')
    
    def run(self):
        print(f"[{self.name}] Tarefa iniciada (safety_distance={self.safety_distance}m, warning_distance={self.warning_distance}m)")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                state = self.shared_state.get_state()
                
                if state.is_automatic():
                    self._check_collisions()
                else:
                    if self.avoidance_active:
                        self.avoidance_active = False
                        print(f"[{self.name}] Desvio desativado (modo manual)")
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.check_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _check_collisions(self):
        state = self.shared_state.get_state()
        my_pos = (state.position_x, state.position_y)
        my_velocity = state.velocity
        my_theta = state.theta
        
        other_trucks = self.shared_state.get_other_trucks_positions()
        
        if not other_trucks:
            if self.avoidance_active:
                self.avoidance_active = False
                self.closest_truck_id = None
                self.closest_distance = float('inf')
            return
        
        closest_truck = None
        min_distance = float('inf')
        
        for truck_id, truck_data in other_trucks.items():
            other_pos = (truck_data['x'], truck_data['y'])
            distance = self._calculate_distance(my_pos, other_pos)
            
            if self._is_in_trajectory(my_pos, my_theta, other_pos, distance):
                if distance < min_distance:
                    min_distance = distance
                    closest_truck = {
                        'id': truck_id,
                        'distance': distance,
                        'position': other_pos
                    }
        
        self.closest_distance = min_distance
        
        if closest_truck is None:
            if self.avoidance_active:
                self.avoidance_active = False
                self.closest_truck_id = None
                print(f"[{self.name}] Caminho livre - desvio desativado")
        
        elif min_distance < self.safety_distance:
            if not self.avoidance_active or self.closest_truck_id != closest_truck['id']:
                self.avoidance_active = True
                self.closest_truck_id = closest_truck['id']
                print(f"[{self.name}] ⚠️ ALERTA: Caminhão {closest_truck['id']} muito próximo ({min_distance:.1f}m) - PARANDO")
            
            self.shared_state.set_setpoints(0.0, None)
        
        elif min_distance < self.warning_distance:
            if not self.avoidance_active or self.closest_truck_id != closest_truck['id']:
                self.avoidance_active = True
                self.closest_truck_id = closest_truck['id']
                print(f"[{self.name}] ⚡ Caminhão {closest_truck['id']} detectado ({min_distance:.1f}m) - REDUZINDO VELOCIDADE")
            
            reduction_factor = (min_distance - self.safety_distance) / (self.warning_distance - self.safety_distance)
            reduction_factor = max(0.3, min(1.0, reduction_factor))
            
            current_setpoint = state.velocity_setpoint
            reduced_velocity = current_setpoint * reduction_factor
            
            avoidance_angle = self._calculate_avoidance_angle(my_pos, my_theta, closest_truck['position'])
            
            self.shared_state.set_setpoints(reduced_velocity, avoidance_angle)
        
        else:
            if self.avoidance_active:
                self.avoidance_active = False
                self.closest_truck_id = None
                print(f"[{self.name}] Distância segura recuperada ({min_distance:.1f}m)")
    
    def _calculate_distance(self, pos1: Tuple[float, float], pos2: Tuple[float, float]) -> float:
        return math.sqrt((pos2[0] - pos1[0])**2 + (pos2[1] - pos1[1])**2)
    
    def _is_in_trajectory(self, my_pos: Tuple[float, float], my_theta: float, 
                          other_pos: Tuple[float, float], distance: float) -> bool:
        dx = other_pos[0] - my_pos[0]
        dy = other_pos[1] - my_pos[1]
        
        angle_to_other = math.atan2(dy, dx)
        
        angle_diff = angle_to_other - my_theta
        angle_diff = math.atan2(math.sin(angle_diff), math.cos(angle_diff))
        
        max_angle = math.pi / 4
        
        in_cone = abs(angle_diff) < max_angle
        in_range = distance < self.warning_distance * 2
        
        return in_cone and in_range
    
    def _calculate_avoidance_angle(self, my_pos: Tuple[float, float], my_theta: float,
                                   other_pos: Tuple[float, float]) -> float:
        dx = other_pos[0] - my_pos[0]
        dy = other_pos[1] - my_pos[1]
        
        angle_to_other = math.atan2(dy, dx)

        angle_diff = angle_to_other - my_theta
        cross = math.sin(angle_diff)
        
        avoidance_offset = math.pi / 6
        
        if cross > 0:
            return my_theta - avoidance_offset
        else:
            return my_theta + avoidance_offset
    
    def get_avoidance_status(self) -> Dict:
        return {
            'active': self.avoidance_active,
            'closest_truck_id': self.closest_truck_id,
            'closest_distance': self.closest_distance if self.closest_distance != float('inf') else None
        }
    
    def reset_avoidance(self):
        self.avoidance_active = False
        self.closest_truck_id = None
        self.closest_distance = float('inf')
        print(f"[{self.name}] Estado de desvio resetado")
    
    def stop(self):
        self._stop_event.set()

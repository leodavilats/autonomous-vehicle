import threading
import time
import math
import queue
from typing import Tuple, Optional, List
from src.embedded.sync.shared_state import SharedState
from src.embedded.sync.event_manager import EventManager, EventType

class RoutePlanningTask(threading.Thread):
    
    def __init__(self,
                 shared_state: SharedState,
                 event_manager: EventManager,
                 waypoint_queue: queue.Queue,
                 planning_period: float = 0.5,
                 waypoint_threshold: float = 1.0):
        super().__init__(name="RoutePlanning", daemon=True)
        
        self.shared_state = shared_state
        self.event_manager = event_manager
        self.waypoint_queue = waypoint_queue
        self.planning_period = planning_period
        self.waypoint_threshold = waypoint_threshold
        self._stop_event = threading.Event()
        
        self.route: List[Tuple[float, float]] = []
        self.current_waypoint_idx = 0
        self._route_saved_before_fault = False
    
    def run(self):
        print(f"[{self.name}] Tarefa iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:

                self._check_new_route()
                
                state = self.shared_state.get_state()
                
                self._check_fault_recovery(state)
                
                if self.route and state.is_automatic() and not state.has_fault():
                    self._update_setpoints()
                elif state.has_fault() and self.route and not self._route_saved_before_fault:
                    self._save_route_state()
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.planning_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _check_new_route(self):
        try:
            new_route = self.waypoint_queue.get_nowait()
            self.route = new_route
            self.current_waypoint_idx = 0
            self._route_saved_before_fault = False
            print(f"[{self.name}] Nova rota recebida com {len(self.route)} waypoints")
            self.event_manager.emit(EventType.NEW_ROUTE, {"waypoints": len(self.route)})
        except queue.Empty:
            pass
    
    def _update_setpoints(self):
        if self.current_waypoint_idx >= len(self.route):

            print(f"[{self.name}] Rota completa")
            self.shared_state.set_setpoints(0.0, None)
            self.event_manager.emit(EventType.TARGET_REACHED, {})
            self.route = []
            return
        
        x, y, theta, velocity = self.shared_state.get_position()
        
        target_x, target_y = self.route[self.current_waypoint_idx]
        
        distance = math.sqrt((target_x - x)**2 + (target_y - y)**2)
        
        if distance < self.waypoint_threshold:

            print(f"[{self.name}] Waypoint {self.current_waypoint_idx + 1}/{len(self.route)} alcançado")
            self.current_waypoint_idx += 1
            if self.current_waypoint_idx >= len(self.route):
                return
            target_x, target_y = self.route[self.current_waypoint_idx]
            distance = math.sqrt((target_x - x)**2 + (target_y - y)**2)
        
        desired_theta = math.atan2(target_y - y, target_x - x)
        
        max_velocity = 5.0
        desired_velocity = min(max_velocity, distance * 0.5)
        desired_velocity = max(0.5, desired_velocity)
        
        self.shared_state.set_setpoints(desired_velocity, desired_theta)
        self.shared_state.set_target(target_x, target_y)
    
    def add_waypoint(self, x: float, y: float):
        try:
            self.waypoint_queue.put_nowait([(x, y)])
        except queue.Full:
            print(f"[{self.name}] Fila de waypoints cheia")
    
    def set_route(self, waypoints: List[Tuple[float, float]]):
        try:
            self.waypoint_queue.put_nowait(waypoints)
        except queue.Full:
            print(f"[{self.name}] Fila de waypoints cheia")
    
    def _save_route_state(self):
        if self.route:
            self.shared_state.save_route(self.route, self.current_waypoint_idx)
            self._route_saved_before_fault = True
            print(f"[{self.name}] Rota salva para restauração: {len(self.route)} waypoints, índice atual: {self.current_waypoint_idx}")
    
    def _check_fault_recovery(self, state):
        if not state.has_fault() and self._route_saved_before_fault:
            saved_route, saved_idx = self.shared_state.get_saved_route()
            if saved_route:
                self.route = saved_route
                self.current_waypoint_idx = saved_idx
                print(f"[{self.name}] Rota restaurada: {len(self.route)} waypoints, índice {self.current_waypoint_idx}")
                self.event_manager.emit(EventType.NEW_ROUTE, {"waypoints": len(self.route)})
            self._route_saved_before_fault = False
    
    def stop(self):
        self._stop_event.set()

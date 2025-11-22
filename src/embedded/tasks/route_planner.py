"""
Tarefa de Planejamento de Rota
Recebe pontos inicial/final e define setpoints para controle
"""

import threading
import time
import math
import queue
from typing import Tuple, Optional, List
from src.embedded.sync.shared_state import SharedState
from src.embedded.sync.event_manager import EventManager, EventType


class RoutePlanningTask(threading.Thread):
    """
    Tarefa de Planejamento de Rota
    
    Responsabilidades:
    - Receber pontos inicial e final (do sistema de Gestão da Mina)
    - Calcular trajetória
    - Definir setpoints de velocidade e posição angular
    - Atualizar conforme veículo se move
    """
    
    def __init__(self,
                 shared_state: SharedState,
                 event_manager: EventManager,
                 waypoint_queue: queue.Queue,
                 planning_period: float = 0.5,
                 waypoint_threshold: float = 1.0):
        """
        Args:
            shared_state: Estado compartilhado do veículo
            event_manager: Gerenciador de eventos
            waypoint_queue: Fila de waypoints (x, y) recebidos da central
            planning_period: Período de replanejamento (segundos)
            waypoint_threshold: Distância para considerar waypoint alcançado (m)
        """
        super().__init__(name="RoutePlanning", daemon=True)
        
        self.shared_state = shared_state
        self.event_manager = event_manager
        self.waypoint_queue = waypoint_queue
        self.planning_period = planning_period
        self.waypoint_threshold = waypoint_threshold
        self._stop_event = threading.Event()
        
        # Rota atual (lista de waypoints)
        self.route: List[Tuple[float, float]] = []
        self.current_waypoint_idx = 0
    
    def run(self):
        """Loop principal da tarefa"""
        print(f"[{self.name}] Tarefa iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                # 1. Verifica se há nova rota
                self._check_new_route()
                
                # 2. Se há rota ativa, calcula setpoints
                if self.route and self.shared_state.is_automatic():
                    self._update_setpoints()
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            # Aguarda próximo ciclo
            elapsed = time.time() - start_time
            sleep_time = max(0, self.planning_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _check_new_route(self):
        """Verifica se há nova rota na fila"""
        try:
            new_route = self.waypoint_queue.get_nowait()
            self.route = new_route
            self.current_waypoint_idx = 0
            print(f"[{self.name}] Nova rota recebida com {len(self.route)} waypoints")
            self.event_manager.emit(EventType.NEW_ROUTE, {"waypoints": len(self.route)})
        except queue.Empty:
            pass
    
    def _update_setpoints(self):
        """Atualiza setpoints baseado na rota"""
        if self.current_waypoint_idx >= len(self.route):
            # Rota completa
            print(f"[{self.name}] Rota completa")
            self.shared_state.set_setpoints(0.0, None)  # Para o veículo
            self.event_manager.emit(EventType.TARGET_REACHED, {})
            self.route = []
            return
        
        # Obtém posição atual
        x, y, theta, velocity = self.shared_state.get_position()
        
        # Waypoint alvo
        target_x, target_y = self.route[self.current_waypoint_idx]
        
        # Verifica se alcançou waypoint atual
        distance = math.sqrt((target_x - x)**2 + (target_y - y)**2)
        
        if distance < self.waypoint_threshold:
            # Alcançou waypoint, avança para próximo
            print(f"[{self.name}] Waypoint {self.current_waypoint_idx + 1}/{len(self.route)} alcançado")
            self.current_waypoint_idx += 1
            if self.current_waypoint_idx >= len(self.route):
                return  # Rota completa
            target_x, target_y = self.route[self.current_waypoint_idx]
            distance = math.sqrt((target_x - x)**2 + (target_y - y)**2)
        
        # Calcula ângulo desejado (direção para o waypoint)
        desired_theta = math.atan2(target_y - y, target_x - x)
        
        # Calcula velocidade desejada (proporcional à distância)
        # Velocidade máxima de 5 m/s, reduz perto do alvo
        max_velocity = 5.0
        desired_velocity = min(max_velocity, distance * 0.5)
        desired_velocity = max(0.5, desired_velocity)  # Velocidade mínima
        
        # Atualiza setpoints
        self.shared_state.set_setpoints(desired_velocity, desired_theta)
        self.shared_state.set_target(target_x, target_y)
    
    def add_waypoint(self, x: float, y: float):
        """Adiciona waypoint à rota atual"""
        try:
            self.waypoint_queue.put_nowait([(x, y)])
        except queue.Full:
            print(f"[{self.name}] Fila de waypoints cheia")
    
    def set_route(self, waypoints: List[Tuple[float, float]]):
        """Define nova rota completa"""
        try:
            self.waypoint_queue.put_nowait(waypoints)
        except queue.Full:
            print(f"[{self.name}] Fila de waypoints cheia")
    
    def stop(self):
        """Para a tarefa"""
        self._stop_event.set()

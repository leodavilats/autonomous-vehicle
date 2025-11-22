"""
Tarefa de Controle de Navegação
Executa controladores PID de velocidade e posição angular
"""

import threading
import time
from src.embedded.sync.shared_state import SharedState
from src.embedded.sync.event_manager import EventManager, EventType
from src.embedded.control.velocity_controller import VelocityController
from src.embedded.control.angular_controller import AngularController
from src.models.vehicle_state import VehicleStatus


class NavigationControlTask(threading.Thread):
    """
    Tarefa de Controle de Navegação
    
    Responsabilidades:
    - Executar controlador PID de velocidade
    - Executar controlador PID de posição angular
    - Implementar bumpless transfer (modo manual -> automático)
    - Receber eventos de falha
    - Atualizar comandos dos atuadores
    """
    
    def __init__(self,
                 shared_state: SharedState,
                 event_manager: EventManager,
                 control_period: float = 0.05):
        """
        Args:
            shared_state: Estado compartilhado do veículo
            event_manager: Gerenciador de eventos
            control_period: Período de controle (segundos) - 50ms típico
        """
        super().__init__(name="NavigationControl", daemon=True)
        
        self.shared_state = shared_state
        self.event_manager = event_manager
        self.control_period = control_period
        self._stop_event = threading.Event()
        
        # Controladores PID
        self.velocity_controller = VelocityController(kp=0.5, ki=0.1, kd=0.05)
        self.angular_controller = AngularController(kp=1.0, ki=0.05, kd=0.2)
        
        # Estado anterior para detectar transições
        self._prev_mode_automatic = False
    
    def run(self):
        """Loop principal da tarefa"""
        print(f"[{self.name}] Tarefa iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                # Obtém estado atual
                state = self.shared_state.get_state()
                
                # Verifica transição de modo
                if state.is_automatic() and not self._prev_mode_automatic:
                    # Transição manual -> automático: bumpless transfer
                    self._enable_controllers(state.velocity, state.theta)
                    print(f"[{self.name}] Controladores ativados (bumpless transfer)")
                elif not state.is_automatic() and self._prev_mode_automatic:
                    # Transição automático -> manual
                    self._disable_controllers()
                    print(f"[{self.name}] Controladores desativados")
                
                self._prev_mode_automatic = state.is_automatic()
                
                # Executa controle se em modo automático e sem falhas críticas
                if state.is_automatic() and state.status != VehicleStatus.EMERGENCY:
                    self._execute_control(state)
                elif state.is_manual():
                    # Em modo manual, atualiza setpoints para bumpless transfer
                    self.shared_state.set_setpoints(state.velocity, state.theta)
                
                # Verifica eventos de falha
                self._check_fault_events()
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            # Aguarda próximo ciclo
            elapsed = time.time() - start_time
            sleep_time = max(0, self.control_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _enable_controllers(self, current_velocity: float, current_angle: float):
        """Ativa controladores com bumpless transfer"""
        self.velocity_controller.enable(current_velocity)
        self.angular_controller.enable(current_angle)
    
    def _disable_controllers(self):
        """Desativa controladores"""
        self.velocity_controller.disable()
        self.angular_controller.disable()
    
    def _execute_control(self, state):
        """Executa lógica de controle"""
        # Controlador de velocidade
        accel_cmd = self.velocity_controller.compute(
            state.velocity,
            state.velocity_setpoint
        )
        
        # Controlador de posição angular
        steer_cmd = self.angular_controller.compute(
            state.theta,
            state.angular_setpoint
        )
        
        # Atualiza atuadores
        self.shared_state.set_actuators(accel_cmd, steer_cmd)
    
    def _check_fault_events(self):
        """Verifica eventos de falha e desativa controle se necessário"""
        event = self.event_manager.check_event(EventType.EMERGENCY_STOP)
        if event:
            print(f"[{self.name}] Emergência detectada - parando controle")
            self._disable_controllers()
            self.shared_state.set_actuators(0.0, 0.0)
    
    def stop(self):
        """Para a tarefa"""
        self._stop_event.set()

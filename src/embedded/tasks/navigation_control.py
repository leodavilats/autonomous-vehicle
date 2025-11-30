import threading
import time
from src.embedded.sync.shared_state import SharedState
from src.embedded.sync.event_manager import EventManager, EventType
from src.embedded.control.velocity_controller import VelocityController
from src.embedded.control.angular_controller import AngularController
from src.models.vehicle_state import VehicleStatus

class NavigationControlTask(threading.Thread):
    
    def __init__(self,
                 shared_state: SharedState,
                 event_manager: EventManager,
                 control_period: float = 0.05):
        super().__init__(name="NavigationControl", daemon=True)
        
        self.shared_state = shared_state
        self.event_manager = event_manager
        self.control_period = control_period
        self._stop_event = threading.Event()
        
        self.velocity_controller = VelocityController(kp=0.5, ki=0.1, kd=0.05)
        self.angular_controller = AngularController(kp=1.0, ki=0.05, kd=0.2)
        
        self._prev_mode_automatic = False
        self._prev_had_fault = False
    
    def run(self):
        print(f"[{self.name}] Tarefa iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:

                state = self.shared_state.get_state()
                
                if self._prev_had_fault and not state.has_fault() and state.is_automatic():
                    self._enable_controllers(state.velocity, state.theta)
                    print(f"[{self.name}] Controladores reabilitados")
                
                if state.is_automatic() and not self._prev_mode_automatic:

                    self._enable_controllers(state.velocity, state.theta)
                    print(f"[{self.name}] Controladores ativados (bumpless transfer)")
                elif not state.is_automatic() and self._prev_mode_automatic:

                    self._disable_controllers()
                    print(f"[{self.name}] Controladores desativados")
                
                self._prev_mode_automatic = state.is_automatic()
                self._prev_had_fault = state.has_fault()
                
                if state.is_automatic() and state.status not in [VehicleStatus.EMERGENCY, VehicleStatus.FAULT]:
                    self._execute_control(state)
                elif state.is_manual() and state.status != VehicleStatus.FAULT:

                    self.shared_state.set_setpoints(state.velocity, state.theta)
                
                self._check_fault_events()
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.control_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _enable_controllers(self, current_velocity: float, current_angle: float):
        self.velocity_controller.enable(current_velocity)
        self.angular_controller.enable(current_angle)
    
    def _disable_controllers(self):
        self.velocity_controller.disable()
        self.angular_controller.disable()
    
    def _execute_control(self, state):

        accel_cmd = self.velocity_controller.compute(
            state.velocity,
            state.velocity_setpoint
        )
        
        steer_cmd = self.angular_controller.compute(
            state.theta,
            state.angular_setpoint
        )
        
        self.shared_state.set_actuators(accel_cmd, steer_cmd)
    
    def _check_fault_events(self):
        event = self.event_manager.check_event(EventType.EMERGENCY_STOP)
        if event:
            print(f"[{self.name}] Emergência detectada - parando controle")
            self._disable_controllers()
            self.shared_state.set_actuators(0.0, 0.0)
        
        event = self.event_manager.check_event(EventType.TEMPERATURE_FAULT)
        if event:
            print(f"[{self.name}] Falha de temperatura detectada - parando controle")
            self._disable_controllers()
            self.shared_state.set_actuators(0.0, 0.0)
        
        event = self.event_manager.check_event(EventType.ELECTRICAL_FAULT)
        if event:
            print(f"[{self.name}] Falha elétrica detectada - parando controle")
            self._disable_controllers()
            self.shared_state.set_actuators(0.0, 0.0)
        
        event = self.event_manager.check_event(EventType.HYDRAULIC_FAULT)
        if event:
            print(f"[{self.name}] Falha hidráulica detectada - parando controle")
            self._disable_controllers()
            self.shared_state.set_actuators(0.0, 0.0)
    
    def stop(self):
        self._stop_event.set()

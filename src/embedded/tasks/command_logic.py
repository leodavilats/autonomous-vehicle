import threading
import time
import queue
from typing import Optional
from src.models.command import Command, CommandType
from src.models.vehicle_state import OperationMode, VehicleStatus
from src.embedded.sync.circular_buffer import CircularBuffer
from src.embedded.sync.shared_state import SharedState
from src.embedded.sync.event_manager import EventManager, EventType

class CommandLogicTask(threading.Thread):
    
    def __init__(self,
                 circular_buffer: CircularBuffer,
                 shared_state: SharedState,
                 event_manager: EventManager,
                 command_queue: queue.Queue,
                 update_period: float = 0.1,
                 fault_generator = None,
                 simulator = None):
        super().__init__(name="CommandLogic", daemon=True)
        
        self.circular_buffer = circular_buffer
        self.shared_state = shared_state
        self.event_manager = event_manager
        self.command_queue = command_queue
        self.update_period = update_period
        self.fault_generator = fault_generator
        self.simulator = simulator
        self._stop_event = threading.Event()
        
        self._pre_fault_velocity_sp = 0.0
        self._pre_fault_angular_sp = 0.0
        self._pre_fault_target_x = None
        self._pre_fault_target_y = None
        self._pre_fault_mode = None
    
    def run(self):
        print(f"[{self.name}] Tarefa iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:

                self._process_commands()
                
                latest_data = self.circular_buffer.read_latest()
                
                if latest_data:

                    self.shared_state.set_position(
                        latest_data.position_x,
                        latest_data.position_y,
                        latest_data.theta,
                        latest_data.velocity
                    )
                    
                    self.shared_state.set_faults(
                        temperature=latest_data.temperature,
                        electrical=latest_data.electrical_fault,
                        hydraulic=latest_data.hydraulic_fault
                    )
                
                self._update_vehicle_status()
                
                self._check_fault_events()
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            elapsed = time.time() - start_time
            sleep_time = max(0, self.update_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _process_commands(self):
        while not self.command_queue.empty():
            try:
                command = self.command_queue.get_nowait()
                self._execute_command(command)
            except queue.Empty:
                break
    
    def _execute_command(self, command: Command):
        print(f"[{self.name}] Executando comando: {command}")
        
        if command.command_type == CommandType.ENABLE_AUTOMATIC:

            self.shared_state.set_mode(OperationMode.AUTOMATIC_REMOTE)
            self.shared_state.set_actuators(0.0, 0.0)
            self.shared_state.set_setpoints(0.0, 0.0)
            self.event_manager.emit(EventType.MODE_CHANGED, {"mode": "AUTOMATIC"})
            print(f"[{self.name}] Modo AUTOMÁTICO ativado - veículo parado")
        
        elif command.command_type == CommandType.DISABLE_AUTOMATIC:

            self.shared_state.set_mode(OperationMode.MANUAL_LOCAL)
            self.shared_state.set_actuators(0.0, 0.0)
            self.shared_state.set_setpoints(0.0, 0.0)
            self.event_manager.emit(EventType.MODE_CHANGED, {"mode": "MANUAL"})
            print(f"[{self.name}] Modo MANUAL ativado - veículo parado")
        
        elif command.command_type == CommandType.EMERGENCY_STOP:

            self.shared_state.set_faults(emergency=True)
            self.shared_state.set_status(VehicleStatus.EMERGENCY)
            self.shared_state.set_actuators(0.0, 0.0)
            self.event_manager.emit(EventType.EMERGENCY_STOP, {})
            print(f"[{self.name}] EMERGÊNCIA ACIONADA")
        
        elif command.command_type == CommandType.RESET_EMERGENCY:

            self.shared_state.set_faults(emergency=False)
            self.shared_state.set_status(VehicleStatus.STOPPED)
            self.event_manager.emit(EventType.EMERGENCY_RESET, {})
            print(f"[{self.name}] Emergência resetada - status: STOPPED")
        
        elif command.command_type == CommandType.RESET_FAULT:
            if self.fault_generator:
                self.fault_generator.clear_all_faults()
            
            if self.simulator and hasattr(self.simulator, 'reset_temperature'):
                self.simulator.reset_temperature()
            
            self.shared_state.set_faults(electrical=False, hydraulic=False, emergency=False)
            self.shared_state.set_status(VehicleStatus.STOPPED)
            
            if self._pre_fault_mode:
                self.shared_state.set_mode(self._pre_fault_mode)
                print(f"[{self.name}] Modo restaurado: {self._pre_fault_mode.name}")
            
            if self._pre_fault_target_x is not None and self._pre_fault_target_y is not None:
                self.shared_state.set_target(self._pre_fault_target_x, self._pre_fault_target_y)
                print(f"[{self.name}] Alvo restaurado: ({self._pre_fault_target_x:.1f}, {self._pre_fault_target_y:.1f})")
            
            self.shared_state.set_setpoints(
                velocity_sp=self._pre_fault_velocity_sp,
                angular_sp=self._pre_fault_angular_sp
            )
            
            state = self.shared_state.get_state()
            print(f"[{self.name}] Sistema REARMADO - Status: {state.status.name}, Modo: {state.mode.name}")
            self.event_manager.emit(EventType.FAULT_CLEARED, {"type": "manual_reset"})
        
        elif command.command_type == CommandType.STOP:

            self.shared_state.set_actuators(0.0, 0.0)
            self.shared_state.set_setpoints(0.0, 0.0)
            print(f"[{self.name}] Veículo parado")
        
        elif command.command_type == CommandType.SHUTDOWN:

            self.event_manager.emit(EventType.SHUTDOWN, {})
            print(f"[{self.name}] Shutdown solicitado")
        
        elif self.shared_state.is_manual():
            if command.command_type == CommandType.ACCELERATE:
                self.shared_state.set_actuators(command.value or 0.5, 0.0)
            elif command.command_type == CommandType.BRAKE:
                self.shared_state.set_actuators(command.value or -0.5, 0.0)
            elif command.command_type == CommandType.STEER_LEFT:
                accel, _ = self.shared_state.get_actuators()
                self.shared_state.set_actuators(accel, command.value or 0.5)
            elif command.command_type == CommandType.STEER_RIGHT:
                accel, _ = self.shared_state.get_actuators()
                self.shared_state.set_actuators(accel, command.value or -0.5)
            elif command.command_type == CommandType.MOVE_FORWARD:
                self.shared_state.set_actuators(command.value or 0.5, 0.0)
                print(f"[{self.name}] Movendo para frente")
            elif command.command_type == CommandType.MOVE_BACKWARD:
                self.shared_state.set_actuators(command.value or -0.5, 0.0)
                print(f"[{self.name}] Movendo para trás")
            elif command.command_type == CommandType.TURN_LEFT:
                accel, _ = self.shared_state.get_actuators()
                self.shared_state.set_actuators(accel, command.value or 0.5)
                print(f"[{self.name}] Girando à esquerda")
            elif command.command_type == CommandType.TURN_RIGHT:
                accel, _ = self.shared_state.get_actuators()
                self.shared_state.set_actuators(accel, command.value or -0.5)
                print(f"[{self.name}] Girando à direita")
    
    def _update_vehicle_status(self):
        state = self.shared_state.get_state()
        
        if state.emergency_stop:
            self.shared_state.set_status(VehicleStatus.EMERGENCY)
        elif state.has_fault():
            self.shared_state.set_status(VehicleStatus.FAULT)
        else:

            is_moving = (
                abs(state.velocity) > 0.1 or
                (state.is_automatic() and abs(state.velocity_setpoint) > 0.1) or
                abs(state.acceleration_cmd) > 0.01
            )
            
            if is_moving:
                self.shared_state.set_status(VehicleStatus.RUNNING)
            else:
                self.shared_state.set_status(VehicleStatus.STOPPED)
    
    def _check_fault_events(self):

        event = self.event_manager.check_event(EventType.TEMPERATURE_FAULT)
        if event:
            print(f"[{self.name}] Falha de temperatura recebida - PARANDO VEÍCULO")
            self._save_state_before_fault()
            self.shared_state.set_actuators(0.0, 0.0)
            self.shared_state.set_setpoints(0.0, 0.0)
        
        event = self.event_manager.check_event(EventType.ELECTRICAL_FAULT)
        if event:
            print(f"[{self.name}] Falha elétrica recebida - PARANDO VEÍCULO")
            self._save_state_before_fault()
            self.shared_state.set_actuators(0.0, 0.0)
            self.shared_state.set_setpoints(0.0, 0.0)
        
        event = self.event_manager.check_event(EventType.HYDRAULIC_FAULT)
        if event:
            print(f"[{self.name}] Falha hidráulica recebida - PARANDO VEÍCULO")
            self._save_state_before_fault()
            self.shared_state.set_actuators(0.0, 0.0)
            self.shared_state.set_setpoints(0.0, 0.0)
    
    def _save_state_before_fault(self):
        """Salva o estado atual para retomar após rearme"""
        state = self.shared_state.get_state()
        self._pre_fault_velocity_sp = state.velocity_setpoint
        self._pre_fault_angular_sp = state.angular_setpoint
        self._pre_fault_target_x = state.target_x
        self._pre_fault_target_y = state.target_y
        self._pre_fault_mode = state.mode
        print(f"[{self.name}] Estado salvo para rearme futuro")
    
    def stop(self):
        self._stop_event.set()

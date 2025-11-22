"""
Tarefa de Lógica de Comando
Determina estado do veículo e processa comandos do operador/central
"""

import threading
import time
import queue
from src.models.command import Command, CommandType
from src.models.vehicle_state import OperationMode, VehicleStatus
from src.embedded.sync.circular_buffer import CircularBuffer
from src.embedded.sync.shared_state import SharedState
from src.embedded.sync.event_manager import EventManager, EventType


class CommandLogicTask(threading.Thread):
    """
    Tarefa de Lógica de Comando
    
    Responsabilidades:
    - Ler dados do buffer circular (sensores tratados)
    - Determinar estado do veículo (manual/automático, funcionando/defeito)
    - Processar comandos do operador e sistema central
    - Atualizar estado compartilhado
    """
    
    def __init__(self,
                 circular_buffer: CircularBuffer,
                 shared_state: SharedState,
                 event_manager: EventManager,
                 command_queue: queue.Queue,
                 update_period: float = 0.1):
        """
        Args:
            circular_buffer: Buffer com dados dos sensores filtrados
            shared_state: Estado compartilhado do veículo
            event_manager: Gerenciador de eventos
            command_queue: Fila de comandos a processar
            update_period: Período de atualização (segundos)
        """
        super().__init__(name="CommandLogic", daemon=True)
        
        self.circular_buffer = circular_buffer
        self.shared_state = shared_state
        self.event_manager = event_manager
        self.command_queue = command_queue
        self.update_period = update_period
        self._stop_event = threading.Event()
    
    def run(self):
        """Loop principal da tarefa"""
        print(f"[{self.name}] Tarefa iniciada")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                # 1. Processa comandos pendentes
                self._process_commands()
                
                # 2. Lê dados do buffer circular
                latest_data = self.circular_buffer.read_latest()
                
                if latest_data:
                    # 3. Atualiza posição no estado compartilhado
                    self.shared_state.set_position(
                        latest_data.position_x,
                        latest_data.position_y,
                        latest_data.theta,
                        latest_data.velocity
                    )
                    
                    # 4. Atualiza falhas
                    self.shared_state.set_faults(
                        temperature=latest_data.temperature,
                        electrical=latest_data.electrical_fault,
                        hydraulic=latest_data.hydraulic_fault
                    )
                
                # 5. Determina status do veículo
                self._update_vehicle_status()
                
                # 6. Verifica eventos de falha
                self._check_fault_events()
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            # Aguarda próximo ciclo
            elapsed = time.time() - start_time
            sleep_time = max(0, self.update_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _process_commands(self):
        """Processa todos os comandos pendentes na fila"""
        while not self.command_queue.empty():
            try:
                command = self.command_queue.get_nowait()
                self._execute_command(command)
            except queue.Empty:
                break
    
    def _execute_command(self, command: Command):
        """Executa um comando específico"""
        print(f"[{self.name}] Executando comando: {command}")
        
        if command.command_type == CommandType.ENABLE_AUTOMATIC:
            # Ativa modo automático
            self.shared_state.set_mode(OperationMode.AUTOMATIC_REMOTE)
            self.event_manager.emit(EventType.MODE_CHANGED, {"mode": "AUTOMATIC"})
            print(f"[{self.name}] Modo AUTOMÁTICO ativado")
        
        elif command.command_type == CommandType.DISABLE_AUTOMATIC:
            # Volta para modo manual
            self.shared_state.set_mode(OperationMode.MANUAL_LOCAL)
            self.event_manager.emit(EventType.MODE_CHANGED, {"mode": "MANUAL"})
            print(f"[{self.name}] Modo MANUAL ativado")
        
        elif command.command_type == CommandType.EMERGENCY_STOP:
            # Parada de emergência
            self.shared_state.set_faults(emergency=True)
            self.shared_state.set_status(VehicleStatus.EMERGENCY)
            self.shared_state.set_actuators(0.0, 0.0)
            self.event_manager.emit(EventType.EMERGENCY_STOP, {})
            print(f"[{self.name}] EMERGÊNCIA ACIONADA")
        
        elif command.command_type == CommandType.RESET_EMERGENCY:
            # Reseta emergência
            self.shared_state.set_faults(emergency=False)
            self.event_manager.emit(EventType.EMERGENCY_RESET, {})
            print(f"[{self.name}] Emergência resetada")
        
        elif command.command_type == CommandType.STOP:
            # Parar veículo
            self.shared_state.set_actuators(0.0, 0.0)
            self.shared_state.set_setpoints(0.0, 0.0)
            print(f"[{self.name}] Veículo parado")
        
        elif command.command_type == CommandType.SHUTDOWN:
            # Desligar sistema
            self.event_manager.emit(EventType.SHUTDOWN, {})
            print(f"[{self.name}] Shutdown solicitado")
        
        # Comandos manuais (apenas em modo manual)
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
    
    def _update_vehicle_status(self):
        """Atualiza status do veículo baseado em falhas e movimento"""
        state = self.shared_state.get_state()
        
        if state.emergency_stop:
            self.shared_state.set_status(VehicleStatus.EMERGENCY)
        elif state.has_fault():
            self.shared_state.set_status(VehicleStatus.FAULT)
        else:
            # Considera RUNNING se:
            # - Velocidade significativa (> 0.1 m/s), OU
            # - Modo automático com setpoint não-zero, OU
            # - Comandos de atuadores não-zero
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
        """Verifica eventos de falha"""
        # Eventos são processados de forma não bloqueante
        event = self.event_manager.check_event(EventType.TEMPERATURE_FAULT)
        if event:
            print(f"[{self.name}] Falha de temperatura recebida")
        
        event = self.event_manager.check_event(EventType.ELECTRICAL_FAULT)
        if event:
            print(f"[{self.name}] Falha elétrica recebida")
        
        event = self.event_manager.check_event(EventType.HYDRAULIC_FAULT)
        if event:
            print(f"[{self.name}] Falha hidráulica recebida")
    
    def stop(self):
        """Para a tarefa"""
        self._stop_event.set()

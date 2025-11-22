"""
Tarefa de Interface Local
Interface de terminal para operador do caminhão
"""

import threading
import time
import queue
import sys
import os
from src.models.command import Command, CommandType
from src.embedded.sync.shared_state import SharedState
from src.embedded.tasks.data_collector import DataCollectorTask


class LocalInterfaceTask(threading.Thread):
    """
    Tarefa de Interface Local
    
    Responsabilidades:
    - Mostrar estados do sistema e medições
    - Aceitar comandos do operador via teclado
    - Comunicar com Coletor de Dados
    
    Comandos:
    [A] Ativar modo automático
    [M] Modo manual
    [W] Acelerar
    [S] Frear
    [Q] Virar esquerda
    [E] Virar direita
    [X] Parar
    [SPACE] Emergência
    [R] Reset emergência
    [ESC] Sair
    """
    
    def __init__(self,
                 shared_state: SharedState,
                 data_collector: DataCollectorTask,
                 command_queue: queue.Queue,
                 update_period: float = 0.5):
        """
        Args:
            shared_state: Estado compartilhado do veículo
            data_collector: Coletor de dados (para obter logs)
            command_queue: Fila para enviar comandos
            update_period: Período de atualização da tela (segundos)
        """
        super().__init__(name="LocalInterface", daemon=True)
        
        self.shared_state = shared_state
        self.data_collector = data_collector
        self.command_queue = command_queue
        self.update_period = update_period
        self._stop_event = threading.Event()
        
        # Buffer de comandos pendentes (Windows não tem getch não-bloqueante fácil)
        self.pending_command = None
    
    def run(self):
        """Loop principal da tarefa"""
        print(f"[{self.name}] Tarefa iniciada")
        print("\nPressione 'h' para ver comandos disponíveis\n")
        
        import msvcrt
        import math
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            # Verifica se há tecla pressionada (não-bloqueante no Windows)
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8', errors='ignore').upper()
                
                if key == 'H':
                    self._print_help()
                elif key == 'A':
                    self.send_command(CommandType.ENABLE_AUTOMATIC)
                    print("→ Modo AUTOMÁTICO ativado")
                elif key == 'M':
                    self.send_command(CommandType.DISABLE_AUTOMATIC)
                    print("→ Modo MANUAL ativado")
                elif key == 'W':
                    self.send_command(CommandType.ACCELERATE, 0.5)
                    print("→ Acelerando")
                elif key == 'S':
                    self.send_command(CommandType.BRAKE, -0.5)
                    print("→ Freando")
                elif key == 'Q':
                    self.send_command(CommandType.STEER_LEFT, 0.5)
                    print("→ Virando à esquerda")
                elif key == 'E':
                    self.send_command(CommandType.STEER_RIGHT, -0.5)
                    print("→ Virando à direita")
                elif key == 'X':
                    self.send_command(CommandType.STOP)
                    print("→ Parando veículo")
                elif key == ' ':
                    self.send_command(CommandType.EMERGENCY_STOP)
                    print("→ EMERGÊNCIA ACIONADA")
                elif key == 'R':
                    self.send_command(CommandType.RESET_EMERGENCY)
                    print("→ Emergência resetada")
                elif key == 'D':
                    # Mostra display de status
                    self._update_display()
            
            # Aguarda próximo ciclo
            elapsed = time.time() - start_time
            sleep_time = max(0, self.update_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _print_help(self):
        """Imprime ajuda de comandos"""
        print("\n" + "="*70)
        print("COMANDOS DISPONÍVEIS:")
        print("  [A] Ativar modo automático    [M] Modo manual")
        print("  [W] Acelerar                   [S] Frear")
        print("  [Q] Virar esquerda            [E] Virar direita")
        print("  [X] Parar                      [SPACE] Emergência")
        print("  [R] Reset emergência           [D] Mostrar display")
        print("  [H] Ajuda")
        print("="*70 + "\n")
    
    def _update_display(self):
        """Atualiza display de status"""
        import math
        state = self.shared_state.get_state()
        
        # Cabeçalho
        print("\n" + "="*70)
        print(f"CAMINHÃO {state.truck_id} - PAINEL DE CONTROLE".center(70))
        print("="*70)
        
        # Status principal
        print(f"\n{'MODO:':<20} {state.mode.name}")
        print(f"{'STATUS:':<20} {state.status.name}")
        
        # Posição e velocidade
        print(f"\n{'POSIÇÃO:':<20} X={state.position_x:>7.2f}m  Y={state.position_y:>7.2f}m")
        print(f"{'ORIENTAÇÃO:':<20} {math.degrees(state.theta):>7.2f}°")
        print(f"{'VELOCIDADE:':<20} {state.velocity:>7.2f} m/s")
        
        # Atuadores
        print(f"\n{'ACELERAÇÃO:':<20} {state.acceleration_cmd:>7.2f}")
        print(f"{'DIREÇÃO:':<20} {state.steering_cmd:>7.2f}")
        
        # Setpoints (modo automático)
        if state.is_automatic():
            print(f"\n{'SETPOINT VEL:':<20} {state.velocity_setpoint:>7.2f} m/s")
            print(f"{'SETPOINT ANG:':<20} {math.degrees(state.angular_setpoint):>7.2f}°")
            if state.target_x is not None:
                print(f"{'ALVO:':<20} X={state.target_x:>7.2f}m  Y={state.target_y:>7.2f}m")
        
        # Sensores de falha
        print(f"\n{'TEMPERATURA:':<20} {state.temperature:>7.1f}°C")
        print(f"{'FALHA ELÉTRICA:':<20} {'SIM' if state.electrical_fault else 'NÃO'}")
        print(f"{'FALHA HIDRÁULICA:':<20} {'SIM' if state.hydraulic_fault else 'NÃO'}")
        print(f"{'EMERGÊNCIA:':<20} {'ACIONADA' if state.emergency_stop else 'NÃO'}")
        
        print("="*70 + "\n")
    
    def send_command(self, command_type: CommandType, value: float = None):
        """Envia comando para a fila"""
        command = Command(
            command_type=command_type,
            value=value,
            timestamp=time.time(),
            source="local"
        )
        try:
            self.command_queue.put_nowait(command)
        except queue.Full:
            print("Fila de comandos cheia!")
    
    def stop(self):
        """Para a tarefa"""
        self._stop_event.set()


# Importa math para conversão de ângulos
import math

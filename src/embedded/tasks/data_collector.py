"""
Tarefa de Coletor de Dados
Coleta dados, adiciona timestamp, grava logs e publica via MQTT
"""

import threading
import time
import queue
import os
from typing import Optional
from src.models.log_entry import LogEntry
from src.embedded.sync.shared_state import SharedState
from src.embedded.sync.event_manager import EventManager, EventType


class DataCollectorTask(threading.Thread):
    """
    Tarefa de Coletor de Dados
    
    Responsabilidades:
    - Obter dados do estado do sistema
    - Atribuir timestamp
    - Armazenar em arquivos de log no disco
    - Organizar dados para Interface Local
    - Publicar dados via MQTT (será integrado depois)
    """
    
    def __init__(self,
                 shared_state: SharedState,
                 event_manager: EventManager,
                 log_dir: str = "data/logs",
                 collection_period: float = 1.0):
        """
        Args:
            shared_state: Estado compartilhado do veículo
            event_manager: Gerenciador de eventos
            log_dir: Diretório para logs
            collection_period: Período de coleta (segundos)
        """
        super().__init__(name="DataCollector", daemon=True)
        
        self.shared_state = shared_state
        self.event_manager = event_manager
        self.log_dir = log_dir
        self.collection_period = collection_period
        self._stop_event = threading.Event()
        
        # Fila de logs (thread-safe)
        self.log_queue = queue.Queue()
        
        # Cria diretório de logs se não existe
        os.makedirs(log_dir, exist_ok=True)
        
        # Arquivo de log
        state = shared_state.get_state()
        self.log_file = os.path.join(log_dir, f"truck_{state.truck_id}.csv")
        self._init_log_file()
    
    def _init_log_file(self):
        """Inicializa arquivo de log com cabeçalho"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w') as f:
                f.write(LogEntry.csv_header())
    
    def run(self):
        """Loop principal da tarefa"""
        print(f"[{self.name}] Tarefa iniciada (log: {self.log_file})")
        
        while not self._stop_event.is_set():
            start_time = time.time()
            
            try:
                # 1. Coleta dados do estado
                state = self.shared_state.get_state()
                
                # 2. Cria entrada de log
                log_entry = LogEntry(
                    timestamp=time.time(),
                    truck_id=state.truck_id,
                    status=state.status.name,
                    mode=state.mode.name,
                    position_x=state.position_x,
                    position_y=state.position_y,
                    theta=state.theta,
                    velocity=state.velocity,
                    event_description="Status normal",
                    temperature=state.temperature,
                    electrical_fault=state.electrical_fault,
                    hydraulic_fault=state.hydraulic_fault
                )
                
                # 3. Verifica eventos para logging
                log_entry = self._check_events(log_entry)
                
                # 4. Armazena em arquivo
                self._write_log(log_entry)
                
                # 5. Adiciona à fila para Interface Local
                try:
                    self.log_queue.put_nowait(log_entry)
                except queue.Full:
                    # Remove item mais antigo se fila cheia
                    try:
                        self.log_queue.get_nowait()
                        self.log_queue.put_nowait(log_entry)
                    except queue.Empty:
                        pass
                
                # 6. TODO: Publicar via MQTT (será implementado depois)
                
            except Exception as e:
                print(f"[{self.name}] Erro: {e}")
            
            # Aguarda próximo ciclo
            elapsed = time.time() - start_time
            sleep_time = max(0, self.collection_period - elapsed)
            time.sleep(sleep_time)
        
        print(f"[{self.name}] Tarefa finalizada")
    
    def _check_events(self, log_entry: LogEntry) -> LogEntry:
        """Verifica eventos e atualiza descrição do log"""
        event = self.event_manager.check_event(EventType.MODE_CHANGED)
        if event:
            mode = event.data.get("mode", "UNKNOWN")
            log_entry.event_description = f"Modo alterado para {mode}"
            return log_entry
        
        event = self.event_manager.check_event(EventType.EMERGENCY_STOP)
        if event:
            log_entry.event_description = "EMERGÊNCIA ACIONADA"
            return log_entry
        
        event = self.event_manager.check_event(EventType.EMERGENCY_RESET)
        if event:
            log_entry.event_description = "Emergência resetada"
            return log_entry
        
        event = self.event_manager.check_event(EventType.TARGET_REACHED)
        if event:
            log_entry.event_description = "Destino alcançado"
            return log_entry
        
        return log_entry
    
    def _write_log(self, log_entry: LogEntry):
        """Escreve entrada no arquivo de log"""
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_entry.to_csv_line())
        except Exception as e:
            print(f"[{self.name}] Erro ao escrever log: {e}")
    
    def get_latest_logs(self, n: int = 10) -> list:
        """
        Retorna os N logs mais recentes da fila
        Para Interface Local
        """
        logs = []
        for _ in range(min(n, self.log_queue.qsize())):
            try:
                logs.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        return logs
    
    def stop(self):
        """Para a tarefa"""
        self._stop_event.set()

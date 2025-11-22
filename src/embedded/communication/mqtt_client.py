"""
Cliente MQTT para comunicação com sistema central
Pub/Sub para integração veículo-central
"""

import json
import threading
from typing import Callable, Optional
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("AVISO: paho-mqtt não instalado. Comunicação MQTT desabilitada.")
    print("Instale com: pip install paho-mqtt")


class MQTTClient:
    """
    Cliente MQTT para comunicação entre caminhão e sistema central
    
    Tópicos:
    - mine/truck/{id}/state  - Estado do caminhão (publish)
    - mine/truck/{id}/position - Posição GPS (publish)
    - mine/truck/{id}/command - Comandos da central (subscribe)
    - mine/truck/{id}/setpoint - Novos setpoints (subscribe)
    - mine/truck/{id}/route - Nova rota (subscribe)
    """
    
    def __init__(self,
                 truck_id: int,
                 broker_host: str = "localhost",
                 broker_port: int = 1883,
                 qos: int = 1):
        """
        Args:
            truck_id: ID do caminhão
            broker_host: Endereço do broker MQTT
            broker_port: Porta do broker
            qos: Quality of Service (0, 1, ou 2)
        """
        self.truck_id = truck_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.qos = qos
        
        self.client = None
        self.connected = False
        self._callbacks = {}
        
        if not MQTT_AVAILABLE:
            return
        
        # Cria cliente com nova API
        try:
            self.client = mqtt.Client(
                client_id=f"truck_{truck_id}",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except (AttributeError, TypeError):
            # Fallback para versão antiga
            self.client = mqtt.Client(client_id=f"truck_{truck_id}")
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
    
    def connect(self) -> bool:
        """Conecta ao broker MQTT"""
        if not MQTT_AVAILABLE or self.client is None:
            return False
        
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()  # Thread em background
            return True
        except Exception as e:
            print(f"[MQTT] Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        """Desconecta do broker"""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback de conexão"""
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Conectado ao broker {self.broker_host}:{self.broker_port}")
            
            # Subscreve tópicos
            self.client.subscribe(f"mine/truck/{self.truck_id}/command", qos=self.qos)
            self.client.subscribe(f"mine/truck/{self.truck_id}/setpoint", qos=self.qos)
            self.client.subscribe(f"mine/truck/{self.truck_id}/route", qos=self.qos)
            print(f"[MQTT] Inscrito nos tópicos do caminhão {self.truck_id}")
        else:
            print(f"[MQTT] Falha na conexão (código {rc})")
    
    def _on_disconnect(self, client, userdata, rc, properties=None):
        """Callback de desconexão"""
        self.connected = False
        print(f"[MQTT] Desconectado (código {rc})")
    
    def _on_message(self, client, userdata, msg):
        """Callback de mensagem recebida"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        # Processa mensagem
        if topic.endswith('/command'):
            self._handle_command(payload)
        elif topic.endswith('/setpoint'):
            self._handle_setpoint(payload)
        elif topic.endswith('/route'):
            self._handle_route(payload)
    
    def _handle_command(self, payload: str):
        """Processa comando recebido"""
        if 'command' in self._callbacks:
            try:
                data = json.loads(payload)
                self._callbacks['command'](data)
            except Exception as e:
                print(f"[MQTT] Erro ao processar comando: {e}")
    
    def _handle_setpoint(self, payload: str):
        """Processa setpoint recebido"""
        if 'setpoint' in self._callbacks:
            try:
                data = json.loads(payload)
                self._callbacks['setpoint'](data)
            except Exception as e:
                print(f"[MQTT] Erro ao processar setpoint: {e}")
    
    def _handle_route(self, payload: str):
        """Processa nova rota recebida"""
        if 'route' in self._callbacks:
            try:
                data = json.loads(payload)
                self._callbacks['route'](data)
            except Exception as e:
                print(f"[MQTT] Erro ao processar rota: {e}")
    
    def publish_state(self, state_data: dict):
        """Publica estado completo do caminhão"""
        if not self.connected:
            print(f"[MQTT] Não conectado - não publicando estado")
            return
        
        topic = f"mine/truck/{self.truck_id}/state"
        payload = json.dumps(state_data)
        result = self.client.publish(topic, payload, qos=self.qos)
        
        # Debug apenas a primeira vez ou se houver erro
        if not hasattr(self, '_first_publish_done'):
            print(f"[MQTT] Primeira publicação: {topic}")
            self._first_publish_done = True
        
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"[MQTT] Erro ao publicar estado: {result.rc}")
    
    def publish_position(self, x: float, y: float, theta: float):
        """Publica posição do caminhão"""
        if not self.connected:
            return
        
        topic = f"mine/truck/{self.truck_id}/position"
        payload = json.dumps({"x": x, "y": y, "theta": theta})
        self.client.publish(topic, payload, qos=self.qos)
    
    def register_callback(self, message_type: str, callback: Callable):
        """
        Registra callback para tipo de mensagem
        
        Args:
            message_type: 'command', 'setpoint', ou 'route'
            callback: Função a ser chamada quando mensagem chega
        """
        self._callbacks[message_type] = callback
    
    def is_connected(self) -> bool:
        """Verifica se está conectado"""
        return self.connected

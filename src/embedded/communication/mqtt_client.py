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
    
    def __init__(self,
                 truck_id: int,
                 broker_host: str = "localhost",
                 broker_port: int = 1883,
                 qos: int = 1):
        self.truck_id = truck_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.qos = qos
        
        self.client = None
        self.connected = False
        self._callbacks = {}
        
        if not MQTT_AVAILABLE:
            return
        
        try:
            self.client = mqtt.Client(
                client_id=f"truck_{truck_id}",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except (AttributeError, TypeError):

            self.client = mqtt.Client(client_id=f"truck_{truck_id}")
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
    
    def connect(self) -> bool:
        if not MQTT_AVAILABLE or self.client is None:
            return False
        
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"[MQTT] Erro ao conectar: {e}")
            return False
    
    def disconnect(self):
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            print(f"[MQTT] Conectado ao broker {self.broker_host}:{self.broker_port}")
            
            self.client.subscribe(f"mine/truck/{self.truck_id}/command", qos=self.qos)
            self.client.subscribe(f"mine/truck/{self.truck_id}/setpoint", qos=self.qos)
            self.client.subscribe(f"mine/truck/{self.truck_id}/route", qos=self.qos)
            
            self.client.subscribe("mine/truck/+/position", qos=self.qos)
            
            print(f"[MQTT] Inscrito nos tópicos do caminhão {self.truck_id}")
            print(f"[MQTT] Inscrito em posições de todos caminhões para desvio de colisão")
        else:
            print(f"[MQTT] Falha na conexão (código {rc})")
    
    def _on_disconnect(self, client, userdata, rc, properties=None):
        self.connected = False
        print(f"[MQTT] Desconectado (código {rc})")
    
    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        if topic.endswith('/command'):
            self._handle_command(payload)
        elif topic.endswith('/setpoint'):
            self._handle_setpoint(payload)
        elif topic.endswith('/route'):
            self._handle_route(payload)
        elif topic.endswith('/position'):
            self._handle_position(topic, payload)
    
    def _handle_command(self, payload: str):
        if 'command' in self._callbacks:
            try:
                data = json.loads(payload)
                self._callbacks['command'](data)
            except Exception as e:
                print(f"[MQTT] Erro ao processar comando: {e}")
    
    def _handle_setpoint(self, payload: str):
        if 'setpoint' in self._callbacks:
            try:
                data = json.loads(payload)
                self._callbacks['setpoint'](data)
            except Exception as e:
                print(f"[MQTT] Erro ao processar setpoint: {e}")
    
    def _handle_route(self, payload: str):
        if 'route' in self._callbacks:
            try:
                data = json.loads(payload)
                self._callbacks['route'](data)
            except Exception as e:
                print(f"[MQTT] Erro ao processar rota: {e}")
    
    def _handle_position(self, topic: str, payload: str):
        if 'position' in self._callbacks:
            try:
                parts = topic.split('/')
                other_truck_id = int(parts[2])
                
                if other_truck_id != self.truck_id:
                    data = json.loads(payload)
                    data['truck_id'] = other_truck_id
                    self._callbacks['position'](data)
            except Exception as e:
                print(f"[MQTT] Erro ao processar posição: {e}")
    
    def publish_state(self, state_data: dict):
        if not self.connected:
            print(f"[MQTT] Não conectado - não publicando estado")
            return
        
        topic = f"mine/truck/{self.truck_id}/state"
        payload = json.dumps(state_data)
        result = self.client.publish(topic, payload, qos=self.qos)
        
        if not hasattr(self, '_first_publish_done'):
            print(f"[MQTT] Primeira publicação: {topic}")
            self._first_publish_done = True
        
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"[MQTT] Erro ao publicar estado: {result.rc}")
    
    def publish_position(self, x: float, y: float, theta: float):
        if not self.connected:
            return
        
        topic = f"mine/truck/{self.truck_id}/position"
        payload = json.dumps({"x": x, "y": y, "theta": theta})
        self.client.publish(topic, payload, qos=self.qos)
    
    def register_callback(self, message_type: str, callback: Callable):
        self._callbacks[message_type] = callback
    
    def is_connected(self) -> bool:
        return self.connected

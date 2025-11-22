"""
Configurações globais do sistema
"""

# Configurações do Veículo
VEHICLE_CONFIG = {
    'max_velocity': 10.0,  # m/s
    'max_angular_velocity': 1.0,  # rad/s
    'tau_velocity': 0.5,  # Constante de tempo para aceleração
    'tau_angular': 0.3,  # Constante de tempo para rotação
}

# Configurações do Filtro
FILTER_CONFIG = {
    'order': 5,  # Ordem M do filtro de média móvel
}

# Configurações dos Controladores PID
PID_VELOCITY_CONFIG = {
    'kp': 0.5,
    'ki': 0.1,
    'kd': 0.05,
}

PID_ANGULAR_CONFIG = {
    'kp': 1.0,
    'ki': 0.05,
    'kd': 0.2,
}

# Configurações de Ruído
NOISE_CONFIG = {
    'position_x': 0.05,  # Desvio padrão em metros
    'position_y': 0.05,
    'theta': 0.02,  # ~1 grau
    'velocity': 0.1,  # m/s
    'temperature': 2.0,  # °C
}

# Configurações de Falha
FAULT_CONFIG = {
    'temperature_threshold': 100.0,  # °C (crítico)
}

# Configurações de Tempo (períodos em segundos)
TIMING_CONFIG = {
    'simulation_period': 0.05,  # 50ms - Simulação
    'sensor_processing_period': 0.1,  # 100ms - Tratamento sensores
    'control_period': 0.05,  # 50ms - Controle de navegação
    'command_logic_period': 0.1,  # 100ms - Lógica de comando
    'fault_monitoring_period': 0.5,  # 500ms - Monitoramento falhas
    'data_collection_period': 1.0,  # 1s - Coleta de dados
    'route_planning_period': 0.5,  # 500ms - Planejamento rota
    'interface_update_period': 0.5,  # 500ms - Interface local
}

# Configurações MQTT
MQTT_CONFIG = {
    'broker_host': 'localhost',
    'broker_port': 1883,
    'qos': 1,  # Quality of Service (0, 1, ou 2)
}

# Configurações de Log
LOG_CONFIG = {
    'log_dir': 'data/logs',
}

# Configurações do Buffer Circular
BUFFER_CONFIG = {
    'size': 100,  # Número de amostras
}

# Configurações de Rota
ROUTE_CONFIG = {
    'waypoint_threshold': 1.0,  # metros (distância para considerar alcançado)
}

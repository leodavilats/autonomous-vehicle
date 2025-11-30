VEHICLE_CONFIG = {
    'max_velocity': 10.0,
    'max_angular_velocity': 1.0,
    'tau_velocity': 0.5,
    'tau_angular': 0.3,
}

FILTER_CONFIG = {
    'order': 5,
}

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

NOISE_CONFIG = {
    'position_x': 0.05,
    'position_y': 0.05,
    'theta': 0.02,
    'velocity': 0.1,
    'temperature': 2.0,
}

FAULT_CONFIG = {
    'temperature_alert_threshold': 95.0,
    'temperature_fault_threshold': 120.0,
}

TIMING_CONFIG = {
    'simulation_period': 0.05,
    'sensor_processing_period': 0.1,
    'control_period': 0.05,
    'command_logic_period': 0.1,
    'fault_monitoring_period': 0.5,
    'data_collection_period': 1.0,
    'route_planning_period': 0.5,
    'interface_update_period': 0.5,
}

MQTT_CONFIG = {
    'broker_host': 'localhost',
    'broker_port': 1883,
    'qos': 1,
}

LOG_CONFIG = {
    'log_dir': 'data/logs',
}

BUFFER_CONFIG = {
    'size': 100,
}

ROUTE_CONFIG = {
    'waypoint_threshold': 1.0,
}

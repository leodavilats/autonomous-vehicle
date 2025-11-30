import time
from typing import Optional

class PIDController:
    
    def __init__(self, 
                 kp: float = 1.0, 
                 ki: float = 0.0, 
                 kd: float = 0.0,
                 output_min: float = -1.0,
                 output_max: float = 1.0,
                 sample_time: float = 0.1):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_min = output_min
        self.output_max = output_max
        self.sample_time = sample_time
        
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = None
        self._last_output = 0.0
        self._enabled = False
        self._setpoint = 0.0
    
    def compute(self, measured_value: float, setpoint: float) -> float:
        current_time = time.time()
        
        if self._last_time is None:
            self._last_time = current_time
            self._last_error = setpoint - measured_value
            return 0.0
        
        dt = current_time - self._last_time
        if dt < self.sample_time:
            return self._last_output
        
        error = setpoint - measured_value
        
        p_term = self.kp * error
        
        self._integral += error * dt

        max_integral = (self.output_max - self.output_min) / (2.0 * self.ki) if self.ki != 0 else 1e6
        self._integral = max(-max_integral, min(max_integral, self._integral))
        i_term = self.ki * self._integral
        
        d_term = 0.0
        if dt > 0:
            d_term = self.kd * (error - self._last_error) / dt
        
        output = p_term + i_term + d_term
        
        output = max(self.output_min, min(self.output_max, output))
        
        self._last_error = error
        self._last_time = current_time
        self._last_output = output
        self._setpoint = setpoint
        
        return output
    
    def enable(self, current_value: float) -> None:
        self._enabled = True
        self._setpoint = current_value
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = None
        self._last_output = 0.0
    
    def disable(self) -> None:
        self._enabled = False
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def reset(self) -> None:
        self._integral = 0.0
        self._last_error = 0.0
        self._last_time = None
        self._last_output = 0.0
    
    def set_gains(self, kp: float = None, ki: float = None, kd: float = None) -> None:
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd
    
    def get_setpoint(self) -> float:
        return self._setpoint

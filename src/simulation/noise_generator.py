"""
Gerador de ruído para simulação de sensores
Adiciona ruído gaussiano de média zero aos dados
"""

import random
import math


class NoiseGenerator:
    """
    Gerador de ruído gaussiano (distribuição normal)
    Simula ruído dos sensores com média zero
    """
    
    def __init__(self, std_dev: float = 0.1, seed: int = None):
        """
        Args:
            std_dev: Desvio padrão do ruído
            seed: Semente para reprodutibilidade (opcional)
        """
        self._std_dev = std_dev
        if seed is not None:
            random.seed(seed)
    
    def add_noise(self, value: float) -> float:
        """
        Adiciona ruído gaussiano a um valor
        
        Args:
            value: Valor original
            
        Returns:
            Valor com ruído adicionado
        """
        noise = random.gauss(0.0, self._std_dev)
        return value + noise
    
    def add_noise_array(self, values: list) -> list:
        """
        Adiciona ruído a múltiplos valores
        
        Args:
            values: Lista de valores
            
        Returns:
            Lista de valores com ruído
        """
        return [self.add_noise(v) for v in values]
    
    def set_std_dev(self, std_dev: float) -> None:
        """Altera o desvio padrão do ruído"""
        self._std_dev = std_dev
    
    def get_std_dev(self) -> float:
        """Retorna o desvio padrão atual"""
        return self._std_dev


class MultiChannelNoise:
    """
    Gerador de ruído para múltiplos canais com desvios padrão diferentes
    """
    
    def __init__(self, std_devs: dict):
        """
        Args:
            std_devs: Dicionário {nome_canal: desvio_padrão}
        """
        self._generators = {
            channel: NoiseGenerator(std_dev) 
            for channel, std_dev in std_devs.items()
        }
    
    def add_noise(self, channel: str, value: float) -> float:
        """Adiciona ruído a um canal específico"""
        if channel not in self._generators:
            return value
        return self._generators[channel].add_noise(value)
    
    def add_noise_dict(self, values: dict) -> dict:
        """
        Adiciona ruído a múltiplos canais
        
        Args:
            values: Dicionário {canal: valor}
            
        Returns:
            Dicionário com valores ruidosos
        """
        return {
            channel: self.add_noise(channel, value)
            for channel, value in values.items()
        }

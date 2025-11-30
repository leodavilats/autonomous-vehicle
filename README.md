# Sistema de Controle de Veículo Autônomo de Mineração

Sistema embarcado em tempo real para caminhões autônomos de mineração com **8 tarefas concorrentes**, controladores PID, sincronização por mutex/condition variables, comunicação MQTT e interface gráfica centralizada.

---

## 🚀 Execução Rápida

### 1. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 2. Sistema Completo (3 Terminais)

**Terminal 1 - Broker MQTT:**
```bash
mosquitto
```
> **Nota Windows**: Se não instalado, use `choco install mosquitto` ou baixe de [mosquitto.org](https://mosquitto.org/download/)

**Terminal 2 - Sistema Central (Interface Gráfica):**
```bash
python central_system.py
```

**Terminal 3 - Caminhão Autônomo:**
```bash
python main.py 1 --mqtt
```
> Use IDs diferentes (2, 3, etc.) para múltiplos caminhões

### 3. Controlar via Interface Gráfica
- Selecione o caminhão no dropdown
- **Modo Automático** → Insira waypoints (x, y) no campo de rota
- **Modo Manual** → Ajuste velocidade linear e angular
- **Emergência** → Parada imediata do veículo

**Alternativa via Terminal:**
```bash
python control_truck.py 1
```
Digite `1` (modo automático) → `6` (rota) → `80 50` (waypoint)

---

## ⚙️ Arquitetura do Sistema

### 🔄 Tarefas Concorrentes (8 Threads)

1. **Simulação da Mina** (`mine_simulator.py`)
   - Dinâmica do veículo com modelo de 1ª ordem (inércia)
   - Período: 50ms (20Hz)
   
2. **Processamento de Sensores** (`sensor_processing.py`)
   - Filtro de média móvel (janela M=5)
   - Leitura: GPS (x, y, θ), velocidade, temperatura
   - Período: 100ms (10Hz)

3. **Lógica de Comando** (`command_logic.py`)
   - Máquina de estados: STOPPED, RUNNING, EMERGENCY
   - Modos: MANUAL_LOCAL, MANUAL_REMOTE, AUTOMATIC_REMOTE
   - Período: 100ms (10Hz)

4. **Controle de Navegação** (`navigation_control.py`)
   - PID de velocidade linear (Kp=0.5, Ki=0.1, Kd=0.05)
   - PID de velocidade angular (Kp=1.0, Ki=0.05, Kd=0.2)
   - Bumpless transfer e anti-windup
   - Período: 50ms (20Hz)

5. **Planejamento de Rota** (`route_planner.py`)
   - Navegação por waypoints com orientação automática
   - Raio de aceitação configurável
   - Período: 500ms (2Hz)

6. **Monitoramento de Falhas** (`fault_monitoring.py`)
   - Temperatura (alerta: 95°C, falha: 120°C)
   - Falhas elétricas e hidráulicas aleatórias (baixa probabilidade)
   - Período: 500ms (2Hz)

7. **Coletor de Dados** (`data_collector.py`)
   - Logging CSV com timestamp, posição, status, eventos
   - Salvamento em `data/logs/truck_{id}.csv`
   - Período: 1s (1Hz)

8. **Interface Local** (`local_interface.py`)
   - Comandos do operador via terminal (opcional)
   - Silenciosa quando `--mqtt` está ativo
   - Período: 500ms (2Hz)

### 🔒 Mecanismos de Sincronização

- **Mutex (Threading.Lock)**:
  - `SharedState`: Estado global do veículo (posição, velocidade, status, modo)
  - `CircularBuffer`: Histórico de sensores filtrados
  
- **Condition Variables (Threading.Condition)**:
  - `EventManager`: Coordenação entre tarefas (alertas, confirmações)
  
- **Queues Thread-Safe (Queue.Queue)**:
  - Fila de comandos remotos (MQTT → Lógica de Comando)
  - Fila de waypoints (Rota → Planejador)

### 🎛️ Controladores PID

**Velocidade Linear:**
- Controla a aceleração/desaceleração do veículo
- Saída: Velocidade de referência para dinâmica
- Anti-windup: Saturação em ±10 m/s

**Velocidade Angular:**
- Controla a orientação para seguir waypoints
- Erro calculado a partir de atan2(Δy, Δx) - θ_atual
- Anti-windup: Saturação em ±1 rad/s

**Bumpless Transfer:**
- Inicializa termo integral do PID com saída manual anterior
- Garante transição suave de manual para automático

### 📡 Comunicação MQTT

**Tópicos Publicados:**
- `mine/truck/{id}/state` - Estado completo (JSON) a cada 100ms
- `mine/truck/{id}/position` - Posição GPS (JSON) a cada 100ms

**Tópicos Subscritos:**
- `mine/truck/{id}/command` - Comandos remotos (modo, emergência, setpoints)
- `mine/truck/{id}/route` - Lista de waypoints [(x1, y1), (x2, y2), ...]

**Formato JSON do Estado:**
```json
{
  "truck_id": 1,
  "timestamp": 1700000000.123,
  "position": {"x": 50.5, "y": 37.8, "theta": 0.785},
  "velocity": 3.5,
  "temperature": 45.2,
  "status": "RUNNING",
  "mode": "AUTOMATIC_REMOTE",
  "faults": {"electrical": false, "hydraulic": false}
}
```

### 🖥️ Interface Gráfica (Sistema Central)

**Características:**
- Mapa 100m × 75m em tempo real
- Suporta múltiplos caminhões simultaneamente
- Atualização a cada 100ms via MQTT

**Representação Visual:**
- 🟢 Verde = RUNNING (operacional)
- 🟡 Amarelo = STOPPED (parado)
- 🔴 Vermelho = EMERGENCY/FAULT (emergência ou falha)
- Triângulo indica direção (orientação θ)

**Controles Disponíveis:**
- Seleção de caminhão (dropdown)
- Botões: Automático, Manual, Emergência, Reset
- Setpoints: Velocidade linear/angular (modo manual)
- Entrada de rota: Lista de waypoints separados por vírgula

**Painel de Informações:**
- ID do caminhão
- Status operacional
- Modo de controle
- Posição (x, y, θ)
- Velocidade atual
- Temperatura do motor

---

## 📁 Estrutura do Projeto

```
autonomous-vehicle/
├── main.py                          # Sistema embarcado (inicializa 8 threads)
├── central_system.py                # Interface gráfica Tkinter + MQTT
├── control_truck.py                 # Controlador CLI via MQTT
├── requirements.txt                 # Dependências Python
├── README.md                        # Esta documentação
│
├── config/
│   └── settings.py                  # Configurações globais do sistema
│
├── data/
│   └── logs/
│       └── truck_{id}.csv           # Logs de telemetria
│
└── src/
    │
    ├── embedded/                    # Sistema embarcado
    │   │
    │   ├── tasks/                   # 8 tarefas concorrentes
    │   │   ├── sensor_processing.py      # Thread 1: Filtro de sensores
    │   │   ├── command_logic.py          # Thread 2: Máquina de estados
    │   │   ├── navigation_control.py     # Thread 3: Controladores PID
    │   │   ├── route_planner.py          # Thread 4: Navegação por waypoints
    │   │   ├── fault_monitoring.py       # Thread 5: Detecção de falhas
    │   │   ├── data_collector.py         # Thread 6: Logging CSV
    │   │   ├── local_interface.py        # Thread 7: Interface do operador
    │   │   └── collision_avoidance.py    # Thread 8: Prevenção de colisões
    │   │
    │   ├── sync/                    # Mecanismos de sincronização
    │   │   ├── shared_state.py           # Mutex para estado global
    │   │   ├── circular_buffer.py        # Buffer thread-safe de sensores
    │   │   └── event_manager.py          # Condition variables
    │   │
    │   ├── control/                 # Controladores
    │   │   ├── pid_controller.py         # Classe base PID genérica
    │   │   ├── velocity_controller.py    # PID de velocidade linear
    │   │   └── angular_controller.py     # PID de velocidade angular
    │   │
    │   ├── filters/
    │   │   └── moving_average.py         # Filtro de média móvel
    │   │
    │   └── communication/
    │       └── mqtt_client.py            # Cliente MQTT (pub/sub)
    │
    ├── simulation/                  # Simulação do ambiente
    │   ├── mine_simulator.py             # Dinâmica do veículo (1ª ordem)
    │   ├── vehicle_dynamics.py           # Modelo físico (tau, saturação)
    │   ├── noise_generator.py            # Ruído gaussiano nos sensores
    │   └── random_fault_generator.py     # Injeção de falhas aleatórias
    │
    ├── central/                     # Sistema central
    │   └── mine_management.py            # Interface Tkinter + MQTT
    │
    └── models/                      # Estruturas de dados
        ├── vehicle_state.py              # Estado do veículo
        ├── sensor_data.py                # Leitura de sensores
        ├── command.py                    # Comandos de controle
        └── log_entry.py                  # Entrada de log CSV
```

---

## 🎮 Comandos do Controlador CLI

Execute `python control_truck.py <truck_id>` e use:

| Comando | Função | Exemplo |
|---------|--------|---------|
| **1** | Ativar modo AUTOMÁTICO | `1` |
| **2** | Ativar modo MANUAL | `2` |
| **3** | Parada de EMERGÊNCIA | `3` |
| **4** | Reset emergência | `4` |
| **5** | Definir velocidade setpoint | `5` → `5.0` (m/s) |
| **6** | Definir rota (waypoints) | `6` → `80 50` → `40 30` → `enter` |
| **7** | Parar caminhão | `7` |
| **8** | Ver status atual | `8` |

**Exemplo de Uso Completo:**
```bash
python control_truck.py 1
> 1                    # Ativar modo automático
> 6                    # Definir rota
> 80 50                # Waypoint 1
> 40 30                # Waypoint 2
> 10 10                # Waypoint 3
> [Enter vazio]        # Finalizar rota
```

---

## 📊 Logs e Telemetria

### Formato CSV (`data/logs/truck_{id}.csv`)

Cada linha registra o estado completo do veículo a cada segundo:

```csv
timestamp,truck_id,status,mode,position_x,position_y,theta,velocity,temperature,electrical_fault,hydraulic_fault,event_description
1700000000.123,1,RUNNING,AUTOMATIC_REMOTE,50.5,37.8,0.785,3.5,45.2,False,False,"Navegando para waypoint (80.0, 50.0)"
1700000001.123,1,RUNNING,AUTOMATIC_REMOTE,50.6,37.9,0.790,3.6,45.3,False,False,"Status normal"
1700000002.123,1,EMERGENCY,AUTOMATIC_REMOTE,50.7,38.0,0.795,0.0,125.4,False,False,"Temperatura crítica: 125.4°C"
```

**Campos:**
- `timestamp`: Unix timestamp com milissegundos
- `truck_id`: ID do veículo
- `status`: STOPPED, RUNNING, EMERGENCY
- `mode`: MANUAL_LOCAL, MANUAL_REMOTE, AUTOMATIC_REMOTE
- `position_x`, `position_y`: Coordenadas GPS (metros)
- `theta`: Orientação (radianos)
- `velocity`: Velocidade linear (m/s)
- `temperature`: Temperatura do motor (°C)
- `electrical_fault`, `hydraulic_fault`: Booleanos
- `event_description`: Descrição textual do evento

---

## 🐛 Solução de Problemas

### ❌ Erro: "No module named 'paho'"
```bash
pip install paho-mqtt
```

### ❌ Broker MQTT não conecta

**Windows (instalação via Chocolatey):**
```powershell
choco install mosquitto
net start mosquitto
```

**Alternativa (executável direto):**
1. Baixe de [mosquitto.org/download](https://mosquitto.org/download/)
2. Instale e execute:
```bash
mosquitto
```

**Linux/Mac:**
```bash
# Instalação
sudo apt-get install mosquitto mosquitto-clients  # Debian/Ubuntu
brew install mosquitto                             # macOS

# Iniciar
mosquitto
```

### ❌ Caminhão não aparece no mapa
1. ✅ Verifique se `mosquitto` está rodando (Terminal 1)
2. ✅ Confirme que usou flag `--mqtt` ao iniciar o caminhão
3. ✅ Aguarde 2-3 segundos para sincronização inicial
4. ✅ Verifique se o ID do caminhão está correto

### ❌ Interface gráfica não abre
```bash
# Tkinter pode não estar instalado
# Windows: Reinstale Python com opção "tcl/tk"
# Linux:
sudo apt-get install python3-tk
```

### ❌ Logs não são gerados
- Verifique se a pasta `data/logs/` existe
- Permissões de escrita no diretório
- A task `data_collector` só grava a cada 1 segundo

### 🔍 Debug Avançado

**Ver mensagens MQTT:**
```bash
# Terminal extra - Monitorar todos os tópicos
mosquitto_sub -t "mine/#" -v
```

**Verificar threads ativas:**
```python
# Adicione no main.py após iniciar threads
import threading
print(f"Threads ativas: {threading.active_count()}")
for t in threading.enumerate():
    print(f"  - {t.name}")
```

---

## 🚦 Cenários de Teste

### Teste 1: Modo Automático com Rota Simples
```bash
# No control_truck.py ou interface gráfica
1. Modo Automático
2. Rota: (50, 50) → (80, 30) → (20, 60)
# Observe o caminhão seguir os waypoints no mapa
```

### Teste 2: Transição Manual → Automático (Bumpless Transfer)
```bash
1. Modo Manual
2. Defina velocidade 5.0 m/s
3. Aguarde estabilizar
4. Modo Automático
5. Defina rota
# Verifique se não há "salto" na velocidade
```

### Teste 3: Recuperação de Emergência
```bash
1. Modo Automático com rota ativa
2. Emergência (botão vermelho ou comando 3)
# Caminhão para instantaneamente
3. Reset (comando 4)
4. Modo Automático novamente
# Caminhão retoma do ponto onde parou
```

### Teste 4: Múltiplos Caminhões
```bash
# Terminal 3
python main.py 1 --mqtt

# Terminal 4
python main.py 2 --mqtt

# Terminal 5
python main.py 3 --mqtt

# No Sistema Central: Controle cada um independentemente
```

### Teste 5: Injeção de Falha
```bash
# Aguarde até temperatura > 120°C (gerado aleatoriamente)
# Caminhão entra em EMERGENCY automaticamente
# Log registra: "Temperatura crítica: XXX°C"
```

---

## 📦 Dependências

```
numpy>=1.21.0        # Cálculos numéricos (filtros, PID, dinâmica)
matplotlib>=3.5.0    # Visualização (potencial para plots futuros)
paho-mqtt>=1.6.0     # Cliente MQTT (pub/sub)
```

**Incluído no Python:**
- `tkinter` - Interface gráfica (built-in)
- `threading` - Multithreading (built-in)
- `queue` - Filas thread-safe (built-in)

**Instalação:**
```bash
pip install -r requirements.txt
```

---

## 🎓 Conceitos de Sistemas Embarcados Implementados

### 1. **Multitarefa com Threads**
- 8 tarefas independentes rodando concorrentemente
- Cada tarefa tem período fixo (design periódico)
- Simulação de sistema de tempo real

### 2. **Sincronização Entre Tarefas**
- **Mutex (Lock)**: Proteção de recursos compartilhados (estado, buffer)
- **Condition Variables**: Notificação de eventos entre tarefas
- **Queues**: Comunicação assíncrona sem bloqueio

### 3. **Controle em Tempo Real**
- Controladores PID discretos (velocidade linear e angular)
- Bumpless transfer: Evita descontinuidades na transição de modos
- Anti-windup: Previne saturação do termo integral

### 4. **Processamento de Sinais**
- Filtro de média móvel (redução de ruído)
- Buffer circular thread-safe para histórico de sensores

### 5. **Máquina de Estados**
- Estados: STOPPED, RUNNING, EMERGENCY
- Modos: MANUAL_LOCAL, MANUAL_REMOTE, AUTOMATIC_REMOTE
- Transições baseadas em comandos e condições de falha

### 6. **Comunicação em Rede**
- Protocolo MQTT (publish/subscribe)
- Arquitetura distribuída: Veículos embarcados + Sistema central
- Serialização JSON para telemetria

### 7. **Tratamento de Falhas**
- Monitoramento contínuo de sensores críticos (temperatura)
- Injeção aleatória de falhas para teste de robustez
- Ação automática em caso de falha (parada de emergência)

### 8. **Logging e Rastreabilidade**
- Registro persistente de todos os eventos (CSV)
- Timestamping preciso para análise pós-operação

---

## 📚 Referências e Recursos

### Documentação Técnica
- [MQTT Protocol](https://mqtt.org/) - Protocolo de mensageria IoT
- [Eclipse Paho MQTT](https://www.eclipse.org/paho/clients/python/) - Cliente Python
- [Tkinter Documentation](https://docs.python.org/3/library/tkinter.html) - GUI
- [Threading in Python](https://docs.python.org/3/library/threading.html) - Concorrência

### Controle e Filtragem
- **PID Control**: Ogata, K. "Modern Control Engineering"
- **Digital Filters**: Smith, S.W. "The Scientist and Engineer's Guide to Digital Signal Processing"
- **Bumpless Transfer**: Åström, K.J. & Hägglund, T. "Advanced PID Control"

### Sistemas Embarcados
- **Real-Time Systems**: Liu, J.W.S. "Real-Time Systems"
- **Concurrent Programming**: Andrews, G.R. "Foundations of Multithreaded, Parallel, and Distributed Programming"

---

## 🔮 Possíveis Extensões

- [ ] Implementar navegação com desvio de obstáculos (A* ou RRT)
- [ ] Adicionar comunicação CAN bus simulada
- [ ] Implementar filtro de Kalman para fusão sensorial
- [ ] Dashboard web com gráficos em tempo real (WebSocket)
- [ ] Simulação 3D com PyBullet ou Gazebo
- [ ] Sistema de planejamento de múltiplos veículos (coordenação)
- [ ] Otimização de rotas (TSP para múltiplos pontos de carga/descarga)
- [ ] Integração com ROS 2 (Robot Operating System)

---

## 👤 Autor

Desenvolvido como projeto acadêmico de **Automação em Tempo Real**.

Sistema demonstra conceitos de:
- Sistemas embarcados de tempo real
- Controle automático digital
- Arquiteturas distribuídas
- Sincronização e comunicação entre processos

---

## 📄 Licença

Este projeto é de código aberto e está disponível para fins educacionais.

---

**Sistema Operacional em 30/11/2025** 🚛⚙️🤖
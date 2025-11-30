import tkinter as tk
from tkinter import ttk
import json
import time
from typing import Dict, Tuple, List
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

class MineManagementGUI:
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        self.trucks: Dict[int, dict] = {}
        self.selected_truck_id: int = None
        self._last_truck_count: int = 0
        
        self.root = tk.Tk()
        self.root.title("Sistema de Gestão da Mina")
        self.root.geometry("1200x900")
        
        self.manual_frame = None
        self.auto_frame = None
        
        self._setup_gui()
        
        self.mqtt_client = None
        if MQTT_AVAILABLE:
            self._setup_mqtt()
    
    def _setup_gui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#1a5490')
        style.configure('Section.TLabelframe.Label', font=('Segoe UI', 11, 'bold'), foreground='#2c5282')
        style.configure('Info.TLabel', font=('Segoe UI', 9))
        style.configure('Status.TLabel', font=('Segoe UI', 9, 'bold'))
        style.configure('Action.TButton', font=('Segoe UI', 10, 'bold'))
        style.configure('Emergency.TButton', font=('Segoe UI', 10, 'bold'), foreground='#c53030')
        style.configure('Reset.TButton', font=('Segoe UI', 10, 'bold'), foreground='#2f855a')
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=3)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky=(tk.W, tk.E))
        
        title = ttk.Label(title_frame, text="🚛 SISTEMA DE GESTÃO DA MINA", 
                         style='Title.TLabel')
        title.pack()
        
        subtitle = ttk.Label(title_frame, text="Monitoramento e Controle de Caminhões Autônomos",
                            font=('Segoe UI', 10), foreground='#718096')
        subtitle.pack()
        
        map_frame = ttk.LabelFrame(main_frame, text=" 🗺️  Mapa da Mina (100m × 75m) ", 
                                   style='Section.TLabelframe', padding="10")
        map_frame.grid(row=1, column=0, padx=(0, 10), pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(0, weight=1)
        
        self.canvas = tk.Canvas(map_frame, bg='#1a202c', highlightthickness=1, 
                               highlightbackground='#4a5568', width=800, height=600)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.canvas.bind('<Configure>', self._on_canvas_resize)
        
        control_outer = ttk.Frame(main_frame)
        control_outer.grid(row=1, column=1, padx=5, pady=5, sticky=(tk.N, tk.W, tk.E, tk.S))
        control_outer.rowconfigure(0, weight=1)
        control_outer.columnconfigure(0, weight=1)
        
        control_canvas = tk.Canvas(control_outer, bg='#f7fafc', highlightthickness=0)
        control_canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        
        scrollbar = ttk.Scrollbar(control_outer, orient=tk.VERTICAL, command=control_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        control_canvas.configure(yscrollcommand=scrollbar.set)
        
        control_container = ttk.Frame(control_canvas)
        canvas_window = control_canvas.create_window((0, 0), window=control_container, anchor=tk.NW)
        
        def _on_frame_configure(event):
            control_canvas.configure(scrollregion=control_canvas.bbox("all"))
        
        def _on_canvas_configure(event):
            control_canvas.itemconfig(canvas_window, width=event.width)
        
        control_container.bind('<Configure>', _on_frame_configure)
        control_canvas.bind('<Configure>', _on_canvas_configure)
        
        def _on_mousewheel(event):
            control_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        control_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        truck_frame = ttk.LabelFrame(control_container, text=" 🚚 Caminhões Ativos ", 
                                     style='Section.TLabelframe', padding="10")
        truck_frame.grid(row=0, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        self.truck_listbox = tk.Listbox(truck_frame, height=6, font=('Consolas', 9),
                                       bg='#f7fafc', fg='#2d3748', 
                                       selectbackground='#4299e1', selectforeground='white',
                                       relief=tk.FLAT, borderwidth=1, highlightthickness=1,
                                       highlightbackground='#cbd5e0')
        self.truck_listbox.pack(fill=tk.BOTH, expand=True)
        self.truck_listbox.bind('<<ListboxSelect>>', self._on_truck_select)
        
        info_frame = ttk.LabelFrame(control_container, text=" ℹ️  Informações ", 
                                    style='Section.TLabelframe', padding="10")
        info_frame.grid(row=1, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        self.info_labels = {}
        labels = [
            ('Status:', '🔄'),
            ('Modo:', '⚙️'),
            ('Posição:', '📍'),
            ('Velocidade:', '💨'),
            ('Temperatura:', '🌡️'),
            ('Falha Elétrica:', '⚡'),
            ('Falha Hidráulica:', '🔧')
        ]
        
        for i, (label, icon) in enumerate(labels):
            row_frame = ttk.Frame(info_frame)
            row_frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            
            ttk.Label(row_frame, text=icon, style='Info.TLabel',
                     foreground='#4a5568', width=2).pack(side=tk.LEFT)
            ttk.Label(row_frame, text=label, style='Info.TLabel',
                     foreground='#4a5568', width=15).pack(side=tk.LEFT)
            self.info_labels[label] = ttk.Label(row_frame, text="-", style='Status.TLabel',
                                               foreground='#2d3748')
            self.info_labels[label].pack(side=tk.LEFT)
        
        cmd_frame = ttk.LabelFrame(control_container, text=" 🎮 Comandos ", 
                                   style='Section.TLabelframe', padding="10")
        cmd_frame.grid(row=2, column=0, pady=(0, 10), sticky=(tk.W, tk.E))
        
        ttk.Button(cmd_frame, text="🤖 Modo Automático", style='Action.TButton',
                  command=self._send_auto_command).pack(fill=tk.X, pady=3)
        ttk.Button(cmd_frame, text="👤 Modo Manual", style='Action.TButton',
                  command=self._send_manual_command).pack(fill=tk.X, pady=3)
        
        sep = ttk.Separator(cmd_frame, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, pady=8)
        
        ttk.Button(cmd_frame, text="🚨 EMERGÊNCIA", style='Emergency.TButton',
                  command=self._send_emergency).pack(fill=tk.X, pady=3)
        ttk.Button(cmd_frame, text="✅ REARMAR Sistema", style='Reset.TButton',
                  command=self._send_reset_fault).pack(fill=tk.X, pady=3)
        
        self.manual_frame = ttk.LabelFrame(control_container, text=" 🕹️  Controle Manual ", 
                                          style='Section.TLabelframe', padding="15")
        
        dir_frame = ttk.Frame(self.manual_frame)
        dir_frame.pack(pady=5)
        
        ttk.Button(dir_frame, text="▲", width=8,
                  command=self._send_forward).grid(row=0, column=1, padx=2, pady=2)
        ttk.Button(dir_frame, text="◄", width=8,
                  command=self._send_left).grid(row=1, column=0, padx=2, pady=2)
        ttk.Label(dir_frame, text="⊗", font=('Segoe UI', 14),
                 foreground='#a0aec0').grid(row=1, column=1, padx=2, pady=2)
        ttk.Button(dir_frame, text="►", width=8,
                  command=self._send_right).grid(row=1, column=2, padx=2, pady=2)
        ttk.Button(dir_frame, text="▼", width=8,
                  command=self._send_backward).grid(row=2, column=1, padx=2, pady=2)
        
        accel_frame = ttk.Frame(self.manual_frame)
        accel_frame.pack(pady=10, fill=tk.X)
        ttk.Button(accel_frame, text="⚡ Acelerar", 
                  command=self._send_accelerate).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        ttk.Button(accel_frame, text="🛑 Freiar", 
                  command=self._send_brake).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.auto_frame = ttk.LabelFrame(control_container, text=" 🎯 Modo Automático - Waypoints ", 
                                        style='Section.TLabelframe', padding="10")
        
        wp_list_frame = ttk.Frame(self.auto_frame)
        wp_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        ttk.Label(wp_list_frame, text="Lista de Waypoints:", style='Info.TLabel',
                 foreground='#4a5568').pack(anchor=tk.W, pady=(0, 5))
        
        self.waypoints_listbox = tk.Listbox(wp_list_frame, height=5, font=('Consolas', 9),
                                           bg='#f7fafc', fg='#2d3748',
                                           selectbackground='#4299e1', selectforeground='white',
                                           relief=tk.FLAT, borderwidth=1, highlightthickness=1,
                                           highlightbackground='#cbd5e0')
        self.waypoints_listbox.pack(fill=tk.BOTH, expand=True)
        
        coord_frame = ttk.Frame(self.auto_frame)
        coord_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(coord_frame, text="X:", style='Info.TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.waypoint_x_entry = ttk.Entry(coord_frame, width=10, font=('Segoe UI', 10))
        self.waypoint_x_entry.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(coord_frame, text="Y:", style='Info.TLabel').grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.waypoint_y_entry = ttk.Entry(coord_frame, width=10, font=('Segoe UI', 10))
        self.waypoint_y_entry.grid(row=0, column=3)
        
        wp_btn_frame = ttk.Frame(self.auto_frame)
        wp_btn_frame.pack(fill=tk.X)
        
        ttk.Button(wp_btn_frame, text="➕ Adicionar", 
                  command=self._add_waypoint).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        ttk.Button(wp_btn_frame, text="➖ Remover", 
                  command=self._remove_waypoint).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        ttk.Button(wp_btn_frame, text="🗑️ Limpar", 
                  command=self._clear_waypoints).pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        ttk.Separator(self.auto_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        ttk.Button(self.auto_frame, text="🚀 Enviar Rota Completa", style='Action.TButton',
                  command=self._send_route).pack(fill=tk.X)
        
        self.waypoints = []
        
        self.status_bar = ttk.Label(self.root, text="⏳ Aguardando conexão MQTT...",
                                    relief=tk.SUNKEN, anchor=tk.W, padding="5",
                                    font=('Segoe UI', 9), background='#edf2f7', foreground='#2d3748')
        self.status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self._draw_map_grid()
        
        self.root.update_idletasks()
        
        self._update_display()
    
    def _setup_mqtt(self):
        try:
            self.mqtt_client = mqtt.Client(
                client_id="mine_management",
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2
            )
        except (AttributeError, TypeError):
            self.mqtt_client = mqtt.Client(client_id="mine_management")
        
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        
        try:
            self.mqtt_client.connect(self.broker_host, self.broker_port, 60)
            self.mqtt_client.loop_start()
        except Exception as e:
            self.status_bar.config(text=f"Erro MQTT: {e}")
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.status_bar.config(text=f"✅ Conectado ao broker MQTT ({self.broker_host})")
            client.subscribe("mine/truck/+/state", qos=1)
            client.subscribe("mine/truck/+/position", qos=1)
        else:
            self.status_bar.config(text=f"❌ Falha na conexão MQTT (código {rc})")
    
    def _on_mqtt_message(self, client, userdata, msg):
        try:
            parts = msg.topic.split('/')
            truck_id = int(parts[2])
            
            payload = json.loads(msg.payload.decode('utf-8'))
            
            if truck_id not in self.trucks:
                self.trucks[truck_id] = {}
                print(f"✓ Caminhão {truck_id} conectado")
            
            if msg.topic.endswith('/state'):
                self.trucks[truck_id].update(payload)
            elif msg.topic.endswith('/position'):
                self.trucks[truck_id].update(payload)
            
            self.trucks[truck_id]['last_update'] = time.time()
            
        except Exception as e:
            print(f"[ERRO] Falha ao processar mensagem MQTT: {e}")
            import traceback
            traceback.print_exc()
    
    def _draw_map_grid(self):
        self.canvas.delete('grid')
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width <= 1:
            width = 800
        if height <= 1:
            height = 600
        
        grid_spacing_x = width / 10
        grid_spacing_y = height / 7.5
        
        for i in range(11):
            x = i * grid_spacing_x
            self.canvas.create_line(x, 0, x, height, fill='#2d3748', width=1, tags='grid')
            if i % 2 == 0:
                self.canvas.create_text(x, height - 10, text=f'{i*10}m', 
                                       fill='#718096', font=('Segoe UI', 8), tags='grid')
        
        for i in range(8):
            y = i * grid_spacing_y
            self.canvas.create_line(0, y, width, y, fill='#2d3748', width=1, tags='grid')
            if i % 2 == 0:
                self.canvas.create_text(10, y + 10, text=f'{int((7.5-i)*10)}m', 
                                       fill='#718096', font=('Segoe UI', 8), tags='grid', anchor=tk.W)
        
        self.canvas.create_rectangle(width/2 - 150, 5, width/2 + 150, 35, 
                                     fill='#2d3748', outline='#4a5568', width=2, tags='grid')
        self.canvas.create_text(width/2, 20, text="ÁREA DA MINA - 100m × 75m", 
                               fill='#e2e8f0', font=('Segoe UI', 12, 'bold'), tags='grid')
        
        legend_x = width - 120
        legend_y = height - 90
        
        self.canvas.create_rectangle(legend_x - 10, legend_y - 5, legend_x + 110, legend_y + 80,
                                     fill='#2d3748', outline='#4a5568', width=2, tags='grid')
        self.canvas.create_text(legend_x + 50, legend_y + 5, text="Legenda", 
                               fill='#e2e8f0', font=('Segoe UI', 9, 'bold'), tags='grid')
        
        legends = [
            (legend_y + 20, '#48bb78', 'Operando'),
            (legend_y + 40, '#f6ad55', 'Parado'),
            (legend_y + 60, '#f56565', 'Falha/Emerg.')
        ]
        
        for y, color, text in legends:
            self.canvas.create_polygon(
                legend_x, y, legend_x + 8, y - 6, legend_x + 8, y + 6,
                fill=color, outline='white', width=1, tags='grid'
            )
            self.canvas.create_text(legend_x + 15, y, text=text, fill='#e2e8f0',
                                   font=('Segoe UI', 8), anchor=tk.W, tags='grid')
    
    def _on_canvas_resize(self, event):
        """Redesenha o grid quando o canvas é redimensionado"""
        if hasattr(self, '_resize_timer'):
            self.root.after_cancel(self._resize_timer)
        
        self._resize_timer = self.root.after(100, self._redraw_canvas)
    
    def _redraw_canvas(self):
        """Redesenha todo o conteúdo do canvas"""
        self._draw_map_grid()
        self._draw_trucks()
    
    def _update_display(self):

        current_selection = self.truck_listbox.curselection()
        selected_index = current_selection[0] if current_selection else None
        
        if self.trucks:
            truck_count = len(self.trucks)
            if truck_count > 0 and hasattr(self, '_last_truck_count') and self._last_truck_count != truck_count:
                print(f"[INFO] {truck_count} caminhão(ões) no sistema")
            self._last_truck_count = truck_count
        
        self.truck_listbox.delete(0, tk.END)
        restore_index = None
        for idx, (truck_id, data) in enumerate(sorted(self.trucks.items())):
            status = data.get('status', 'UNKNOWN')
            electrical_fault = data.get('electrical_fault', False)
            hydraulic_fault = data.get('hydraulic_fault', False)
            emergency = data.get('emergency_stop', False)
            
            fault_indicator = ""
            if emergency:
                fault_indicator = " ⚠️ EMERGÊNCIA"
            elif electrical_fault:
                fault_indicator = " ⚡ FALHA ELÉTRICA"
            elif hydraulic_fault:
                fault_indicator = " 🔧 FALHA HIDRÁULICA"
            
            display_text = f"Caminhão {truck_id} - {status}{fault_indicator}"
            self.truck_listbox.insert(tk.END, display_text)
            
            if self.selected_truck_id == truck_id:
                restore_index = idx
        
        if restore_index is not None:
            self.truck_listbox.selection_set(restore_index)
            self.truck_listbox.see(restore_index)
        elif selected_index is not None and selected_index < self.truck_listbox.size():
            self.truck_listbox.selection_set(selected_index)
        
        self._draw_trucks()
        
        self._update_selected_truck_info()
        
        self.root.after(500, self._update_display)
    
    def _draw_trucks(self):
        import math
        
        self.canvas.delete('truck')
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width <= 1:
            width = 800
        if height <= 1:
            height = 600
        
        scale_x = width / 100
        scale_y = height / 75
        
        if not self.trucks:
            center_x = width / 2
            center_y = height / 2
            self.canvas.create_text(center_x, center_y, 
                                   text="⏳ Aguardando conexão de caminhões...",
                                   fill='#718096', font=('Segoe UI', 14), tags='truck')
            return  # Sem caminhões para desenhar
        
        for truck_id, data in self.trucks.items():
            x = data.get('x', 50.0)  # Default no centro se não houver dados
            y = data.get('y', 37.5)
            theta = data.get('theta', 0)
            
            px = x * scale_x
            py = (75 - y) * scale_y
            
            if px < -100 or px > width + 100 or py < -100 or py > height + 100:
                print(f"[AVISO] Truck {truck_id} muito fora dos limites: x={x:.1f}, y={y:.1f} (px={px:.0f}, py={py:.0f})")
                continue
            
            status = data.get('status', 'UNKNOWN')
            if status == 'RUNNING':
                color = '#48bb78'
                outline_color = '#38a169'
            elif status == 'FAULT' or status == 'EMERGENCY':
                color = '#f56565'
                outline_color = '#e53e3e'
            else:
                color = '#f6ad55'
                outline_color = '#ed8936'
            
            size = 18
            
            front_x = px + size * math.cos(theta)
            front_y = py - size * math.sin(theta)
            
            left_x = px + (size * 0.7) * math.cos(theta + 2.5)
            left_y = py - (size * 0.7) * math.sin(theta + 2.5)
            
            right_x = px + (size * 0.7) * math.cos(theta - 2.5)
            right_y = py - (size * 0.7) * math.sin(theta - 2.5)
            
            shadow_offset = 3
            points_shadow = [
                front_x + shadow_offset, front_y + shadow_offset,
                left_x + shadow_offset, left_y + shadow_offset,
                right_x + shadow_offset, right_y + shadow_offset
            ]
            self.canvas.create_polygon(points_shadow, fill='#000000', outline='',
                                      stipple='gray50', tags='truck')
            
            points = [front_x, front_y, left_x, left_y, right_x, right_y]
            self.canvas.create_polygon(points, fill=color, outline=outline_color,
                                      width=2, tags='truck')
            
            highlight_size = size * 0.4
            highlight_x = px + highlight_size * math.cos(theta)
            highlight_y = py - highlight_size * math.sin(theta)
            self.canvas.create_oval(highlight_x - 3, highlight_y - 3,
                                   highlight_x + 3, highlight_y + 3,
                                   fill='white', outline='', tags='truck')
            
            label_y = py - 30
            self.canvas.create_rectangle(px - 25, label_y - 12, px + 25, label_y + 12,
                                         fill='#2d3748', outline='#4a5568', width=1, tags='truck')
            self.canvas.create_text(px, label_y, text=f"T{truck_id}",
                                   fill='white', font=('Segoe UI', 10, 'bold'), tags='truck')
            
            velocity = data.get('velocity', 0)
            if abs(velocity) > 0.1:
                vel_text = f"{velocity:.1f}m/s"
                self.canvas.create_text(px, py + 30, text=vel_text,
                                       fill='#90cdf4', font=('Segoe UI', 9), tags='truck')
    
    def _on_truck_select(self, event):
        selection = self.truck_listbox.curselection()
        if not selection:
            return
        
        text = self.truck_listbox.get(selection[0])
        truck_id = int(text.split()[1])
        
        self.selected_truck_id = truck_id
        
        if truck_id in self.trucks:
            data = self.trucks[truck_id]
            self.info_labels['Status:'].config(text=data.get('status', '-'))
            self.info_labels['Modo:'].config(text=data.get('mode', '-'))
            x = data.get('x', 0)
            y = data.get('y', 0)
            self.info_labels['Posição:'].config(text=f"({x:.1f}, {y:.1f})")
            self.info_labels['Velocidade:'].config(text=f"{data.get('velocity', 0):.1f} m/s")
            
            # Temperatura com indicador de status
            temp = data.get('temperature', 0)
            if temp > 120.0:
                temp_text = f"{temp:.1f}°C 🔴 FALHA"
                temp_color = '#e53e3e'
            elif temp > 95.0:
                temp_text = f"{temp:.1f}°C 🟡 ALERTA"
                temp_color = '#dd6b20'
            else:
                temp_text = f"{temp:.1f}°C 🟢"
                temp_color = '#2d3748'
            self.info_labels['Temperatura:'].config(text=temp_text, foreground=temp_color)
            
            electrical_fault = data.get('electrical_fault', False)
            hydraulic_fault = data.get('hydraulic_fault', False)
            self.info_labels['Falha Elétrica:'].config(text='SIM ⚡' if electrical_fault else 'NÃO')
            self.info_labels['Falha Hidráulica:'].config(text='SIM 🔧' if hydraulic_fault else 'NÃO')
            
            self._update_control_visibility(data.get('mode', '-'))
    
    def _update_selected_truck_info(self):
        if self.selected_truck_id and self.selected_truck_id in self.trucks:
            data = self.trucks[self.selected_truck_id]
            self.info_labels['Status:'].config(text=data.get('status', '-'))
            self.info_labels['Modo:'].config(text=data.get('mode', '-'))
            x = data.get('x', 0)
            y = data.get('y', 0)
            self.info_labels['Posição:'].config(text=f"({x:.1f}, {y:.1f})")
            self.info_labels['Velocidade:'].config(text=f"{data.get('velocity', 0):.1f} m/s")
            
            # Temperatura com indicador de status
            temp = data.get('temperature', 0)
            if temp > 120.0:
                temp_text = f"{temp:.1f}°C 🔴FALHA"
                temp_color = '#e53e3e'
            elif temp > 95.0:
                temp_text = f"{temp:.1f}°C 🟡ALERTA"
                temp_color = '#dd6b20'
            else:
                temp_text = f"{temp:.1f}°C 🟢"
                temp_color = '#2d3748'
            self.info_labels['Temperatura:'].config(text=temp_text, foreground=temp_color)
            
            electrical_fault = data.get('electrical_fault', False)
            hydraulic_fault = data.get('hydraulic_fault', False)
            self.info_labels['Falha Elétrica:'].config(text='SIM ⚡' if electrical_fault else 'NÃO')
            self.info_labels['Falha Hidráulica:'].config(text='SIM 🔧' if hydraulic_fault else 'NÃO')
    
    def _update_control_visibility(self, mode: str):
        if mode == 'MANUAL':
            self.manual_frame.grid(row=4, column=0, pady=10, sticky=(tk.W, tk.E))

            self.auto_frame.grid_remove()
        elif mode == 'AUTOMATIC':
            self.manual_frame.grid_remove()

            self.auto_frame.grid(row=4, column=0, pady=10, sticky=(tk.W, tk.E))
        else:

            self.manual_frame.grid_remove()
            self.auto_frame.grid_remove()
    
    def _get_selected_truck_id(self) -> int:

        return self.selected_truck_id
    
    def _check_truck_has_fault(self, truck_id: int) -> bool:
        """Verifica se o caminhão tem alguma falha ativa"""
        if truck_id in self.trucks:
            data = self.trucks[truck_id]
            return (data.get('electrical_fault', False) or 
                   data.get('hydraulic_fault', False) or
                   data.get('emergency_stop', False))
        return False
    
    def _send_auto_command(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"type": "ENABLE_AUTOMATIC"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✅ Modo AUTOMÁTICO enviado para caminhão {truck_id}")
            self._update_control_visibility('AUTOMATIC')
    
    def _send_manual_command(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"type": "DISABLE_AUTOMATIC"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✅ Modo MANUAL enviado para caminhão {truck_id}")
            self._update_control_visibility('MANUAL')
    
    def _send_emergency(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        if self.mqtt_client:
            payload = json.dumps({"type": "EMERGENCY_STOP"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"⚠ EMERGÊNCIA enviada para caminhão {truck_id}")
    
    def _send_setpoint(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        if not self.mqtt_client:
            return
        
        try:
            velocity = float(self.velocity_entry.get())
            payload = json.dumps({"velocity": velocity, "angular": 0.0})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/setpoint", payload, qos=1)
            self.status_bar.config(text=f"Setpoint enviado para caminhão {truck_id}")
        except ValueError:
            self.status_bar.config(text="Erro: velocidade inválida")
    
    def _send_reset_fault(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        if self.mqtt_client:
            payload = json.dumps({"type": "RESET_FAULT"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✓ REARME enviado para caminhão {truck_id}")
    
    def _send_forward(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"type": "MOVE_FORWARD"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✓ Comando FRENTE enviado")
    
    def _send_backward(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"type": "MOVE_BACKWARD"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✓ Comando RÉ enviado")
    
    def _send_left(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"type": "TURN_LEFT"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✓ Comando ESQUERDA enviado")
    
    def _send_right(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"type": "TURN_RIGHT"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✓ Comando DIREITA enviado")
    
    def _send_accelerate(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"type": "ACCELERATE"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✓ Comando ACELERAR enviado")
    
    def _send_brake(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"type": "BRAKE"})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/command", payload, qos=1)
            self.status_bar.config(text=f"✓ Comando FREIAR enviado")
    
    def _add_waypoint(self):
        try:
            x = float(self.waypoint_x_entry.get())
            y = float(self.waypoint_y_entry.get())
            
            if not (0 <= x <= 100 and 0 <= y <= 75):
                self.status_bar.config(text="⚠ Waypoint fora dos limites (0-100m, 0-75m)")
                return
            
            self.waypoints.append([x, y])
            self.waypoints_listbox.insert(tk.END, f"({x:.1f}, {y:.1f})")
            
            self.waypoint_x_entry.delete(0, tk.END)
            self.waypoint_y_entry.delete(0, tk.END)
            
            self.status_bar.config(text=f"✓ Waypoint adicionado: ({x:.1f}, {y:.1f})")
        except ValueError:
            self.status_bar.config(text="⚠ Valores inválidos para waypoint")
    
    def _remove_waypoint(self):
        selection = self.waypoints_listbox.curselection()
        if not selection:
            self.status_bar.config(text="⚠ Selecione um waypoint para remover")
            return
        
        index = selection[0]
        self.waypoints.pop(index)
        self.waypoints_listbox.delete(index)
        self.status_bar.config(text="✓ Waypoint removido")
    
    def _clear_waypoints(self):
        if not self.waypoints:
            self.status_bar.config(text="⚠ Lista de waypoints já está vazia")
            return
        
        self.waypoints.clear()
        self.waypoints_listbox.delete(0, tk.END)
        self.status_bar.config(text="✓ Todos os waypoints foram removidos")
    
    def _send_route(self):
        truck_id = self._get_selected_truck_id()
        if not truck_id:
            self.status_bar.config(text="⚠ Selecione um caminhão primeiro")
            return
        
        if self._check_truck_has_fault(truck_id):
            self.status_bar.config(text="⚠ Caminhão com FALHA ATIVA! Use REARMAR primeiro")
            return
        
        if not self.waypoints:
            self.status_bar.config(text="⚠ Adicione waypoints antes de enviar rota")
            return
        
        if self.mqtt_client:
            payload = json.dumps({"waypoints": self.waypoints})
            self.mqtt_client.publish(f"mine/truck/{truck_id}/route", payload, qos=1)
            self.status_bar.config(text=f"✓ Rota com {len(self.waypoints)} waypoints enviada")
    
    def run(self):
        self.root.mainloop()
    
    def cleanup(self):
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

def main():
    app = MineManagementGUI()
    try:
        app.run()
    finally:
        app.cleanup()

if __name__ == "__main__":
    main()

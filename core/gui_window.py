'''
Haptic GUI Window
햅틱 피드백 시스템 GUI 윈도우

역할:
- 실시간 그래프 표시 (3개 뉴런)
- 마우스 이벤트 처리
- 키보드 단축키 처리
- 상태 정보 표시
'''

import sys
import numpy as np
import time
from collections import deque
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QKeyEvent

# Matplotlib 설정
import matplotlib
matplotlib.use('QtAgg')
matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
    'axes.titlesize': 14,
    'axes.labelsize': 11,
    'xtick.labelsize': 9, 
    'ytick.labelsize': 9,
    'legend.fontsize': 10,
    'figure.dpi': 100,
    'figure.facecolor': '#1c1c1e',
    'axes.facecolor': '#1c1c1e',
    'axes.edgecolor': '#a0a0a0',
    'axes.labelcolor': '#e0e0e0',
    'text.color': '#f0f0f0',
    'xtick.color': '#c0c0c0',
    'ytick.color': '#c0c0c0',
    'grid.color': '#505050',
    'grid.linestyle': '--',
    'grid.alpha': 0.7,
    'lines.linewidth': 1.8
})

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from .haptic_system import HapticSystem

class HapticGUI(QMainWindow):
    """
    햅틱 피드백 시뮬레이션 GUI 윈도우
    
    기능:
    1. 3개 뉴런 실시간 그래프 표시
    2. 마우스 입력 이벤트 처리
    3. 키보드 단축키 처리
    4. 상태 정보 표시
    """
    
    def __init__(self, config):
        """GUI 윈도우 초기화"""
        super().__init__()
        self.config = config
        ui_cfg = config['ui']
        
        # 윈도우 설정
        self.setWindowTitle("Haptic Ring Monitoring - Neural Feedback System")
        self.setGeometry(50, 50, ui_cfg['window_width'], ui_cfg['window_height'])
        
        # === 햅틱 시스템 초기화 ===
        self.haptic_system = HapticSystem(config)
        
        # === UI 구성 ===
        self._setup_ui()
        
        # === 그래프 데이터 초기화 ===
        self._init_plot_data()
        
        # === 그래프 설정 ===
        self._setup_plots()
        
        # === 마우스 상태 변수 ===
        self.mouse_pressed = False
        self.last_mouse_pos = QPointF(0, 0)
        self.last_mouse_time = time.perf_counter()
        self.mouse_speed = 0.0
        self.speed_history = deque(maxlen=10)
        self.avg_mouse_speed = 0.0
        
        # === 그래프 업데이트 관련 ===
        self.plot_update_counter = 0
        self.plot_update_interval = config['plot']['update_interval']
        self.sa_spike_indices = deque(maxlen=config['plot_hist_sz'])
        self.ra_motion_spike_indices = deque(maxlen=config['plot_hist_sz'])
        self.ra_click_spike_indices = deque(maxlen=config['plot_hist_sz'])
        self.drawn_spike_lines = []
        
        # === 타이머 시작 ===
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_simulation)
        self.timer.start(int(config['neuron_dt_ms']))
        
        print("🖥️ GUI initialized successfully!")
    
    def _setup_ui(self):
        """UI 컴포넌트 설정"""
        # 메인 위젯
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        main_widget.setStyleSheet("background-color: #48484a;")
        
        # 사용법 안내 라벨
        self.info_label = QLabel("Click/SA+RA_Click, Move/RA_Motion (1-7 Materials)", self)
        font = self.info_label.font()
        font.setPointSize(16)
        self.info_label.setFont(font)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        
        # 상태 정보 라벨
        self.status_label = QLabel("Mat:Glass(R:0.1)|Spd:0|FR:0.0Hz|Vol:0.00", self)
        font = self.status_label.font()
        font.setPointSize(14)
        self.status_label.setFont(font)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 그래프 캔버스는 나중에 추가
        self.setCentralWidget(main_widget)
        self.main_layout = layout
    
    def _init_plot_data(self):
        """그래프 데이터 히스토리 초기화"""
        plot_hist_sz = self.config['plot_hist_sz']
        
        # SA 뉴런 히스토리
        sa_v_init = self.config['sa_neuron']['v_init']
        self.sa_v_hist = deque([sa_v_init] * plot_hist_sz, maxlen=plot_hist_sz)
        self.sa_u_hist = deque([0.0] * plot_hist_sz, maxlen=plot_hist_sz)
        
        # RA Motion 뉴런 히스토리
        ra_motion_v_init = self.config['ra_neuron']['v_init']
        self.ra_motion_v_hist = deque([ra_motion_v_init] * plot_hist_sz, maxlen=plot_hist_sz)
        self.ra_motion_u_hist = deque([0.0] * plot_hist_sz, maxlen=plot_hist_sz)
        
        # RA Click 뉴런 히스토리
        ra_click_v_init = self.config['ra_click_neuron']['v_init']
        self.ra_click_v_hist = deque([ra_click_v_init] * plot_hist_sz, maxlen=plot_hist_sz)
        self.ra_click_u_hist = deque([0.0] * plot_hist_sz, maxlen=plot_hist_sz)
        
        self.x_data = np.arange(plot_hist_sz)
    
    def _setup_plots(self):
        """3개 뉴런 그래프 설정"""
        ui_cfg = self.config['ui']
        plot_hist_sz = self.config['plot_hist_sz']
        
        # 그래프 생성
        self.figure = Figure(figsize=(7, 8))
        self.ax_sa, self.ax_ra_motion, self.ax_ra_click = self.figure.subplots(3, 1)
        
        # SA 뉴런 그래프
        self.sa_v_line, = self.ax_sa.plot(self.x_data, list(self.sa_v_hist), 
                                         lw=1.8, label='SA_v', color=ui_cfg['sa_line_color'])
        self.sa_u_line, = self.ax_sa.plot(self.x_data, list(self.sa_u_hist), 
                                         lw=1.8, label='SA_u', color=ui_cfg['ra_line_color'])
        self.ax_sa.set_title('SA Neuron (Pressure)')
        self.ax_sa.set_ylabel('V (mV), U', fontsize=11)
        self.ax_sa.set_ylim(ui_cfg['plot_y_min'], ui_cfg['plot_y_max'])
        self.ax_sa.set_xlim(0, plot_hist_sz - 1)
        self.ax_sa.legend(loc='upper right', frameon=False)
        self.ax_sa.grid(True)
        self.ax_sa.spines['top'].set_visible(False)
        self.ax_sa.spines['right'].set_visible(False)
        
        # RA Motion 뉴런 그래프
        self.ra_motion_v_line, = self.ax_ra_motion.plot(self.x_data, list(self.ra_motion_v_hist), 
                                                       lw=1.8, label='RA_Motion_v', color=ui_cfg['sa_line_color'])
        self.ra_motion_u_line, = self.ax_ra_motion.plot(self.x_data, list(self.ra_motion_u_hist), 
                                                       lw=1.8, label='RA_Motion_u', color=ui_cfg['ra_line_color'])
        self.ax_ra_motion.set_title('RA Motion Neuron (Movement)')
        self.ax_ra_motion.set_ylabel('V (mV), U', fontsize=11)
        self.ax_ra_motion.set_ylim(ui_cfg['plot_y_min'], ui_cfg['plot_y_max'])
        self.ax_ra_motion.set_xlim(0, plot_hist_sz - 1)
        self.ax_ra_motion.legend(loc='upper right', frameon=False)
        self.ax_ra_motion.grid(True)
        self.ax_ra_motion.spines['top'].set_visible(False)
        self.ax_ra_motion.spines['right'].set_visible(False)
        
        # RA Click 뉴런 그래프
        self.ra_click_v_line, = self.ax_ra_click.plot(self.x_data, list(self.ra_click_v_hist), 
                                                     lw=1.8, label='RA_Click_v', color=ui_cfg['sa_line_color'])
        self.ra_click_u_line, = self.ax_ra_click.plot(self.x_data, list(self.ra_click_u_hist), 
                                                     lw=1.8, label='RA_Click_u', color=ui_cfg['ra_line_color'])
        self.ax_ra_click.set_title('RA Click Neuron (Click On/Off)')
        self.ax_ra_click.set_ylabel('V (mV), U', fontsize=11)
        self.ax_ra_click.set_xlabel('Time (ms)', fontsize=12)
        self.ax_ra_click.set_ylim(ui_cfg['plot_y_min'], ui_cfg['plot_y_max'])
        self.ax_ra_click.set_xlim(0, plot_hist_sz - 1)
        self.ax_ra_click.legend(loc='upper right', frameon=False)
        self.ax_ra_click.grid(True)
        self.ax_ra_click.spines['top'].set_visible(False)
        self.ax_ra_click.spines['right'].set_visible(False)
        
        # 시간축 설정
        tick_locs = np.linspace(0, plot_hist_sz - 1, 6)
        tick_labels = np.linspace(2500, 0, 6).astype(int)
        for ax in [self.ax_sa, self.ax_ra_motion, self.ax_ra_click]:
            ax.set_xticks(tick_locs)
            ax.set_xticklabels(tick_labels)
        
        # 그래프 레이아웃 조정 및 캔버스 추가
        self.figure.tight_layout(pad=3.0)
        self.plot_canvas = FigureCanvas(self.figure)
        self.main_layout.addWidget(self.plot_canvas)
    
    def _update_simulation(self):
        """시뮬레이션 한 스텝 실행"""
        # 마우스 정지 감지
        if (time.perf_counter() - self.last_mouse_time) > self.config['mouse']['m_stop_thresh'] and self.mouse_pressed:
            self.mouse_speed = 0.0
            self._update_status_label()
        
        # 햅틱 시스템 스텝 실행
        sa_fired, ra_motion_fired, ra_click_fired, sa_vu, ra_motion_vu, ra_click_vu = self.haptic_system.step(
            mouse_speed=self.mouse_speed,
            avg_mouse_speed=self.avg_mouse_speed
        )
        
        # 뉴런 상태 히스토리 업데이트
        self.sa_v_hist.append(sa_vu[0])
        self.sa_u_hist.append(sa_vu[1])
        self.ra_motion_v_hist.append(ra_motion_vu[0])
        self.ra_motion_u_hist.append(ra_motion_vu[1])
        self.ra_click_v_hist.append(ra_click_vu[0])
        self.ra_click_u_hist.append(ra_click_vu[1])
        
        # 스파이크 인덱스 기록
        plot_hist_sz = self.config['plot_hist_sz']
        if sa_fired:
            self.sa_spike_indices.append(plot_hist_sz - 1)
        if ra_motion_fired:
            self.ra_motion_spike_indices.append(plot_hist_sz - 1)
        if ra_click_fired:
            self.ra_click_spike_indices.append(plot_hist_sz - 1)
        
        # 주기적으로 그래프 업데이트
        self.plot_update_counter += 1
        if self.plot_update_counter >= self.plot_update_interval:
            self._update_plots()
            self.plot_update_counter = 0
    
    def _update_plots(self):
        """그래프 업데이트"""
        # 기존 스파이크 라인 제거
        for line in self.drawn_spike_lines:
            line.remove()
        self.drawn_spike_lines.clear()
        
        # 그래프 데이터 업데이트
        self.sa_v_line.set_ydata(self.sa_v_hist)
        self.sa_u_line.set_ydata(self.sa_u_hist)
        self.ra_motion_v_line.set_ydata(self.ra_motion_v_hist)
        self.ra_motion_u_line.set_ydata(self.ra_motion_u_hist)
        self.ra_click_v_line.set_ydata(self.ra_click_v_hist)
        self.ra_click_u_line.set_ydata(self.ra_click_u_hist)
        
        # 스파이크 라인 그리기
        spike_color = self.config['ui']['spike_line_color']
        
        # SA 스파이크 라인
        visible_sa_spikes = list(self.sa_spike_indices)[-20:] if len(self.sa_spike_indices) > 20 else self.sa_spike_indices
        for x_idx in visible_sa_spikes:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_sa.axvline(x_idx, color=spike_color, ls='--', lw=1.2))
        
        # RA Motion 스파이크 라인
        visible_ra_motion_spikes = list(self.ra_motion_spike_indices)[-30:] if len(self.ra_motion_spike_indices) > 30 else self.ra_motion_spike_indices
        for x_idx in visible_ra_motion_spikes:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_ra_motion.axvline(x_idx, color=spike_color, ls='--', lw=1.2))
        
        # RA Click 스파이크 라인
        visible_ra_click_spikes = list(self.ra_click_spike_indices)[-15:] if len(self.ra_click_spike_indices) > 15 else self.ra_click_spike_indices
        for x_idx in visible_ra_click_spikes:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_ra_click.axvline(x_idx, color=spike_color, ls='--', lw=1.2))
        
        # 스파이크 인덱스 이동 (시간 흐름)
        self._shift_spike_indices()
        
        # 그래프 다시 그리기
        self.plot_canvas.draw_idle()
    
    def _shift_spike_indices(self):
        """스파이크 인덱스를 시간 흐름에 따라 이동"""
        interval = self.plot_update_interval
        
        # SA 스파이크 인덱스 이동
        new_sa_indices = deque(maxlen=self.sa_spike_indices.maxlen)
        for x_idx in self.sa_spike_indices:
            shifted_idx = x_idx - interval
            if shifted_idx >= 0:
                new_sa_indices.append(shifted_idx)
        self.sa_spike_indices = new_sa_indices
        
        # RA Motion 스파이크 인덱스 이동
        new_ra_motion_indices = deque(maxlen=self.ra_motion_spike_indices.maxlen)
        for x_idx in self.ra_motion_spike_indices:
            shifted_idx = x_idx - interval
            if shifted_idx >= 0:
                new_ra_motion_indices.append(shifted_idx)
        self.ra_motion_spike_indices = new_ra_motion_indices
        
        # RA Click 스파이크 인덱스 이동
        new_ra_click_indices = deque(maxlen=self.ra_click_spike_indices.maxlen)
        for x_idx in self.ra_click_spike_indices:
            shifted_idx = x_idx - interval
            if shifted_idx >= 0:
                new_ra_click_indices.append(shifted_idx)
        self.ra_click_spike_indices = new_ra_click_indices
    
    def _update_status_label(self):
        """상태 라벨 업데이트"""
        material = self.haptic_system.current_material_key
        roughness = self.haptic_system.current_roughness
        spike_rate = self.haptic_system.current_spike_rate
        volume = self.haptic_system.current_volume
        
        self.status_label.setText(
            f"Mat:{material}(R:{roughness:.1f})|Spd:{self.mouse_speed:.0f}|"
            f"FR:{spike_rate:.1f}Hz|Vol:{volume:.2f}"
        )
    
    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        self.mouse_pressed = True
        self.haptic_system.mouse_press()
        
        pos = event.position() if hasattr(event, 'position') else QPointF(event.x(), event.y())
        self.last_mouse_pos = pos
        self.last_mouse_time = time.perf_counter()
        self.mouse_speed = 0.0
        self.speed_history.clear()
        self.avg_mouse_speed = 0.0
        self._update_status_label()
    
    def mouseReleaseEvent(self, event):
        """마우스 릴리즈 이벤트"""
        self.mouse_pressed = False
        self.haptic_system.mouse_release()
        self.mouse_speed = 0.0
        self._update_status_label()
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트"""
        if self.mouse_pressed:
            current_time = time.perf_counter()
            dt = current_time - self.last_mouse_time
            current_pos = event.position() if hasattr(event, 'position') else QPointF(event.x(), event.y())
            
            if dt > 0.0001:  # 최소 시간 간격
                distance = np.sqrt((current_pos.x() - self.last_mouse_pos.x())**2 + 
                                 (current_pos.y() - self.last_mouse_pos.y())**2)
                self.mouse_speed = min(distance / dt, self.config['mouse']['max_spd_clamp'])
                self.speed_history.append(self.mouse_speed)
                self.avg_mouse_speed = np.mean(self.speed_history) if self.speed_history else 0.0
                
                self.last_mouse_pos = current_pos
                self.last_mouse_time = current_time
                self._update_status_label()
    
    def keyPressEvent(self, event: QKeyEvent):
        """키보드 이벤트 처리"""
        key = event.key()
        
        # 재질 변경 (1-7 키)
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_7:
            material_index = key - Qt.Key.Key_1
            if self.haptic_system.change_material(material_index):
                self._update_status_label()
        
        # 일시정지/재개 (스페이스바)
        elif key == Qt.Key.Key_Space:
            if self.timer.isActive():
                self.timer.stop()
                self.info_label.setText("PAUSED - Press SPACE to resume")
            else:
                self.timer.start(int(self.config['neuron_dt_ms']))
                self.info_label.setText("Click/SA+RA_Click, Move/RA_Motion (1-7 Materials)")
        
        # 시뮬레이션 리셋 (R 키)
        elif key == Qt.Key.Key_R:
            self._reset_simulation()
        
        # 볼륨 조절 (+/- 키)
        elif key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
            self._adjust_volume(0.1)
        elif key == Qt.Key.Key_Minus:
            self._adjust_volume(-0.1)
        
        # 종료 (ESC 키)
        elif key == Qt.Key.Key_Escape:
            self.close()
        
        else:
            super().keyPressEvent(event)
    
    def _reset_simulation(self):
        """시뮬레이션 리셋"""
        # 햅틱 시스템 재생성
        self.haptic_system.cleanup()
        self.haptic_system = HapticSystem(self.config)
        
        # 그래프 데이터 초기화
        self._init_plot_data()
        
        # 마우스 상태 초기화
        self.mouse_pressed = False
        self.mouse_speed = 0.0
        self.speed_history.clear()
        self.avg_mouse_speed = 0.0
        
        # 스파이크 인덱스 초기화
        self.sa_spike_indices.clear()
        self.ra_motion_spike_indices.clear()
        self.ra_click_spike_indices.clear()
        
        self._update_status_label()
        print("🔄 Simulation reset!")
    
    def _adjust_volume(self, delta):
        """볼륨 조절"""
        sound_cfg = self.config['sound']
        
        # 모든 사운드 볼륨 동시 조절
        sound_cfg['sa_sound_volume'] = max(0.0, min(1.0, sound_cfg['sa_sound_volume'] + delta))
        sound_cfg['ra_motion_max_vol_scl'] = max(0.0, min(1.0, sound_cfg['ra_motion_max_vol_scl'] + delta))
        sound_cfg['ra_click_volume'] = max(0.0, min(1.0, sound_cfg['ra_click_volume'] + delta))
        
        vol = sound_cfg['sa_sound_volume']
        print(f"🔊 Volume adjusted: SA={vol:.1f}, RA_Motion={sound_cfg['ra_motion_max_vol_scl']:.1f}, RA_Click={sound_cfg['ra_click_volume']:.1f}")
        self._update_status_label()
    
    def closeEvent(self, event):
        """윈도우 종료 이벤트"""
        self.haptic_system.cleanup()
        super().closeEvent(event) 
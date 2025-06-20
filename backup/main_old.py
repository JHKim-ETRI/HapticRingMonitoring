'''
Haptic Ring Monitoring - 햅틱 피드백 시뮬레이션 메인 프로그램
Izhikevich 뉴런 모델을 사용하여 촉각 수용체(SA, RA)의 반응을 시뮬레이션하고
마우스 입력을 실시간 오디오 피드백으로 변환하는 햅틱 렌더링 시스템

전체 시스템 구조:
마우스 입력 → SpikeEncoder → 뉴런 시뮬레이션 → HapticRenderer → AudioPlayer → 소리 출력
                                    ↓
                           실시간 그래프 시각화
'''

import sys
import numpy as np
import pygame
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QKeyEvent
import time
from collections import deque
import logging
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Matplotlib 설정 - 실시간 뉴런 상태 시각화용
import matplotlib
matplotlib.use('QtAgg')  # PyQt6과 호환되는 백엔드 사용

# 다크 테마 시각화 설정
matplotlib.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Helvetica Neue', 'Arial', 'DejaVu Sans'],
    'axes.titlesize': 14,
    'axes.labelsize': 11,
    'xtick.labelsize': 9, 
    'ytick.labelsize': 9,
    'legend.fontsize': 10,
    'figure.dpi': 100,
    'figure.facecolor': '#1c1c1e',    # 다크 배경
    'axes.facecolor': '#1c1c1e',      # 축 배경
    'axes.edgecolor': '#a0a0a0',      # 축 테두리
    'axes.labelcolor': '#e0e0e0',     # 축 라벨 색상
    'text.color': '#f0f0f0',          # 텍스트 색상
    'xtick.color': '#c0c0c0',         # X축 눈금 색상
    'ytick.color': '#c0c0c0',         # Y축 눈금 색상
    'grid.color': '#505050',          # 격자 색상
    'grid.linestyle': '--',           # 격자 스타일
    'grid.alpha': 0.7,                # 격자 투명도
    'lines.linewidth': 1.8            # 라인 두께
})

# 모듈 임포트 - 각 모듈의 역할
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from izhikevich_neuron import IzhikevichNeuron  # 뉴런 시뮬레이션
from audio_player import AudioPlayer              # 오디오 재생
from haptic_renderer import HapticRenderer        # 사운드 생성
from spike_encoder import SpikeEncoder            # 마우스→뉴런 변환

class Constants:
    """애플리케이션 전역 상수 정의"""
    DEFAULT_WINDOW_WIDTH = 1200        # 기본 윈도우 너비
    DEFAULT_WINDOW_HEIGHT = 1200       # 기본 윈도우 높이
    SPIKE_THRESHOLD = 30.0             # 스파이크 감지 임계값 (mV)
    MIN_MOUSE_DELTA_TIME = 0.0001      # 마우스 이벤트 최소 간격
    SPIKE_LINE_COLOR = '#e60026'       # 스파이크 표시 색상 (빨간색)
    SA_LINE_COLOR = '#007aff'          # SA 뉴런 표시 색상 (파란색)
    RA_LINE_COLOR = '#ff9500'          # RA 뉴런 표시 색상 (주황색)
    FADE_OUT_MS = 10                   # 사운드 페이드아웃 시간
    PLOT_Y_MIN = -90                   # 그래프 Y축 최소값
    PLOT_Y_MAX = 40                    # 그래프 Y축 최대값

class TestWindow(QMainWindow):
    """
    햅틱 피드백 시뮬레이션 메인 윈도우 클래스
    
    기능:
    1. SA/RA 뉴런의 실시간 상태 시각화 (막전위, 회복변수)
    2. 마우스 입력을 뉴런 자극으로 변환
    3. 뉴런 스파이크를 실시간 오디오로 출력
    4. 다양한 재질(S, M, R) 시뮬레이션
    5. 키보드 단축키로 시뮬레이션 제어
    
    데이터 흐름:
    마우스 입력 → SpikeEncoder → 뉴런 시뮬레이션 → 그래프 업데이트 + 오디오 출력
    """
    
    def __init__(self):
        """메인 윈도우 초기화 및 모든 컴포넌트 설정"""
        super().__init__()
        self.setWindowTitle("Izhikevich Haptic Test")
        self.setGeometry(50,50,Constants.DEFAULT_WINDOW_WIDTH,Constants.DEFAULT_WINDOW_HEIGHT)

        # 설정 로드 및 검증
        self.config = self._get_validated_config()
        self.neuron_dt_ms = self.config['neuron_dt_ms']  # 뉴런 시뮬레이션 시간 간격

        # === UI 구성 요소 초기화 ===
        main_w=QWidget(); layout=QVBoxLayout(main_w)
        main_w.setStyleSheet("background-color: #48484a;")  # 다크 테마 배경
        
        # 사용법 안내 라벨
        self.info_lbl=QLabel("Click/SA+RA_Click, Move/RA_Motion (1-7 Materials)",self)
        fnt=self.info_lbl.font();fnt.setPointSize(16);self.info_lbl.setFont(fnt)
        self.info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_lbl)
        
        # 상태 정보 라벨 (현재 재질, 마우스 속도, 볼륨 등)
        self.stat_lbl=QLabel("Mat:Glass(R:0.5)|Spd:0",self)
        fnt=self.stat_lbl.font();fnt.setPointSize(14);self.stat_lbl.setFont(fnt)
        self.stat_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.stat_lbl)

        # === 데이터 히스토리 초기화 (실시간 그래프용) ===
        self.plot_hist_sz=self.config['plot_hist_sz']  # 그래프에 표시할 데이터 포인트 수 (500개)
        
        # SA 뉴런 히스토리 초기화
        v_init_val_sa = self.config['sa_neuron']['v_init']  # SA 뉴런 초기 막전위
        sa_params = self.config['sa_neuron']
        u_init_sa = IzhikevichNeuron(sa_params['a'], sa_params['b'], sa_params['c'], sa_params['d'], v_init=v_init_val_sa).u
        self.sa_v_hist=deque([v_init_val_sa]*self.plot_hist_sz, maxlen=self.plot_hist_sz)  # SA 막전위 히스토리
        self.sa_u_hist=deque([u_init_sa]*self.plot_hist_sz, maxlen=self.plot_hist_sz)      # SA 회복변수 히스토리
        
        # RA 움직임 뉴런 히스토리 초기화
        v_init_val_ra_motion = self.config['ra_neuron']['v_init']  # RA 움직임 뉴런 초기 막전위
        ra_params_base = self.config['ra_neuron']
        u_init_ra_motion = IzhikevichNeuron(ra_params_base['base_a'], ra_params_base['base_b'], ra_params_base['base_c'], ra_params_base['base_d'], v_init=v_init_val_ra_motion).u
        self.ra_motion_v_hist=deque([v_init_val_ra_motion]*self.plot_hist_sz, maxlen=self.plot_hist_sz)  # RA 움직임 막전위 히스토리
        self.ra_motion_u_hist=deque([u_init_ra_motion]*self.plot_hist_sz, maxlen=self.plot_hist_sz)      # RA 움직임 회복변수 히스토리
        
        # RA 클릭 뉴런 히스토리 초기화
        v_init_val_ra_click = self.config['ra_click_neuron']['v_init']  # RA 클릭 뉴런 초기 막전위
        ra_click_params = self.config['ra_click_neuron']
        u_init_ra_click = IzhikevichNeuron(ra_click_params['a'], ra_click_params['b'], ra_click_params['c'], ra_click_params['d'], v_init=v_init_val_ra_click).u
        self.ra_click_v_hist=deque([v_init_val_ra_click]*self.plot_hist_sz, maxlen=self.plot_hist_sz)  # RA 클릭 막전위 히스토리
        self.ra_click_u_hist=deque([u_init_ra_click]*self.plot_hist_sz, maxlen=self.plot_hist_sz)      # RA 클릭 회복변수 히스토리
        
        self.x_data=np.arange(self.plot_hist_sz)  # X축 데이터 (시간축)

        # === 그래프 설정 (3개 뉴런용) ===
        self.fig=Figure(figsize=(7,8)); self.ax_sa,self.ax_ra_motion,self.ax_ra_click=self.fig.subplots(3,1)
        # SA 뉴런 그래프 설정
        self.sa_v_line,=self.ax_sa.plot(self.x_data,list(self.sa_v_hist),lw=1.8,label='SA_v', color='#007aff')
        self.sa_u_line,=self.ax_sa.plot(self.x_data,list(self.sa_u_hist),lw=1.8,label='SA_u', color='#ff9500')
        self.ax_sa.set_title('SA Neuron (Pressure)')
        self.ax_sa.set_ylabel('V (mV), U', fontsize=11)
        self.ax_sa.set_ylim(-90,40)
        self.ax_sa.set_xlim(0,self.plot_hist_sz-1);self.ax_sa.legend(loc='upper right', frameon=False);self.ax_sa.grid(True)
        self.ax_sa.spines['top'].set_visible(False); self.ax_sa.spines['right'].set_visible(False)

        tick_locs = np.linspace(0, self.plot_hist_sz - 1, 6)
        tick_labels = np.linspace(2500, 0, 6).astype(int)
        self.ax_sa.set_xticks(tick_locs)
        self.ax_sa.set_xticklabels(tick_labels)

        # RA 움직임 뉴런 그래프 설정
        self.ra_motion_v_line,=self.ax_ra_motion.plot(self.x_data,list(self.ra_motion_v_hist),lw=1.8,label='RA_Motion_v', color='#007aff')
        self.ra_motion_u_line,=self.ax_ra_motion.plot(self.x_data,list(self.ra_motion_u_hist),lw=1.8,label='RA_Motion_u', color='#ff9500')
        self.ax_ra_motion.set_title('RA Motion Neuron (Movement)')
        self.ax_ra_motion.set_ylabel('V (mV), U', fontsize=11)
        self.ax_ra_motion.set_ylim(-90,40)
        self.ax_ra_motion.set_xlim(0,self.plot_hist_sz-1);self.ax_ra_motion.legend(loc='upper right', frameon=False);self.ax_ra_motion.grid(True)
        self.ax_ra_motion.spines['top'].set_visible(False); self.ax_ra_motion.spines['right'].set_visible(False)
        self.ax_ra_motion.set_xticks(tick_locs)
        self.ax_ra_motion.set_xticklabels(tick_labels)

        # RA 클릭 뉴런 그래프 설정
        self.ra_click_v_line,=self.ax_ra_click.plot(self.x_data,list(self.ra_click_v_hist),lw=1.8,label='RA_Click_v', color='#007aff')
        self.ra_click_u_line,=self.ax_ra_click.plot(self.x_data,list(self.ra_click_u_hist),lw=1.8,label='RA_Click_u', color='#ff9500')
        self.ax_ra_click.set_title('RA Click Neuron (Click On/Off)')
        self.ax_ra_click.set_ylabel('V (mV), U', fontsize=11)
        self.ax_ra_click.set_ylim(-90,40)
        self.ax_ra_click.set_xlabel('Time (ms)', fontsize=12)
        self.ax_ra_click.set_xlim(0,self.plot_hist_sz-1);self.ax_ra_click.legend(loc='upper right', frameon=False);self.ax_ra_click.grid(True)
        self.ax_ra_click.spines['top'].set_visible(False); self.ax_ra_click.spines['right'].set_visible(False)
        self.ax_ra_click.set_xticks(tick_locs)
        self.ax_ra_click.set_xticklabels(tick_labels)

        self.fig.tight_layout(pad=3.0);self.plot_canvas=FigureCanvas(self.fig)
        layout.addWidget(self.plot_canvas);self.setCentralWidget(main_w)

        self.audio_player = AudioPlayer()
        self.haptic_renderer = HapticRenderer()

        self.spike_encoder = SpikeEncoder(
            sa_params=self.config['sa_neuron'],
            ra_params=self.config['ra_neuron'],
            ra_click_params=self.config['ra_click_neuron'],
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )

        self.materials = self.config['materials']
        self.mat_keys=list(self.materials.keys())
        self.curr_mat_key=self.mat_keys[0] 
        self.mat_roughness=self.materials[self.curr_mat_key]['r']

        self.sound_cache = {}
        self._init_sounds()

        # === 기존 개별 뉴런 변수들은 이제 SpikeEncoder에서 관리됨 ===
        # 모든 뉴런 시뮬레이션은 self.spike_encoder.step()을 통해 처리

        self.m_pressed=False;self.last_m_pos=QPointF(0,0)
        self.last_m_t=time.perf_counter();self.m_spd=0.0
        mouse_cfg = self.config['mouse']
        self.max_spd_clamp=mouse_cfg['max_spd_clamp']
        self.m_stop_thresh=mouse_cfg['m_stop_thresh']
        self.spd_hist=deque(maxlen=10);self.avg_m_spd=0.0

        self.plot_upd_cnt=0
        self.plot_upd_interval=self.config['plot']['update_interval']
        self.sa_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.ra_motion_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.ra_click_spike_idxs=deque(maxlen=self.plot_hist_sz)
        self.drawn_spike_lines=[]

        # === 시간 기반 스파이크 패턴 분석을 위한 변수들 (반응속도 개선) ===
        self.spike_window_duration_sec = 0.025  # 스파이크 추적 윈도우 지속시간 (25ms로 더 짧게 - 빠른 반응)
        self.ra_motion_spike_timestamps = deque()  # (timestamp, spike_occurred) 튜플들을 저장
        self.current_spike_rate = 0.0       # 현재 스파이크 발생률 (spikes/sec)
        self.target_volume = 0.0            # 목표 볼륨
        self.current_volume = 0.0           # 현재 볼륨 (부드러운 전환용)
        self.volume_smooth_factor = 0.4     # 볼륨 스무딩 계수 (0.15 → 0.4로 빠른 반응)
        self.volume_fast_decay_factor = 0.8 # 볼륨 감소 시 더 빠른 감쇠 (새로 추가)
        self.spike_rate_update_interval = 2  # 스파이크 발생률 계산 간격 (3 → 2프레임으로 더 자주)
        self.spike_rate_update_counter = 0   # 스파이크 발생률 계산 카운터
        self.last_spike_window_info = {     # 디버깅용 정보 (초기화)
            'total_records': 0, 
            'spike_count': 0, 
            'duration': 0.0,
            'target_duration': 0.025
        }

        self.update_stat_lbl()
        self.timer=QTimer(self);self.timer.timeout.connect(self.update_neuron);self.timer.start(int(self.neuron_dt_ms))

        self.last_neuron_update_time = time.perf_counter()

        # === 연속 재생용 루프 사운드 생성 및 시작 ===
        self._init_loop_sounds()
        if hasattr(self, 'ra_motion_loop_snd'):
            self.audio_player.start_continuous_sound(self.ra_motion_loop_snd, channel_id=1, initial_volume=0.0)

    def _init_sounds(self):
        """사운드 객체들 초기화 - SA, RA 움직임, RA 클릭 각각 다른 주파수"""
        snd_cfg = self.config['sound']
        
        # SA 뉴런 사운드 (낮은 주파수, 긴 지속시간)
        self.sa_snd = self.haptic_renderer.create_sound_object(
            snd_cfg['sa_hz'], snd_cfg['sa_ms'], snd_cfg['sa_amp'], fade_out_ms=10
        )
        
        # 재질별로 RA 움직임과 RA 클릭 사운드 생성
        for mat_key, mat_props in self.materials.items():
            # RA 움직임 뉴런 사운드 (재질별 특화 파형)
            ra_motion_hz = int(snd_cfg['ra_motion_base_hz'] * mat_props['f'])
            ra_motion_cache_key = f"ra_motion_{mat_key}_{ra_motion_hz}"
            
            if 'type' in mat_props:
                # 재질별 특성 파라미터 추출
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                self.sound_cache[ra_motion_cache_key] = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_motion_hz, snd_cfg['ra_motion_ms'], snd_cfg['ra_motion_base_amp'], 
                    fade_out_ms=10, **material_params
                )
                print(f"Created {mat_props['type']} RA_Motion sound for {mat_key}: {ra_motion_hz}Hz with params {material_params}")
            else:
                # 기본 사인파 사용
                self.sound_cache[ra_motion_cache_key] = self.haptic_renderer.create_sound_object(
                    ra_motion_hz, snd_cfg['ra_motion_ms'], snd_cfg['ra_motion_base_amp'], fade_out_ms=10
                )
            
            # RA 클릭 뉴런 사운드도 재질별로 생성 (NEW!)
            ra_click_hz = int(snd_cfg['ra_click_hz'] * mat_props['f'])  # 재질별 주파수 계수 적용
            ra_click_cache_key = f"ra_click_{mat_key}_{ra_click_hz}"
            
            if 'type' in mat_props:
                # 클릭은 짧고 강하게 - 진폭을 1.2배로 증가, 지속시간은 그대로
                click_amp = snd_cfg['ra_click_amp'] * 1.2
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                self.sound_cache[ra_click_cache_key] = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_click_hz, snd_cfg['ra_click_ms'], click_amp, 
                    fade_out_ms=5, **material_params  # 클릭은 더 빠른 페이드아웃
                )
                print(f"Created {mat_props['type']} RA_Click sound for {mat_key}: {ra_click_hz}Hz")
            else:
                # 기본 사인파 사용
                self.sound_cache[ra_click_cache_key] = self.haptic_renderer.create_sound_object(
                    ra_click_hz, snd_cfg['ra_click_ms'], snd_cfg['ra_click_amp'], fade_out_ms=5
                )
        
        # 현재 재질의 사운드들 설정
        self.ra_motion_snd = self.sound_cache[f"ra_motion_{self.curr_mat_key}_{int(snd_cfg['ra_motion_base_hz'] * self.materials[self.curr_mat_key]['f'])}"]
        self.ra_click_snd = self.sound_cache[f"ra_click_{self.curr_mat_key}_{int(snd_cfg['ra_click_hz'] * self.materials[self.curr_mat_key]['f'])}"]

    def _init_loop_sounds(self):
        """연속 재생용 루프 사운드들 초기화"""
        snd_cfg = self.config['sound']
        
        # 각 재질별로 루프 사운드 생성 (더 긴 지속시간으로 자연스러운 루프)
        loop_duration_ms = 2000  # 2초 길이로 루프 사운드 생성
        
        for mat_key, mat_props in self.materials.items():
            ra_motion_hz = int(snd_cfg['ra_motion_base_hz'] * mat_props['f'])
            ra_motion_cache_key = f"ra_motion_loop_{mat_key}_{ra_motion_hz}"
            
            if 'type' in mat_props:
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                # 루프용이므로 페이드아웃 없음 (0ms)
                self.sound_cache[ra_motion_cache_key] = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_motion_hz, loop_duration_ms, snd_cfg['ra_motion_base_amp'], 
                    fade_out_ms=0, **material_params
                )
            else:
                self.sound_cache[ra_motion_cache_key] = self.haptic_renderer.create_sound_object(
                    ra_motion_hz, loop_duration_ms, snd_cfg['ra_motion_base_amp'], fade_out_ms=0
                )
        
        # 현재 재질의 루프 사운드 설정
        self.ra_motion_loop_snd = self.sound_cache[f"ra_motion_loop_{self.curr_mat_key}_{int(snd_cfg['ra_motion_base_hz'] * self.materials[self.curr_mat_key]['f'])}"]

    def _update_ra_motion_sound(self):
        """재질 변경 시 RA 움직임 루프 사운드와 RA 클릭 뉴런 사운드 모두 업데이트"""
        mat_props = self.materials[self.curr_mat_key]
        snd_cfg = self.config['sound']
        
        # 기존 연속 사운드 중지
        if self.audio_player.is_continuous_playing(1):
            self.audio_player.stop_continuous_sound(1)
        
        # 새로운 재질의 루프 사운드로 변경
        ra_motion_hz = int(snd_cfg['ra_motion_base_hz'] * mat_props['f'])
        ra_motion_cache_key = f"ra_motion_loop_{self.curr_mat_key}_{ra_motion_hz}"
        
        if ra_motion_cache_key in self.sound_cache:
            self.ra_motion_loop_snd = self.sound_cache[ra_motion_cache_key]
        else:
            # 재질별 특화 루프 사운드 새로 생성
            loop_duration_ms = 2000
            if 'type' in mat_props:
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                self.ra_motion_loop_snd = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_motion_hz, loop_duration_ms, snd_cfg['ra_motion_base_amp'], 
                    fade_out_ms=0, **material_params
                )
                self.sound_cache[ra_motion_cache_key] = self.ra_motion_loop_snd
            else:
                self.ra_motion_loop_snd = self.haptic_renderer.create_sound_object(
                    ra_motion_hz, loop_duration_ms, snd_cfg['ra_motion_base_amp'], fade_out_ms=0
                )
                self.sound_cache[ra_motion_cache_key] = self.ra_motion_loop_snd
        
        # 새로운 루프 사운드 시작 (현재 볼륨으로)
        self.audio_player.start_continuous_sound(self.ra_motion_loop_snd, channel_id=1, initial_volume=self.current_volume)
        
        # RA 클릭 사운드 업데이트 (기존 로직 유지)
        ra_click_hz = int(snd_cfg['ra_click_hz'] * mat_props['f'])
        ra_click_cache_key = f"ra_click_{self.curr_mat_key}_{ra_click_hz}"
        
        if ra_click_cache_key in self.sound_cache:
            self.ra_click_snd = self.sound_cache[ra_click_cache_key]
        else:
            # 재질별 특화 파형 사용
            if 'type' in mat_props:
                click_amp = snd_cfg['ra_click_amp'] * 1.2
                material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
                self.ra_click_snd = self.haptic_renderer.create_material_sound(
                    mat_props['type'], ra_click_hz, snd_cfg['ra_click_ms'], click_amp, 
                    fade_out_ms=5, **material_params
                )
                self.sound_cache[ra_click_cache_key] = self.ra_click_snd
            else:
                self.ra_click_snd = self.haptic_renderer.create_sound_object(
                    ra_click_hz, snd_cfg['ra_click_ms'], snd_cfg['ra_click_amp'], fade_out_ms=5
                )
                self.sound_cache[ra_click_cache_key] = self.ra_click_snd
        
        self.update_stat_lbl()

    def keyPressEvent(self,e:QKeyEvent):
        k=e.key()
        if Qt.Key.Key_1<=k<=Qt.Key.Key_7:
            if k-Qt.Key.Key_1 < len(self.mat_keys):
                self.curr_mat_key=self.mat_keys[k-Qt.Key.Key_1]
                self.mat_roughness=self.materials[self.curr_mat_key]['r']; self._update_ra_motion_sound()
        elif k == Qt.Key.Key_Space:
            if self.timer.isActive():
                self.timer.stop()
                self.info_lbl.setText("PAUSED - Press SPACE to resume")
            else:
                self.timer.start(int(self.neuron_dt_ms))
                self.info_lbl.setText("Click/SA+RA_Click, Move/RA_Motion (1-7 Materials)")
        elif k == Qt.Key.Key_R:
            self._reset_simulation()
        elif k == Qt.Key.Key_Plus or k == Qt.Key.Key_Equal:
            self._adjust_volume(0.1)
        elif k == Qt.Key.Key_Minus:
            self._adjust_volume(-0.1)
        elif k == Qt.Key.Key_Escape:
            self.close()
        else: 
            super().keyPressEvent(e)

    def _reset_simulation(self):
        self.spike_encoder = SpikeEncoder(
            sa_params=self.config['sa_neuron'],
            ra_params=self.config['ra_neuron'],
            ra_click_params=self.config['ra_click_neuron'],
            neuron_dt_ms=self.config['neuron_dt_ms'],
            input_config=self.config['input_current']
        )
        
        v_init_sa = self.config['sa_neuron']['v_init']
        v_init_ra_motion = self.config['ra_neuron']['v_init']
        v_init_ra_click = self.config['ra_click_neuron']['v_init']
        
        self.sa_v_hist.clear()
        self.sa_u_hist.clear()
        self.ra_motion_v_hist.clear()
        self.ra_motion_u_hist.clear()
        self.ra_click_v_hist.clear()
        self.ra_click_u_hist.clear()
        
        for _ in range(self.plot_hist_sz):
            self.sa_v_hist.append(v_init_sa)
            self.sa_u_hist.append(0.0)
            self.ra_motion_v_hist.append(v_init_ra_motion)
            self.ra_motion_u_hist.append(0.0)
            self.ra_click_v_hist.append(v_init_ra_click)
            self.ra_click_u_hist.append(0.0)
        
        self.sa_spike_idxs.clear()
        self.ra_motion_spike_idxs.clear()
        self.ra_click_spike_idxs.clear()
        
        self.m_pressed = False
        self.m_spd = 0.0
        self.spd_hist.clear()
        self.avg_m_spd = 0.0
        
        # 스파이크 히스토리 및 볼륨 변수 초기화
        self.ra_motion_spike_timestamps.clear()
        self.current_spike_rate = 0.0
        self.target_volume = 0.0
        self.current_volume = 0.0
        
        # 연속 사운드 볼륨 초기화
        if self.audio_player.is_continuous_playing(1):
            self.audio_player.set_continuous_volume(1, 0.0)
        
        self.update_stat_lbl()
        print("Simulation reset!")

    def _adjust_volume(self, delta):
        """모든 뉴런 사운드의 볼륨을 동시에 조절"""
        self.config['sound']['sa_sound_volume'] = max(0.0, min(1.0, 
            self.config['sound']['sa_sound_volume'] + delta))
        
        self.config['sound']['ra_motion_max_vol_scl'] = max(0.0, min(1.0,
            self.config['sound']['ra_motion_max_vol_scl'] + delta))
            
        self.config['sound']['ra_click_volume'] = max(0.0, min(1.0,
            self.config['sound']['ra_click_volume'] + delta))
        
        vol = self.config['sound']['sa_sound_volume']
        print(f"Volume adjusted: SA={vol:.1f}, RA_Motion={self.config['sound']['ra_motion_max_vol_scl']:.1f}, RA_Click={self.config['sound']['ra_click_volume']:.1f}")
        
        self.update_stat_lbl()

    def _calculate_spike_rate(self):
        """
        실제 시간 기반으로 최근 윈도우 내 스파이크 발생률 계산
        
        Returns:
        - float: 스파이크 발생률 (spikes/second)
        """
        current_time = time.perf_counter()
        cutoff_time = current_time - self.spike_window_duration_sec
        
        # 오래된 스파이크 기록들 제거 (윈도우 밖의 데이터)
        while self.ra_motion_spike_timestamps and self.ra_motion_spike_timestamps[0][0] < cutoff_time:
            self.ra_motion_spike_timestamps.popleft()
        
        # 윈도우 내의 실제 스파이크 개수 계산
        spike_count = sum(1 for timestamp, spike_occurred in self.ra_motion_spike_timestamps if spike_occurred)
        
        # 실제 윈도우 지속시간 계산 (데이터가 있는 경우)
        if len(self.ra_motion_spike_timestamps) > 0:
            # 가장 오래된 기록부터 현재까지의 실제 시간
            oldest_time = self.ra_motion_spike_timestamps[0][0]
            actual_window_duration = current_time - oldest_time
            
            # 최소 윈도우 시간 보장 (너무 짧은 시간으로 나누어지는 것 방지)
            effective_duration = max(actual_window_duration, 0.005)  # 최소 5ms
            
            # 하지만 설정된 윈도우 크기를 초과하지 않도록 제한
            effective_duration = min(effective_duration, self.spike_window_duration_sec)
        else:
            effective_duration = self.spike_window_duration_sec
        
        # 디버깅 정보 저장
        self.last_spike_window_info = {
            'total_records': len(self.ra_motion_spike_timestamps),
            'spike_count': spike_count,
            'duration': effective_duration,
            'target_duration': self.spike_window_duration_sec
        }
        
        # 스파이크 발생률 계산 (spikes/second)
        spike_rate = spike_count / effective_duration if effective_duration > 0 else 0.0
        
        return spike_rate

    def _spike_rate_to_volume(self, spike_rate):
        """
        스파이크 발생률을 볼륨으로 변환
        
        Parameters:
        - spike_rate: 스파이크 발생률 (spikes/second)
        
        Returns:
        - float: 목표 볼륨 (0.0~1.0)
        """
        snd_cfg = self.config['sound']
        
        # 스파이크 발생률 기반 볼륨 매핑 설정 (25ms 윈도우에 최적화)
        min_spike_rate = 20.0   # 최소 볼륨을 적용할 스파이크 발생률 (20 spikes/sec) - 더 높은 시작점
        max_spike_rate = 120.0  # 최대 볼륨을 적용할 스파이크 발생률 (120 spikes/sec) - 더 높은 범위
        min_volume = snd_cfg['ra_motion_min_vol_scl']  # 최소 볼륨
        max_volume = snd_cfg['ra_motion_max_vol_scl']  # 최대 볼륨
        
        if spike_rate <= 0:
            return 0.0  # 스파이크가 없으면 볼륨 0
        elif spike_rate <= min_spike_rate:
            return min_volume
        elif spike_rate >= max_spike_rate:
            return max_volume
        else:
            # 선형 보간으로 볼륨 계산
            volume_range = max_volume - min_volume
            rate_range = max_spike_rate - min_spike_rate
            volume = min_volume + ((spike_rate - min_spike_rate) / rate_range) * volume_range
            return np.clip(volume, 0.0, 1.0)

    def update_stat_lbl(self):
        vol = self.config['sound']['sa_sound_volume']
        spike_rate = getattr(self, 'current_spike_rate', 0.0)
        current_vol = getattr(self, 'current_volume', 0.0)
        
        # 스파이크 윈도우 정보 추가 (안전한 기본값 설정)
        default_window_info = {
            'total_records': 0, 
            'spike_count': 0, 
            'duration': 0.0,
            'target_duration': 0.025
        }
        window_info = getattr(self, 'last_spike_window_info', default_window_info)
        
        self.stat_lbl.setText(
            f"Mat:{self.curr_mat_key}(R:{self.mat_roughness:.1f})|Spd:{self.m_spd:.0f}|"
            f"FR:{spike_rate:.1f}Hz({window_info['spike_count']}/{window_info['total_records']} in {window_info['duration']*1000:.0f}ms)|"
            f"Vol:{current_vol:.2f}"
        )

    def mousePressEvent(self,e:QPointF):
        self.m_pressed=True
        self.spike_encoder.update_sa_input(self.config['input_current']['click_mag'])
        p=e.position() if hasattr(e,'position') else QPointF(e.x(),e.y())
        self.last_m_pos=p; self.last_m_t=time.perf_counter(); self.m_spd=0.0; self.spd_hist.clear(); self.avg_m_spd=0.0
        self.update_stat_lbl()

    def mouseReleaseEvent(self,e:QPointF):
        self.m_pressed=False
        self.spike_encoder.update_sa_input(0.0)
        self.m_spd=0.0
        
        # === 즉시 볼륨 0으로 (끊으면 딱 끊기는 효과) ===
        self.target_volume = 0.0
        self.current_volume = 0.0  # 즉시 0으로 설정
        if self.audio_player.is_continuous_playing(1):
            self.audio_player.set_continuous_volume(1, 0.0)
        
        self.update_stat_lbl()

    def mouseMoveEvent(self,e:QPointF):
        if self.m_pressed:
            t_now=time.perf_counter(); dt=t_now-self.last_m_t; p_now=e.position() if hasattr(e,'position') else QPointF(e.x(),e.y())
            if dt>Constants.MIN_MOUSE_DELTA_TIME:
                dist=np.sqrt((p_now.x()-self.last_m_pos.x())**2+(p_now.y()-self.last_m_pos.y())**2)
                self.m_spd=min(dist/dt,self.max_spd_clamp); self.spd_hist.append(self.m_spd)
                self.avg_m_spd=np.mean(self.spd_hist) if self.spd_hist else 0.0
                self.last_m_pos=p_now; self.last_m_t=t_now; self.update_stat_lbl()

    def update_plots(self):
        """3개 뉴런 그래프 업데이트 (SA, RA Motion, RA Click) - 성능 최적화"""
        # 기존 스파이크 라인들 제거
        for line in self.drawn_spike_lines: line.remove()
        self.drawn_spike_lines.clear()

        # === SA 뉴런 그래프 업데이트 (최적화: list() 변환 제거) ===
        self.sa_v_line.set_ydata(self.sa_v_hist); self.sa_u_line.set_ydata(self.sa_u_hist)
        new_sa_spike_idxs=deque(maxlen=self.sa_spike_idxs.maxlen)
        # 스파이크 라인 개수 증가 (10개 → 20개로 더 많은 시각적 피드백)
        visible_spikes = list(self.sa_spike_idxs)[-20:] if len(self.sa_spike_idxs) > 20 else self.sa_spike_idxs
        for x_idx in visible_spikes:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_sa.axvline(x_idx,color='#e60026',ls='--',lw=1.2))
        # 인덱스 이동 처리
        for x_idx in self.sa_spike_idxs:
            shifted_idx = x_idx - self.plot_upd_interval
            if shifted_idx >= 0: 
                new_sa_spike_idxs.append(shifted_idx)
        self.sa_spike_idxs = new_sa_spike_idxs

        # === RA 움직임 뉴런 그래프 업데이트 (최적화: list() 변환 제거) ===
        self.ra_motion_v_line.set_ydata(self.ra_motion_v_hist); self.ra_motion_u_line.set_ydata(self.ra_motion_u_hist)
        new_ra_motion_spike_idxs=deque(maxlen=self.ra_motion_spike_idxs.maxlen)
        # 스파이크 라인 개수 증가 (15개 → 30개로 더 많은 RA motion 시각화)
        visible_spikes = list(self.ra_motion_spike_idxs)[-30:] if len(self.ra_motion_spike_idxs) > 30 else self.ra_motion_spike_idxs
        for x_idx in visible_spikes:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_ra_motion.axvline(x_idx,color='#e60026',ls='--',lw=1.2))
        # 인덱스 이동 처리
        for x_idx in self.ra_motion_spike_idxs:
            shifted_idx = x_idx - self.plot_upd_interval
            if shifted_idx >= 0:
                new_ra_motion_spike_idxs.append(shifted_idx)
        self.ra_motion_spike_idxs = new_ra_motion_spike_idxs
        
        # === RA 클릭 뉴런 그래프 업데이트 (최적화: list() 변환 제거) ===
        self.ra_click_v_line.set_ydata(self.ra_click_v_hist); self.ra_click_u_line.set_ydata(self.ra_click_u_hist)
        new_ra_click_spike_idxs=deque(maxlen=self.ra_click_spike_idxs.maxlen)
        # 스파이크 라인 개수 증가 (8개 → 15개로 더 많은 클릭 시각화)
        visible_spikes = list(self.ra_click_spike_idxs)[-15:] if len(self.ra_click_spike_idxs) > 15 else self.ra_click_spike_idxs
        for x_idx in visible_spikes:
            if x_idx >= 0:
                self.drawn_spike_lines.append(self.ax_ra_click.axvline(x_idx,color='#e60026',ls='--',lw=1.2))
        # 인덱스 이동 처리
        for x_idx in self.ra_click_spike_idxs:
            shifted_idx = x_idx - self.plot_upd_interval
            if shifted_idx >= 0:
                new_ra_click_spike_idxs.append(shifted_idx)
        self.ra_click_spike_idxs = new_ra_click_spike_idxs
        
        # 그래프 업데이트 최적화: blit 사용 대신 간단한 draw
        self.plot_canvas.draw_idle()  # draw() 대신 draw_idle() 사용으로 성능 향상

    def update_neuron(self):
        """
        뉴런 시뮬레이션의 핵심 업데이트 함수 (1ms마다 호출)
        
        처리 과정:
        1. 마우스 속도 상태 확인 및 업데이트
        2. SpikeEncoder를 통한 뉴런 시뮬레이션 실행
        3. 뉴런 상태 데이터 히스토리에 추가
        4. 스파이크 발생 시 오디오 피드백 재생
        5. 주기적으로 그래프 업데이트
        
        데이터 흐름:
        마우스 상태 → SpikeEncoder → 뉴런 상태 → 그래프 히스토리 + 오디오 출력
        """
        current_time = time.perf_counter()
        elapsed_time = (current_time - self.last_neuron_update_time) * 1000
        self.last_neuron_update_time = current_time

        # 마우스 정지 감지 (일정 시간 이상 움직임이 없으면 속도를 0으로 설정)
        if (time.perf_counter()-self.last_m_t)>self.config['mouse']['m_stop_thresh'] and self.m_pressed:
            self.m_spd=0.0;
            self.update_stat_lbl()
        
        # === 3개 뉴런 시뮬레이션 실행 ===
        # SpikeEncoder를 통해 마우스 입력을 뉴런 자극으로 변환하고 시뮬레이션 실행
        sa_f, ra_motion_f, ra_click_f, sa_vu, ra_motion_vu, ra_click_vu = self.spike_encoder.step(
            mouse_speed=self.m_spd,              # 현재 마우스 속도
            avg_mouse_speed=self.avg_m_spd,      # 평균 마우스 속도
            material_roughness=self.mat_roughness, # 현재 선택된 재질의 거칠기
            mouse_pressed=self.m_pressed         # 마우스 클릭 상태
        )

        # === 뉴런 상태 데이터 히스토리 업데이트 ===
        # 실시간 그래프 표시를 위해 최신 뉴런 상태를 히스토리에 추가
        self.sa_v_hist.append(sa_vu[0]); self.sa_u_hist.append(sa_vu[1])  # SA 뉴런 (v, u)
        self.ra_motion_v_hist.append(ra_motion_vu[0]); self.ra_motion_u_hist.append(ra_motion_vu[1])  # RA 움직임 뉴런 (v, u)
        self.ra_click_v_hist.append(ra_click_vu[0]); self.ra_click_u_hist.append(ra_click_vu[1])  # RA 클릭 뉴런 (v, u)

        # === SA 뉴런 스파이크 처리 ===
        if sa_f:  # SA 뉴런이 스파이크를 발생시킨 경우
            # 그래프에 스파이크 마커 추가 (맨 오른쪽 위치)
            self.sa_spike_idxs.append(self.plot_hist_sz-1)
            # SA 뉴런 전용 사운드 재생 (채널 0, 설정된 볼륨)
            sa_volume = self.config['sound'].get('sa_sound_volume', 1.0)
            self.audio_player.play_sound(self.sa_snd, channel_id=0, volume=sa_volume)
            print(f"🔴 SA SPIKE! Volume: {sa_volume:.2f}")  # 디버깅용

        # === RA 움직임 뉴런 - 시간 기반 스파이크 패턴 분석 ===
        # 스파이크 히스토리에 현재 시간과 스파이크 여부 기록
        self.ra_motion_spike_timestamps.append((current_time, ra_motion_f))
        
        if ra_motion_f:
            self.ra_motion_spike_idxs.append(self.plot_hist_sz-1)
        
        # 스파이크 발생률 계산 (성능 최적화를 위해 주기적으로만 계산)
        self.spike_rate_update_counter += 1
        if self.spike_rate_update_counter >= self.spike_rate_update_interval:
            self.current_spike_rate = self._calculate_spike_rate()
            self.spike_rate_update_counter = 0
        
        # 마우스가 눌려있고 실제 스파이크 활동이 있을 때만 사운드 활성화
        if self.m_pressed and self.current_spike_rate > 0:
            # 스파이크 발생률을 볼륨으로 변환
            self.target_volume = self._spike_rate_to_volume(self.current_spike_rate)
        else:
            # 마우스가 눌리지 않았거나 스파이크가 없으면 즉시 볼륨 0
            self.target_volume = 0.0
        
        # 적응형 볼륨 전환 (증가 시 부드럽게, 감소 시 빠르게)
        if self.target_volume > self.current_volume:
            # 볼륨 증가 시: 부드러운 전환
            smooth_factor = self.volume_smooth_factor
        else:
            # 볼륨 감소 시: 빠른 감쇠 (더 즉각적인 반응)
            smooth_factor = self.volume_fast_decay_factor
        
        self.current_volume += (self.target_volume - self.current_volume) * smooth_factor
        
        # 매우 작은 차이는 목표값으로 스냅 (임계값 확대로 더 빠른 수렴)
        if abs(self.current_volume - self.target_volume) < 0.005:
            self.current_volume = self.target_volume
        
        # 연속 사운드 볼륨 설정
        if self.audio_player.is_continuous_playing(1):
            if abs(self.current_volume - getattr(self, 'last_logged_volume', 0.0)) > 0.05:  # 볼륨 변화가 0.05 이상일 때만 로그
                print(f"🔵 RA MOTION Volume: {self.current_volume:.2f} (target: {self.target_volume:.2f}, rate: {self.current_spike_rate:.1f}Hz)")
                self.last_logged_volume = self.current_volume
            self.audio_player.set_continuous_volume(1, self.current_volume)

        # === RA 클릭 뉴런 스파이크 처리 ===
        if ra_click_f:  # RA 클릭 뉴런이 스파이크를 발생시킨 경우
            # 그래프에 스파이크 마커 추가
            self.ra_click_spike_idxs.append(self.plot_hist_sz-1)
            # RA 클릭 뉴런 전용 사운드 재생 (채널 2, 고정 볼륨)
            ra_click_volume = self.config['sound'].get('ra_click_volume', 1.0)
            self.audio_player.play_sound(self.ra_click_snd, channel_id=2, volume=ra_click_volume)
            print(f"🟡 RA CLICK SPIKE! Volume: {ra_click_volume:.2f}")  # 디버깅용

        # === 연속 사운드 볼륨 업데이트 (매 프레임마다 호출) ===
        self.audio_player.update_volumes()

        # === 그래프 업데이트 ===
        # 매 프레임마다 그래프를 업데이트하면 성능 저하가 발생하므로 주기적으로만 업데이트
        self.plot_upd_cnt+=1
        if self.plot_upd_cnt>=self.plot_upd_interval:  # 설정된 간격마다 업데이트 (기본: 8프레임)
            self.update_plots()  # 실제 그래프 화면 갱신
            self.plot_upd_cnt=0

    def closeEvent(self, e):
        """종료 시 연속 사운드들 정리"""
        # 모든 연속 사운드 중지
        if hasattr(self, 'audio_player'):
            if hasattr(self.audio_player, 'continuous_channels'):
                for channel_id in list(self.audio_player.continuous_channels.keys()):
                    self.audio_player.stop_continuous_sound(channel_id)
            self.audio_player.quit()
        super().closeEvent(e)

    def _get_validated_config(self):
        """
        햅틱 피드백 시스템의 모든 설정값을 정의하는 함수
        뉴런 모델, 사운드, 재질 등 시스템 전체 파라미터를 포함
        """
        config = {
            # === 시뮬레이션 기본 설정 ===
            'neuron_dt_ms': 1.0,        # 뉴런 시뮬레이션 시간 간격 (밀리초) - 1ms마다 뉴런 상태 업데이트
            'plot_hist_sz': 500,        # 그래프에 표시할 데이터 포인트 수 - 500개 = 2.5초 분량 (500ms * 5업데이트간격)
            
            # === SA 뉴런 (압력 감지) 파라미터 ===
            # Izhikevich 뉴런 모델의 수학적 파라미터들
            'sa_neuron': {
                'a': 0.05,              # 회복변수(u)의 회복 속도 - 반응속도 향상을 위해 0.03->0.05로 증가
                'b': 0.25,              # 막전위(v)와 회복변수(u) 간의 결합 강도 - 뉴런의 민감도 조절
                'c': -65.0,             # 스파이크 후 리셋 전압 (mV) - 스파이크 후 막전위가 이 값으로 리셋
                'd': 6.0,               # 스파이크 후 회복변수(u) 증가량 - 스파이크 후 일시적 비활성화 정도
                'v_init': -70.0,        # 초기 막전위 (mV) - 뉴런의 휴지 전위
                'init_a': 0.05,         # SA 뉴런의 초기 a값 (적응을 위해 동적으로 변경됨)
            },
            
            # === RA 움직임 뉴런 (움직임/진동 감지) 파라미터 ===
            'ra_neuron': {
                'base_a': 0.4,         # 기본 a값 - 반응속도 향상을 위해 0.3->0.4로 증가
                'base_b': 0.25,         # 기본 b값 - 막전위 민감도
                'base_c': -65.0,        # 스파이크 후 리셋 전압 (mV)
                'base_d': 1.5,          # 스파이크 후 회복변수 증가량 - SA보다 작아서 빠른 반복 스파이크 가능
                'v_init': -65.0,        # 초기 막전위 (mV) - SA보다 높아서 더 민감
            },
            
            # === RA 클릭 뉴런 (클릭 순간 감지) 파라미터 ===
            'ra_click_neuron': {
                'a': 0.3,               # 매우 빠른 회복 - 반응속도 향상을 위해 0.2->0.3으로 증가
                'b': 0.25,              # 막전위 민감도
                'c': -65.0,             # 스파이크 후 리셋 전압 (mV)
                'd': 6.0,               # 스파이크 후 회복변수 증가량
                'v_init': -65.0,        # 초기 막전위 (mV)
            },
            
            # === 입력 전류 설정 (마우스 → 뉴런 변환) ===
            'input_current': {
                'click_mag': 12.0,              # 마우스 클릭 시 SA 뉴런에 가해지는 기본 전류 강도
                'ra_click_scl_chg': 25.0,       # RA 클릭 뉴런 전류 스케일링 - 클릭 변화량에 곱해지는 계수
                'RA_CLICK_SUSTAIN_DURATION': 3, # RA 클릭 뉴런 자극 지속 프레임 수 (3프레임 = 3ms)
                'ra_motion_scl_spd_dev': 0.02,  # RA 움직임 뉴런 전류 스케일링 - 마우스 속도*거칠기에 곱해지는 계수
                'ra_min_spd_for_input': 1.0,    # RA 움직임 뉴런 활성화 최소 마우스 속도 (픽셀/ms)
                'ra_click_clip_min': -40.0,     # RA 클릭 뉴런 입력 전류 최소값 (클리핑)
                'ra_click_clip_max': 40.0,      # RA 클릭 뉴런 입력 전류 최대값 (클리핑)
                'ra_motion_clip_min': -30.0,    # RA 움직임 뉴런 입력 전류 최소값 (클리핑)
                'ra_motion_clip_max': 30.0,     # RA 움직임 뉴런 입력 전류 최대값 (클리핑)
            },
            
            # === 사운드 설정 (뉴런 → 오디오 변환) ===
            'sound': {
                # SA 뉴런 사운드 (압력 피드백)
                'sa_hz': 25,                    # SA 뉴런 기본 주파수 (Hz) - 더 낮은 주파수로 부드러운 압력감
                'sa_ms': 120,                   # SA 뉴런 사운드 지속시간 (ms) - 길게 지속되는 압력감
                'sa_amp': 0.6,                  # SA 뉴런 사운드 진폭 (0.25→0.6으로 대폭 증가)
                'sa_sound_volume': 1.0,         # SA 뉴런 최종 볼륨 (0.9→1.0으로 최대)
                
                # RA 움직임 뉴런 사운드 (움직임 피드백)
                'ra_motion_base_hz': 35,        # RA 움직임 뉴런 기본 주파수 (45->35Hz로 낮춤)
                'ra_motion_ms': 90,             # RA 움직임 뉴런 사운드 지속시간 (100->90ms로 약간 단축)
                'ra_motion_base_amp': 0.8,      # RA 움직임 뉴런 기본 진폭 (0.6→0.8로 대폭 증가)
                'ra_motion_vol_min_spd': 100.0, # RA 움직임 뉴런 최소 볼륨 적용 마우스 속도
                'ra_motion_vol_max_spd': 5000.0,# RA 움직임 뉴런 최대 볼륨 적용 마우스 속도
                'ra_motion_min_vol_scl': 0.7,   # RA 움직임 뉴런 최소 볼륨 스케일 (0.5→0.7로 증가)
                'ra_motion_max_vol_scl': 1.0,   # RA 움직임 뉴런 최대 볼륨 스케일 (1.0 유지)
                
                # RA 클릭 뉴런 사운드 (클릭 순간 피드백)
                'ra_click_hz': 50,              # RA 클릭 뉴런 주파수 (60->50Hz로 낮춤)
                'ra_click_ms': 70,              # RA 클릭 뉴런 사운드 지속시간 (80->70ms로 단축)
                'ra_click_amp': 0.9,            # RA 클릭 뉴런 진폭 (0.7→0.9로 증가)
                'ra_click_volume': 1.0,         # RA 클릭 뉴런 최종 볼륨 (0.9→1.0으로 최대)
            },
            
            # === 마우스 입력 설정 ===
            'mouse': {
                'max_spd_clamp': 100000.0,      # 마우스 속도 최대 제한값 (픽셀/초) - 너무 빠른 움직임 제한
                'm_stop_thresh': 0.02,          # 마우스 정지 감지 임계값 (초) - 이 시간 이상 움직임 없으면 정지로 판단
            },
            
            # === 그래프 표시 설정 ===
            'plot': {
                'update_interval': 8,           # 그래프 업데이트 간격 (프레임) - 5→8로 늘려서 성능 향상
            },
            
            # === 재질별 설정 (키보드 1-7로 선택) ===
            'materials': {
                # 각 재질마다 r(거칠기), f(주파수계수), type(파형타입), 특성파라미터를 정의
                'Glass': {          # 유리 (키보드 1) - 진짜 유리처럼 맑고 깨끗하게
                    'r': 0.1,           # 거칠기 대폭 감소 (0.3→0.1) - 거의 마찰이 없는 매끄러운 유리 표면
                    'f': 1.8,           # 주파수 계수 대폭 증가 (1.4→1.8) - 훨씬 맑고 높은 유리 소리
                    'type': 'glass',    # 파형 타입 - 유리 특화 파형 사용
                    'brightness': 4.0   # 유리 특성 최대 강화 (3.2→4.0) - 매우 맑고 투명한 소리
                },
                'Metal': {          # 메탈 (키보드 2) - 금속 특성 강화
                    'r': 1.2,           # 거칠기 증가 (1.0→1.2) - 더 거친 금속 질감
                    'f': 1.0,           # 주파수 계수 조정 (1.1→1.0) - 더 중후한 금속음
                    'type': 'metal',    # 파형 타입 - 메탈 특화 파형 사용
                    'resonance': 2.2    # 메탈 특성 강화 (1.8→2.2) - 더 강한 울림과 공명
                },
                'Wood': {           # 나무 (키보드 3) - 따뜻한 목재 특성 강화
                    'r': 0.9,           # 거칠기 증가 (0.8→0.9) - 목재의 자연스러운 질감
                    'f': 0.8,           # 주파수 계수 감소 (0.9→0.8) - 더 낮고 따뜻한 소리
                    'type': 'wood',     # 파형 타입 - 나무 특화 파형 사용
                    'warmth': 1.5       # 나무 특성 강화 (1.2→1.5) - 더 따뜻하고 부드러운 느낌
                },
                'Plastic': {        # 플라스틱 (키보드 4) - 인공적 특성 강화
                    'r': 0.3,           # 거칠기 감소 (0.4→0.3) - 더 매끄러운 플라스틱 표면
                    'f': 1.1,           # 주파수 계수 증가 (1.0→1.1) - 약간 높은 인공적 소리
                    'type': 'plastic',  # 파형 타입 - 플라스틱 특화 파형 사용
                    'hardness': 1.4     # 플라스틱 특성 강화 (1.1→1.4) - 더 단단하고 인공적인 느낌
                },
                'Fabric': {         # 직물 (키보드 5) - 부드러운 섬유 특성 강화
                    'r': 0.1,           # 거칠기 감소 (0.2→0.1) - 매우 부드러운 직물 표면
                    'f': 0.6,           # 주파수 계수 감소 (0.7→0.6) - 더 낮고 부드러운 소리
                    'type': 'fabric',   # 파형 타입 - 직물 특화 파형 사용
                    'softness': 2.0     # 직물 특성 강화 (1.5→2.0) - 극도로 부드러운 느낌
                },
                'Ceramic': {        # 세라믹 (키보드 6) - 딱딱하고 깨지기 쉬운 특성 강화
                    'r': 0.7,           # 거칠기 증가 (0.6→0.7) - 세라믹의 특별한 질감
                    'f': 1.3,           # 주파수 계수 증가 (1.2→1.3) - 더 높고 맑은 세라믹 소리
                    'type': 'ceramic',  # 파형 타입 - 세라믹 특화 파형 사용
                    'brittleness': 1.8  # 세라믹 특성 강화 (1.4→1.8) - 더 취성적이고 날카로운 느낌
                },
                'Rubber': {         # 고무 (키보드 7) - 탄성과 점성 특성 강화
                    'r': 0.4,           # 거칠기 증가 (0.3→0.4) - 고무의 독특한 질감
                    'f': 0.7,           # 주파수 계수 감소 (0.8→0.7) - 더 낮고 둔탁한 고무 소리
                    'type': 'rubber',   # 파형 타입 - 고무 특화 파형 사용
                    'elasticity': 1.6   # 고무 특성 강화 (1.3→1.6) - 더 탄성적이고 부드러운 느낌
                }
            }
        }
        
        self._validate_config(config)
        return config

    def _validate_config(self, config):
        """새로운 3개 뉴런 설정 구조 검증"""
        assert config['neuron_dt_ms'] > 0, "neuron_dt_ms must be positive"
        assert config['plot_hist_sz'] > 0, "plot_hist_sz must be positive"
        
        # SA 뉴런 파라미터 검증
        sa_cfg = config['sa_neuron']
        assert 'a' in sa_cfg and 'b' in sa_cfg and 'c' in sa_cfg and 'd' in sa_cfg, "SA neuron missing parameters"
        
        # RA 움직임 뉴런 파라미터 검증
        ra_cfg = config['ra_neuron']
        assert 'base_a' in ra_cfg and 'base_b' in ra_cfg and 'base_c' in ra_cfg and 'base_d' in ra_cfg, "RA motion neuron missing parameters"
        
        # RA 클릭 뉴런 파라미터 검증  
        ra_click_cfg = config['ra_click_neuron']
        assert 'a' in ra_click_cfg and 'b' in ra_click_cfg and 'c' in ra_click_cfg and 'd' in ra_click_cfg, "RA click neuron missing parameters"
        
        # 사운드 설정 검증
        sound_cfg = config['sound']
        assert 0 < sound_cfg['sa_hz'] < 22050, "sa_hz must be in valid audio range"
        assert 0 < sound_cfg['ra_motion_base_hz'] < 22050, "ra_motion_base_hz must be in valid audio range"
        assert 0 < sound_cfg['ra_click_hz'] < 22050, "ra_click_hz must be in valid audio range"
        assert 0 <= sound_cfg['sa_sound_volume'] <= 1.0, "sa_sound_volume must be 0-1"
        assert 0 <= sound_cfg['ra_click_volume'] <= 1.0, "ra_click_volume must be 0-1"
        
        # 재질 설정 검증
        for mat_name, mat_props in config['materials'].items():
            assert 'r' in mat_props and 'f' in mat_props, f"Material {mat_name} missing properties"
            assert mat_props['r'] > 0, f"Material {mat_name} roughness must be positive"
            assert mat_props['f'] > 0, f"Material {mat_name} frequency factor must be positive"
            
            # 재질 타입이 있는 경우 유효성 검증
            if 'type' in mat_props:
                valid_types = ['glass', 'metal', 'wood', 'plastic', 'fabric', 'ceramic', 'rubber']
                assert mat_props['type'] in valid_types, f"Material {mat_name} has invalid type: {mat_props['type']}"
        
        print("Configuration validated successfully!")

if __name__=='__main__': 
    app=QApplication(sys.argv);w=TestWindow();w.show();sys.exit(app.exec()) 
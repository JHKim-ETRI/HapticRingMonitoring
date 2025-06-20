'''
Haptic System Coordinator
햅틱 시스템 전체 코디네이터

역할:
- SpikeEncoder, HapticRenderer, AudioPlayer 조합 관리
- 스파이크 발생 시 사운드 재생 처리  
- 재질별 사운드 관리
- 연속 사운드 볼륨 제어
'''

import time
import numpy as np
from collections import deque
from neuron.spike_encoder import SpikeEncoder
from audio.haptic_renderer import HapticRenderer
from audio.audio_player import AudioPlayer

class HapticSystem:
    """
    햅틱 피드백 시스템의 핵심 로직을 담당하는 클래스
    
    기능:
    1. 스파이크 생성 (SpikeEncoder)
    2. 스파이크 → 사운드 변환 (HapticRenderer)
    3. 사운드 재생 (AudioPlayer)
    4. 재질별 사운드 관리
    5. 연속 사운드 볼륨 제어
    """
    
    def __init__(self, config):
        """햅틱 시스템 초기화"""
        self.config = config
        
        # === 핵심 컴포넌트 초기화 ===
        self.audio_player = AudioPlayer()
        self.haptic_renderer = HapticRenderer()
        self.spike_encoder = SpikeEncoder(
            sa_params=config['sa_neuron'],
            ra_params=config['ra_neuron'],
            ra_click_params=config['ra_click_neuron'],
            neuron_dt_ms=config['neuron_dt_ms'],
            input_config=config['input_current']
        )
        
        # === 재질 관리 ===
        self.materials = config['materials']
        self.material_keys = list(self.materials.keys())
        self.current_material_key = self.material_keys[0]  # 기본: Glass
        self.current_roughness = self.materials[self.current_material_key]['r']
        
        # === 사운드 캐시 ===
        self.sound_cache = {}
        self._init_all_sounds()
        
        # === 연속 사운드 볼륨 제어 ===
        self.spike_window_duration_sec = 0.025  # 25ms 윈도우
        self.ra_motion_spike_timestamps = deque()
        self.current_spike_rate = 0.0
        self.target_volume = 0.0
        self.current_volume = 0.0
        self.volume_smooth_factor = 0.4
        self.volume_fast_decay_factor = 0.8
        self.spike_rate_update_interval = 2
        self.spike_rate_update_counter = 0
        
        # === 마우스 상태 ===
        self.mouse_pressed = False
        self.last_mouse_time = time.perf_counter()
        
        # 연속 사운드 시작
        if hasattr(self, 'ra_motion_loop_sound'):
            self.audio_player.start_continuous_sound(
                self.ra_motion_loop_sound, channel_id=1, initial_volume=0.0
            )
    
    def _init_all_sounds(self):
        """모든 재질의 사운드들을 미리 생성하여 캐시"""
        snd_cfg = self.config['sound']
        
        # SA 뉴런 사운드 (진동감 있는 배경음으로 변경)
        self.sa_sound = self.haptic_renderer.create_sa_background_sound(
            snd_cfg['sa_hz'], snd_cfg['sa_ms'], snd_cfg['sa_amp'], fade_out_ms=20
        )
        
        # 각 재질별로 RA Motion, RA Click, Loop 사운드 생성
        for mat_key, mat_props in self.materials.items():
            self._create_material_sounds(mat_key, mat_props, snd_cfg)
        
        # 현재 재질의 사운드들 설정
        self._update_current_material_sounds()
    
    def _create_material_sounds(self, mat_key, mat_props, snd_cfg):
        """특정 재질의 모든 사운드 생성"""
        # RA Motion 사운드
        ra_motion_hz = int(snd_cfg['ra_motion_base_hz'] * mat_props['f'])
        ra_motion_cache_key = f"ra_motion_{mat_key}_{ra_motion_hz}"
        
        if 'type' in mat_props:
            material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
            self.sound_cache[ra_motion_cache_key] = self.haptic_renderer.create_material_sound(
                mat_props['type'], ra_motion_hz, snd_cfg['ra_motion_ms'], 
                snd_cfg['ra_motion_base_amp'], fade_out_ms=10, **material_params
            )
        else:
            self.sound_cache[ra_motion_cache_key] = self.haptic_renderer.create_sound_object(
                ra_motion_hz, snd_cfg['ra_motion_ms'], snd_cfg['ra_motion_base_amp'], fade_out_ms=10
            )
        
        # RA Click 사운드  
        ra_click_hz = int(snd_cfg['ra_click_hz'] * mat_props['f'])
        ra_click_cache_key = f"ra_click_{mat_key}_{ra_click_hz}"
        
        # RA 클릭은 저주파 딸깍 사운드로 변경 (재질 무관)
        click_amp = snd_cfg['ra_click_amp']  # 볼륨 증가 제거
        self.sound_cache[ra_click_cache_key] = self.haptic_renderer.create_ra_click_sound(
            ra_click_hz, snd_cfg['ra_click_ms'], click_amp, fade_out_ms=5
        )
        
        # RA Motion Loop 사운드 (연속 재생용)
        loop_duration_ms = 2000
        ra_loop_cache_key = f"ra_motion_loop_{mat_key}_{ra_motion_hz}"
        
        if 'type' in mat_props:
            material_params = {k: v for k, v in mat_props.items() if k not in ['r', 'f', 'type']}
            self.sound_cache[ra_loop_cache_key] = self.haptic_renderer.create_material_sound(
                mat_props['type'], ra_motion_hz, loop_duration_ms, 
                snd_cfg['ra_motion_base_amp'], fade_out_ms=0, **material_params
            )
        else:
            self.sound_cache[ra_loop_cache_key] = self.haptic_renderer.create_sound_object(
                ra_motion_hz, loop_duration_ms, snd_cfg['ra_motion_base_amp'], fade_out_ms=0
            )
        
        print(f"🎵 Created {mat_key} sounds: Motion({ra_motion_hz}Hz), Click({ra_click_hz}Hz)")
    
    def _update_current_material_sounds(self):
        """현재 재질의 사운드들을 설정"""
        mat_props = self.materials[self.current_material_key]
        snd_cfg = self.config['sound']
        
        # 현재 재질의 주파수 계산
        ra_motion_hz = int(snd_cfg['ra_motion_base_hz'] * mat_props['f'])
        ra_click_hz = int(snd_cfg['ra_click_hz'] * mat_props['f'])
        
        # 캐시에서 사운드 가져오기
        self.ra_motion_sound = self.sound_cache[f"ra_motion_{self.current_material_key}_{ra_motion_hz}"]
        self.ra_click_sound = self.sound_cache[f"ra_click_{self.current_material_key}_{ra_click_hz}"]
        self.ra_motion_loop_sound = self.sound_cache[f"ra_motion_loop_{self.current_material_key}_{ra_motion_hz}"]
    
    def change_material(self, material_index):
        """재질 변경 (0-6 인덱스)"""
        if 0 <= material_index < len(self.material_keys):
            old_material = self.current_material_key
            self.current_material_key = self.material_keys[material_index]
            self.current_roughness = self.materials[self.current_material_key]['r']
            
            # 기존 연속 사운드 중지
            if self.audio_player.is_continuous_playing(1):
                self.audio_player.stop_continuous_sound(1)
            
            # 새로운 재질의 사운드들 설정
            self._update_current_material_sounds()
            
            # 새로운 연속 사운드 시작
            self.audio_player.start_continuous_sound(
                self.ra_motion_loop_sound, channel_id=1, initial_volume=self.current_volume
            )
            
            print(f"🔄 Material changed: {old_material} → {self.current_material_key}")
            return True
        return False
    
    def update_mouse_state(self, pressed, speed, avg_speed):
        """마우스 상태 업데이트"""
        self.mouse_pressed = pressed
        # SpikeEncoder에 마우스 상태 전달 (기존 로직 유지)
    
    def step(self, mouse_speed, avg_mouse_speed):
        """
        햅틱 시스템 한 스텝 실행
        
        Returns:
        - tuple: (sa_fired, ra_motion_fired, ra_click_fired, sa_vu, ra_motion_vu, ra_click_vu)
        """
        current_time = time.perf_counter()
        
        # === 1. 스파이크 생성 ===
        sa_fired, ra_motion_fired, ra_click_fired, sa_vu, ra_motion_vu, ra_click_vu = self.spike_encoder.step(
            mouse_speed=mouse_speed,
            avg_mouse_speed=avg_mouse_speed,
            material_roughness=self.current_roughness,
            mouse_pressed=self.mouse_pressed
        )
        
        # === 2. 스파이크 → 사운드 재생 ===
        if sa_fired:
            volume = self.config['sound']['sa_sound_volume']
            self.audio_player.play_sound(self.sa_sound, channel_id=0, volume=volume)
            print(f"🔴 SA SPIKE! Volume: {volume:.2f}")
        
        if ra_click_fired:
            volume = self.config['sound']['ra_click_volume']
            self.audio_player.play_sound(self.ra_click_sound, channel_id=2, volume=volume)
            print(f"🟡 RA CLICK SPIKE! Volume: {volume:.2f}")
        
        # === 3. RA Motion 연속 사운드 볼륨 제어 ===
        self._update_ra_motion_volume(ra_motion_fired, current_time)
        
        return sa_fired, ra_motion_fired, ra_click_fired, sa_vu, ra_motion_vu, ra_click_vu
    
    def _update_ra_motion_volume(self, ra_motion_fired, current_time):
        """RA Motion 연속 사운드 볼륨 업데이트"""
        # 스파이크 히스토리 기록
        self.ra_motion_spike_timestamps.append((current_time, ra_motion_fired))
        
        # 스파이크 발생률 계산 (주기적으로)
        self.spike_rate_update_counter += 1
        if self.spike_rate_update_counter >= self.spike_rate_update_interval:
            self.current_spike_rate = self._calculate_spike_rate(current_time)
            self.spike_rate_update_counter = 0
        
        # 목표 볼륨 계산
        if self.mouse_pressed and self.current_spike_rate > 0:
            self.target_volume = self._spike_rate_to_volume(self.current_spike_rate)
        else:
            self.target_volume = 0.0
        
        # 볼륨 스무딩 (증가 시 부드럽게, 감소 시 빠르게)
        if self.target_volume > self.current_volume:
            smooth_factor = self.volume_smooth_factor
        else:
            smooth_factor = self.volume_fast_decay_factor
        
        self.current_volume += (self.target_volume - self.current_volume) * smooth_factor
        
        # 작은 차이는 목표값으로 스냅
        if abs(self.current_volume - self.target_volume) < 0.005:
            self.current_volume = self.target_volume
        
        # 연속 사운드 볼륨 설정
        if self.audio_player.is_continuous_playing(1):
            self.audio_player.set_continuous_volume(1, self.current_volume)
        
        # 볼륨 업데이트
        self.audio_player.update_volumes()
        
        # 볼륨 변화 로깅 (큰 변화만)
        if hasattr(self, 'last_logged_volume'):
            if abs(self.current_volume - self.last_logged_volume) > 0.05:
                print(f"🔵 RA MOTION Volume: {self.current_volume:.2f} (target: {self.target_volume:.2f}, rate: {self.current_spike_rate:.1f}Hz)")
                self.last_logged_volume = self.current_volume
        else:
            self.last_logged_volume = self.current_volume
    
    def _calculate_spike_rate(self, current_time):
        """스파이크 발생률 계산 (spikes/second)"""
        cutoff_time = current_time - self.spike_window_duration_sec
        
        # 오래된 기록 제거
        while self.ra_motion_spike_timestamps and self.ra_motion_spike_timestamps[0][0] < cutoff_time:
            self.ra_motion_spike_timestamps.popleft()
        
        # 윈도우 내 스파이크 개수
        spike_count = sum(1 for timestamp, spike_occurred in self.ra_motion_spike_timestamps if spike_occurred)
        
        # 실제 윈도우 지속시간
        if len(self.ra_motion_spike_timestamps) > 0:
            oldest_time = self.ra_motion_spike_timestamps[0][0]
            actual_duration = current_time - oldest_time
            effective_duration = max(min(actual_duration, self.spike_window_duration_sec), 0.005)
        else:
            effective_duration = self.spike_window_duration_sec
        
        return spike_count / effective_duration if effective_duration > 0 else 0.0
    
    def _spike_rate_to_volume(self, spike_rate):
        """스파이크 발생률을 볼륨으로 변환"""
        snd_cfg = self.config['sound']
        
        min_spike_rate = 20.0
        max_spike_rate = 120.0
        min_volume = snd_cfg['ra_motion_min_vol_scl']
        max_volume = snd_cfg['ra_motion_max_vol_scl']
        
        if spike_rate <= 0:
            return 0.0
        elif spike_rate <= min_spike_rate:
            return min_volume
        elif spike_rate >= max_spike_rate:
            return max_volume
        else:
            volume_range = max_volume - min_volume
            rate_range = max_spike_rate - min_spike_rate
            volume = min_volume + ((spike_rate - min_spike_rate) / rate_range) * volume_range
            return np.clip(volume, 0.0, 1.0)
    
    def mouse_press(self, click_magnitude=None):
        """마우스 클릭 처리"""
        self.mouse_pressed = True
        if click_magnitude is None:
            click_magnitude = self.config['input_current']['click_mag']
        self.spike_encoder.update_sa_input(click_magnitude)
        
        # RA 클릭 사운드 즉시 재생 (hover 시 들리도록)
        volume = self.config['sound']['ra_click_volume']
        self.audio_player.play_sound(self.ra_click_sound, channel_id=2, volume=volume)
        print(f"🟡 MANUAL RA CLICK! Volume: {volume:.2f}")

    def mouse_release(self):
        """마우스 릴리즈 처리"""
        self.mouse_pressed = False
        self.spike_encoder.update_sa_input(0.0)
        
        # 즉시 볼륨 0으로
        self.target_volume = 0.0
        self.current_volume = 0.0
        if self.audio_player.is_continuous_playing(1):
            self.audio_player.set_continuous_volume(1, 0.0)
    
    def cleanup(self):
        """시스템 정리"""
        if hasattr(self, 'audio_player'):
            # 모든 연속 사운드 중지
            if hasattr(self.audio_player, 'continuous_channels'):
                for channel_id in list(self.audio_player.continuous_channels.keys()):
                    self.audio_player.stop_continuous_sound(channel_id)
            self.audio_player.quit()
        print("🧹 Haptic system cleaned up!") 
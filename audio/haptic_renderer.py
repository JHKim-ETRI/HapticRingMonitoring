'''
Haptic Renderer for generating sound objects from parameters
햅틱 렌더러 - 뉴런 스파이크 신호를 사운드 객체로 변환하는 모듈
주파수, 지속시간, 진폭 파라미터를 받아서 pygame.mixer.Sound 객체를 생성
'''
import numpy as np
import pygame

class HapticRenderer:
    """
    햅틱 피드백을 위한 사운드 렌더링 클래스
    
    뉴런의 스파이크 이벤트를 사운드로 변환하여 촉각적 피드백을 제공합니다.
    다양한 타입의 사운드 (단일 주파수, 주파수 스위프)를 생성할 수 있으며,
    각 뉴런 타입(SA, RA)에 맞는 특성의 사운드를 생성합니다.
    
    Data Flow:
    뉴런 스파이크 → 파라미터 (hz, ms, amp) → HapticRenderer → pygame.mixer.Sound
    """
    
    def __init__(self, sample_rate=44100):
        """
        햅틱 렌더러 초기화
        
        Parameters:
        - sample_rate: 오디오 샘플링 주파수 (Hz)
        """
        self.sample_rate = sample_rate
        # pygame mixer 초기화 상태 확인
        if pygame.mixer.get_init() is None:
            print("Warning: Pygame mixer is not initialized. HapticRenderer might rely on a default sample rate.")
        else:
            pass 

    def create_sound_buffer(self, hz, ms, amp, fade_out_ms=10):
        """
        주어진 파라미터로 사운드 버퍼(원시 오디오 데이터)를 생성
        
        Parameters:
        - hz: 주파수 (Hz) - SA뉴런은 낮은 주파수(50Hz), RA뉴런은 높은 주파수(80Hz+)
        - ms: 지속시간 (milliseconds) - SA는 길게(120ms), RA는 짧게(100ms)
        - amp: 진폭 (0.0~1.0) - 소리 크기 결정
        - fade_out_ms: 페이드아웃 시간 (ms) - 갑작스런 소리 끊김 방지
        
        Returns:
        - numpy.ndarray: 16비트 정수 형태의 오디오 데이터
        """
        # 샘플 수 계산: 지속시간 × 샘플레이트
        n_s = int(self.sample_rate * (ms / 1000.0))
        
        # 시간 축 생성 (0부터 지속시간까지)
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 사인파 생성: y = amp * sin(2π * freq * time)
        wave_data = amp * np.sin(2 * np.pi * hz * t)
        
        # 페이드아웃 효과 적용 (끝부분에서 점진적으로 볼륨 감소)
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            # 끝부분을 1에서 0으로 선형 감소
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        # 16비트 정수로 변환 (-32768 ~ 32767 범위)
        return (wave_data * 32767).astype(np.int16)

    def create_sound_object(self, hz, ms, amp, fade_out_ms=10):
        """
        pygame.mixer.Sound 객체를 생성
        
        Parameters:
        - hz: 주파수 (Hz)
        - ms: 지속시간 (ms) 
        - amp: 진폭 (0.0~1.0)
        - fade_out_ms: 페이드아웃 시간 (ms)
        
        Returns:
        - pygame.mixer.Sound: AudioPlayer에서 재생할 수 있는 사운드 객체
        
        Usage in main.py:
        SA뉴런 스파이크 시 → sa_sound = create_sound_object(50, 120, 0.15)
        RA뉴런 스파이크 시 → ra_sound = create_sound_object(80, 100, 0.6)
        """
        sound_buffer = self.create_sound_buffer(hz, ms, amp, fade_out_ms)
        
        # 빈 버퍼 처리 (에러 방지)
        if sound_buffer.size == 0:
            print(f"Warning: Created empty sound buffer for hz={hz}, ms={ms}, amp={amp}")
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        
        return pygame.mixer.Sound(buffer=sound_buffer)

    def create_sweep_sound(self, start_hz, end_hz, ms, amp, fade_out_ms=10):
        """
        주파수 스위프 사운드 생성 (시작 주파수에서 끝 주파수로 변화)
        
        이 기능은 현재 main.py에서 사용되지 않지만, 향후 더 복잡한 햅틱 효과를 위해 준비된 기능입니다.
        예: 마우스 속도에 따라 주파수가 변하는 효과
        
        Parameters:
        - start_hz: 시작 주파수 (Hz)
        - end_hz: 끝 주파수 (Hz) 
        - ms: 지속시간 (ms)
        - amp: 진폭 (0.0~1.0)
        - fade_out_ms: 페이드아웃 시간 (ms)
        
        Returns:
        - pygame.mixer.Sound: 주파수가 시간에 따라 변하는 사운드 객체
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 선형적으로 변화하는 주파수 배열
        frequency_sweep = np.linspace(start_hz, end_hz, n_s)
        
        # 적분하여 위상 계산 (frequency sweep를 위해)
        # 각 시점에서의 순간 주파수를 적분하여 위상 계산
        phase = 2 * np.pi * np.cumsum(frequency_sweep) * (ms / 1000.0) / n_s
        wave_data = amp * np.sin(phase)
        
        # 페이드 아웃 적용
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        sound_buffer = (wave_data * 32767).astype(np.int16)
        if sound_buffer.size == 0:
            print(f"Warning: Created empty sweep sound buffer")
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        return pygame.mixer.Sound(buffer=sound_buffer)

    def create_material_sound(self, material_type, hz, ms, amp, fade_out_ms=10, **kwargs):
        """
        재질별 특화 파형을 가진 사운드 객체를 생성
        
        Parameters:
        - material_type: 재질 타입 ('glass', 'metal', 'wood', 'plastic', 'fabric', 'ceramic', 'rubber')
        - hz: 기본 주파수 (Hz)
        - ms: 지속시간 (ms)
        - amp: 진폭 (0.0~1.0)
        - fade_out_ms: 페이드아웃 시간 (ms)
        - **kwargs: 재질별 추가 파라미터
        
        Returns:
        - pygame.mixer.Sound: 재질 특성이 반영된 사운드 객체
        """
        if material_type == 'glass':
            sound_buffer = self._create_glass_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'metal':
            sound_buffer = self._create_metal_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'wood':
            sound_buffer = self._create_wood_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'plastic':
            sound_buffer = self._create_plastic_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'fabric':
            sound_buffer = self._create_fabric_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'ceramic':
            sound_buffer = self._create_ceramic_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        elif material_type == 'rubber':
            sound_buffer = self._create_rubber_waveform(hz, ms, amp, fade_out_ms, **kwargs)
        else:
            # 기본 사인파 사용
            sound_buffer = self.create_sound_buffer(hz, ms, amp, fade_out_ms)
        
        if sound_buffer.size == 0:
            print(f"Warning: Created empty {material_type} sound buffer")
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        
        return pygame.mixer.Sound(buffer=sound_buffer)

    def _create_glass_waveform(self, hz, ms, amp, fade_out_ms, brightness=2.0):
        """
        유리 재질 파형 생성 - 맑고 날카로우며 배음이 많은 소리
        특징: 높은 배음, 빠른 어택, 긴 서스테인, 날카로운 특성
        
        개선: 지직거림 완전 제거, 매우 부드러운 질감
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 기본파 + 매우 부드러운 배음들 (지직거림 완전 제거)
        fundamental = amp * 0.85 * np.sin(2 * np.pi * hz * t)
        harmonic2 = amp * 0.08 * brightness * 0.2 * np.sin(2 * np.pi * hz * 2 * t)
        harmonic3 = amp * 0.03 * brightness * 0.1 * np.sin(2 * np.pi * hz * 3 * t)
        
        # 극미량의 매우 부드러운 고주파 질감 (유리 특성)
        subtle_texture = amp * 0.001 * np.sin(2 * np.pi * hz * 8 * t) * (1 + 0.1 * np.sin(2 * np.pi * 2 * t))
        
        # 모든 성분을 부드럽게 스무딩
        wave_data = fundamental + harmonic2 + harmonic3 + subtle_texture
        
        # 강력한 스무딩으로 완전히 부드럽게
        if n_s > 20:
            smooth_kernel = np.ones(15) / 15
            wave_data = np.convolve(wave_data, smooth_kernel, mode='same')
        
        # 빠른 어택, 긴 서스테인을 위한 envelope
        attack_samples = int(0.001 * self.sample_rate)  # 1ms 빠른 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (wave_data * 32767).astype(np.int16)

    def _create_metal_waveform(self, hz, ms, amp, fade_out_ms, resonance=1.5):
        """
        메탈 재질 파형 생성 - 날카롭고 밝으며 잔향이 있는 소리
        특징: 강한 기본파, 날카로운 배음, 메탈릭한 잔향
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 강한 기본파
        fundamental = amp * 0.7 * np.sin(2 * np.pi * hz * t)
        
        # 날카로운 메탈릭 배음들 (더 강하게)
        harmonic2 = amp * 0.25 * resonance * np.sin(2 * np.pi * hz * 2 * t)
        harmonic3 = amp * 0.15 * resonance * np.sin(2 * np.pi * hz * 3 * t)
        harmonic5 = amp * 0.08 * resonance * np.sin(2 * np.pi * hz * 5 * t)
        
        # 메탈 특유의 고주파 울림
        metal_ring = amp * 0.05 * resonance * np.sin(2 * np.pi * hz * 7 * t) * np.exp(-1.5 * t)
        
        # 메탈 충돌 시 특유의 진동 효과
        metal_vibration = amp * 0.03 * np.sin(2 * np.pi * hz * 1.3 * t) * (1 + 0.3 * np.sin(2 * np.pi * 4 * t))
        
        wave_data = fundamental + harmonic2 + harmonic3 + harmonic5 + metal_ring + metal_vibration
        
        # 최소한의 스무딩 (날카로운 특성 유지)
        if n_s > 10:
            smooth_kernel = np.ones(5) / 5  # 매우 적은 스무딩
            wave_data = np.convolve(wave_data, smooth_kernel, mode='same')
        
        # 빠른 어택
        attack_samples = int(0.001 * self.sample_rate)
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 긴 잔향
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_wood_waveform(self, hz, ms, amp, fade_out_ms, warmth=1.0):
        """
        나무 재질 파형 생성 - 따뜻하고 자연스러운 거칠기가 있는 소리
        특징: 자연스러운 노이즈, 나무 특유의 거칠기, 따뜻한 배음
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 따뜻한 기본파
        fundamental = amp * 0.65 * np.sin(2 * np.pi * hz * t)
        
        # 따뜻한 배음들 (더 강하게)
        harmonic2 = amp * 0.15 * warmth * np.sin(2 * np.pi * hz * 2 * t)
        harmonic3 = amp * 0.08 * warmth * np.sin(2 * np.pi * hz * 3 * t)
        
        # 나무 특유의 자연스러운 거칠기 (노이즈 추가)
        wood_roughness = amp * 0.08 * np.random.normal(0, 1, n_s)
        # 저주파 필터로 자연스러운 거칠기 만들기
        for i in range(1, len(wood_roughness)):
            wood_roughness[i] = 0.6 * wood_roughness[i] + 0.4 * wood_roughness[i-1]
        
        # 나무 결 따라 흐르는 질감 (주기적 변조)
        wood_grain = amp * 0.04 * np.sin(2 * np.pi * hz * 0.3 * t) * (1 + 0.5 * np.sin(2 * np.pi * 0.8 * t))
        
        # 나무 타격 시 특유의 펄스 효과
        wood_pulse = amp * 0.02 * np.sin(2 * np.pi * hz * 8 * t) * np.exp(-3 * t)
        
        wave_data = fundamental + harmonic2 + harmonic3 + wood_roughness + wood_grain + wood_pulse
        
        # 적당한 스무딩 (너무 부드럽지 않게 - 거칠기 유지)
        if n_s > 15:
            smooth_kernel = np.ones(8) / 8  # 더 적은 스무딩
            wave_data = np.convolve(wave_data, smooth_kernel, mode='same')
        
        # 중간 속도 어택
        attack_samples = int(0.003 * self.sample_rate)
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 자연스러운 감쇠
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_plastic_waveform(self, hz, ms, amp, fade_out_ms, hardness=1.0):
        """
        플라스틱 재질 파형 생성 - 밝고 가벼우며 합성적인 소리
        특징: 깔끔한 배음, 빠른 감쇠, 인공적 느낌
        
        개선: 부드러운 플라스틱 질감
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 깔끔한 기본파
        fundamental = amp * 0.78 * np.sin(2 * np.pi * hz * t)
        
        # 플라스틱 특성의 배음들
        harmonic2 = amp * 0.09 * hardness * 0.3 * np.sin(2 * np.pi * hz * 2 * t)
        harmonic4 = amp * 0.05 * hardness * 0.2 * np.sin(2 * np.pi * hz * 4 * t)
        
        # 매우 부드러운 플라스틱 질감
        plastic_texture = amp * 0.0008 * np.sin(2 * np.pi * hz * 6 * t)
        
        wave_data = fundamental + harmonic2 + harmonic4 + plastic_texture
        
        # 스무딩
        if n_s > 15:
            smooth_kernel = np.ones(12) / 12
            wave_data = np.convolve(wave_data, smooth_kernel, mode='same')
        
        # 빠른 어택
        attack_samples = int(0.001 * self.sample_rate)
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 빠른 감쇠
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (wave_data * 32767).astype(np.int16)

    def _create_fabric_waveform(self, hz, ms, amp, fade_out_ms, softness=1.0):
        """
        직물 재질 파형 생성 - 부드럽고 노이즈가 많은 소리
        특징: 높은 노이즈 성분, 매우 부드러운 질감, 마찰음
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 매우 부드러운 기본 톤
        fundamental = amp * 0.4 * np.sin(2 * np.pi * hz * 0.8 * t)  # 더 낮은 주파수
        
        # 직물 특유의 부드러운 마찰 노이즈 (더 강하게)
        fabric_noise = amp * 0.4 * softness * np.random.normal(0, 1, n_s)
        
        # 매우 강한 저주파 필터링 (부드러운 느낌)
        for i in range(1, len(fabric_noise)):
            fabric_noise[i] = 0.2 * fabric_noise[i] + 0.8 * fabric_noise[i-1]  # 매우 부드럽게
        
        # 직물 섬유 특유의 미세한 진동
        fiber_texture = amp * 0.1 * np.sin(2 * np.pi * hz * 0.1 * t) * (1 + 0.2 * np.random.normal(0, 1, n_s))
        
        # 직물 접촉 시 특유의 스위시 사운드
        swish_effect = amp * 0.08 * np.sin(2 * np.pi * hz * 0.05 * t) * np.exp(-0.5 * t)
        
        wave_data = fundamental + fabric_noise + fiber_texture + swish_effect
        
        # 매우 부드러운 어택
        attack_samples = int(0.015 * self.sample_rate)  # 15ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 자연스러운 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_ceramic_waveform(self, hz, ms, amp, fade_out_ms, brittleness=1.5):
        """
        세라믹 재질 파형 생성 - 유리와 비슷하지만 더 둔한 소리
        특징: 중간 정도의 배음, 유리보다 덜 날카로움
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 세라믹 특유의 배음 구조
        fundamental = amp * 0.7 * np.sin(2 * np.pi * hz * t)
        harmonic2 = amp * 0.3 * brittleness * np.sin(2 * np.pi * hz * 2 * t)
        harmonic3 = amp * 0.2 * brittleness * np.sin(2 * np.pi * hz * 3 * t)
        harmonic4 = amp * 0.1 * brittleness * np.sin(2 * np.pi * hz * 4 * t)
        
        wave_data = fundamental + harmonic2 + harmonic3 + harmonic4
        
        # 중간 속도 어택
        attack_samples = int(0.002 * self.sample_rate)  # 2ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def _create_rubber_waveform(self, hz, ms, amp, fade_out_ms, elasticity=1.0):
        """
        고무 재질 파형 생성 - 부드럽고 탄성적인 소리
        특징: 낮은 주파수, 부드러운 감쇠, 탄성적 특성
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 고무의 탄성적 특성을 위한 낮은 주파수 성분
        fundamental = amp * 0.8 * np.sin(2 * np.pi * hz * 0.8 * t)  # 약간 낮은 주파수
        harmonic2 = amp * 0.2 * elasticity * np.sin(2 * np.pi * hz * 1.6 * t)
        
        # 탄성적 변조 효과
        elastic_modulation = 1 + 0.2 * np.sin(2 * np.pi * hz * 0.1 * t)
        
        wave_data = (fundamental + harmonic2) * elastic_modulation
        
        # 부드러운 어택
        attack_samples = int(0.005 * self.sample_rate)  # 5ms 어택
        if attack_samples < n_s:
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 부드러운 감쇠
        decay_envelope = np.exp(-2 * t / (ms / 1000.0))
        wave_data *= decay_envelope
        
        # 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            wave_data[n_s - fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)
        
        return (np.clip(wave_data, -1, 1) * 32767).astype(np.int16)

    def create_sa_background_sound(self, hz, ms, amp, fade_out_ms=50):
        """
        SA 뉴런용 피에조 진동 사운드 생성
        특징: 80-120Hz 중간 주파수로 피에조 미세변위자극기에서 실제 진동감을 느낄 수 있도록 설계
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 피에조 진동감을 위한 중간 주파수 (80-120Hz) - 실제 진동이 느껴지는 범위
        base_hz = max(min(hz * 1.5, 120), 80)  # 80-120Hz로 피에조 진동 최적화
        
        # 강한 기본파 (피에조 진동의 핵심)
        fundamental = amp * 0.7 * np.sin(2 * np.pi * base_hz * t)
        
        # 진동감 강화를 위한 서브하모닉
        sub_harmonic = amp * 0.2 * np.sin(2 * np.pi * base_hz * 0.8 * t)
        
        # 피에조 특성을 위한 2차 배음 (진동 질감)
        second_harmonic = amp * 0.1 * np.sin(2 * np.pi * base_hz * 2 * t)
        
        # 피에조 진동기의 자연스러운 진폭 변조 (미세한 변동)
        vibration_modulation = 1 + 0.03 * np.sin(2 * np.pi * base_hz * 0.05 * t)
        
        # 모든 성분을 합성하여 피에조 진동감 구현
        wave_data = (fundamental + sub_harmonic + second_harmonic) * vibration_modulation
        
        # 피에조 특성에 맞는 적당한 스무딩 (너무 부드럽지 않게)
        if n_s > 20:
            # 3단계 스무딩으로 적당한 질감 유지
            for i in range(3):
                kernel_size = 8 - i * 2  # 8, 6, 4
                if kernel_size > 2:
                    smooth_kernel = np.ones(kernel_size) / kernel_size
                    wave_data = np.convolve(wave_data, smooth_kernel, mode='same')
        
        # 피에조 진동기의 빠른 응답 특성 (10ms 어택)
        attack_samples = int(0.01 * self.sample_rate)
        if attack_samples < n_s:
            # 빠른 선형 어택
            wave_data[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
        # 자연스러운 페이드아웃
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            actual_fade_samples = min(fade_out_samples, n_s)
            decay_curve = np.exp(-1.2 * np.linspace(0, 1, actual_fade_samples))
            wave_data[n_s - actual_fade_samples:] *= decay_curve
        
        # 피에조 진동기의 적당한 포화 특성
        wave_data = np.tanh(wave_data * 0.9) * 0.95
        
        sound_buffer = (wave_data * 32767).astype(np.int16)
        if sound_buffer.size == 0:
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        
        return pygame.mixer.Sound(buffer=sound_buffer)

    def create_ra_click_sound(self, hz, ms, amp, fade_out_ms=5):
        """
        RA 클릭용 맥북 터치패드 스타일 깔끔한 클릭 사운드 생성
        특징: 18-25Hz 초저주파, 틱틱거림 없는 부드러운 진동감, 매우 짧고 깔끔함
        """
        n_s = int(self.sample_rate * (ms / 1000.0))
        t = np.linspace(0, ms / 1000.0, n_s, False)
        
        # 맥북 터치패드 스타일 초저주파 (18-25Hz)
        click_hz = min(max(hz * 0.3, 18), 25)  # 더 낮은 주파수로
        
        # 매우 순수한 사인파 (틱틱거림 방지)
        fundamental = amp * 0.6 * np.sin(2 * np.pi * click_hz * t)
        
        # 깊이감을 위한 극미량의 서브하모닉 (진동감 강화)
        sub_harmonic = amp * 0.1 * np.sin(2 * np.pi * click_hz * 0.5 * t)
        
        # 맥북 터치패드의 특징적인 envelope (빠른 어택, 부드러운 감쇠)
        # 지수적 감쇠 envelope 적용
        envelope = np.exp(-8 * t / (ms / 1000.0))  # 빠른 감쇠
        
        # 파형 합성 (노이즈 완전 제거)
        wave_data = (fundamental + sub_harmonic) * envelope
        
        # 맥북 스타일의 부드러운 필터링 (틱틱거림 완전 제거)
        if n_s > 10:
            # 간단한 이동평균 스무딩으로 안전하게
            kernel_size = min(8, n_s // 3)
            if kernel_size > 2:
                smooth_kernel = np.ones(kernel_size) / kernel_size
                wave_data = np.convolve(wave_data, smooth_kernel, mode='same')
        
        # 맥북 터치패드의 특징적인 순간 어택 (0.1ms)
        attack_samples = int(0.0001 * self.sample_rate)
        if attack_samples > 0 and attack_samples < n_s:
            # 매우 부드러운 어택 곡선
            attack_curve = np.linspace(0, 1, attack_samples) ** 0.5
            wave_data[:attack_samples] *= attack_curve
        
        # 자연스러운 페이드아웃 (거의 필요없음, envelope이 이미 처리)
        fade_out_samples = int(self.sample_rate * (fade_out_ms / 1000.0))
        if n_s > fade_out_samples and fade_out_ms > 0:
            actual_fade_samples = min(fade_out_samples, n_s)
            fade_curve = np.exp(-3 * np.linspace(0, 1, actual_fade_samples))
            wave_data[n_s - actual_fade_samples:] *= fade_curve
        
        # 매우 부드러운 클리핑 (맥북 터치패드의 깔끔함)
        wave_data = np.tanh(wave_data * 0.9) * 0.8
        
        sound_buffer = (wave_data * 32767).astype(np.int16)
        if sound_buffer.size == 0:
            return pygame.mixer.Sound(buffer=np.array([0], dtype=np.int16))
        
        return pygame.mixer.Sound(buffer=sound_buffer)

# 사용 예시 (테스트용)
if __name__ == '__main__':
    """
    HapticRenderer 테스트 코드
    SA뉴런과 RA뉴런에 해당하는 사운드를 생성하고 재생
    """
    pygame.init()
    if pygame.mixer.get_init() is None:
        pygame.mixer.init()

    renderer = HapticRenderer()
    player = AudioPlayer()  # AudioPlayer import 필요

    print("Creating SA sound object...")
    # SA뉴런용 사운드: 낮은 주파수(120Hz), 긴 지속시간(120ms), 작은 진폭(0.15)
    sa_sound = renderer.create_sound_object(hz=120, ms=120, amp=0.15, fade_out_ms= (120 * 0.1) if 120 > 10 else 0)

    print("Creating RA sound object...")
    # RA뉴런용 사운드: 높은 주파수(220Hz), 짧은 지속시간(60ms), 큰 진폭(0.25)  
    ra_sound = renderer.create_sound_object(hz=220, ms=60, amp=0.25, fade_out_ms= (60*0.1) if 60 > 10 else 0)

    if sa_sound:
        print("Playing SA sound...")
        player.play_sound(sa_sound, channel_id=0, volume=0.8)
        pygame.time.wait(500)

    if ra_sound:
        print("Playing RA sound...")
        player.play_sound(ra_sound, channel_id=1, volume=0.7)
        pygame.time.wait(500)

    player.quit()
    pygame.quit() 
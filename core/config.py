'''
Haptic System Configuration
햅틱 시스템 전체 설정 관리

모든 파라미터를 중앙에서 관리:
- 뉴런 모델 파라미터
- 사운드 설정
- 재질별 특성
- UI 설정
'''

def get_haptic_config():
    """
    햅틱 피드백 시스템의 모든 설정값을 반환하는 함수
    """
    config = {
        # === 시뮬레이션 기본 설정 ===
        'neuron_dt_ms': 1.0,        # 뉴런 시뮬레이션 시간 간격 (밀리초)
        'plot_hist_sz': 500,        # 그래프에 표시할 데이터 포인트 수
        
        # === SA 뉴런 (압력 감지) 파라미터 ===
        'sa_neuron': {
            'a': 0.05,              # 회복변수 회복 속도
            'b': 0.25,              # 막전위와 회복변수 결합 강도
            'c': -65.0,             # 스파이크 후 리셋 전압 (mV)
            'd': 6.0,               # 스파이크 후 회복변수 증가량
            'v_init': -70.0,        # 초기 막전위 (mV)
            'init_a': 0.05,         # 초기 a값
        },
        
        # === RA 움직임 뉴런 (움직임/진동 감지) 파라미터 ===
        'ra_neuron': {
            'base_a': 0.4,          # 기본 a값
            'base_b': 0.25,         # 기본 b값
            'base_c': -65.0,        # 스파이크 후 리셋 전압 (mV)
            'base_d': 1.5,          # 스파이크 후 회복변수 증가량
            'v_init': -65.0,        # 초기 막전위 (mV)
        },
        
        # === RA 클릭 뉴런 (클릭 순간 감지) 파라미터 ===
        'ra_click_neuron': {
            'a': 0.3,               # 매우 빠른 회복
            'b': 0.25,              # 막전위 민감도
            'c': -65.0,             # 스파이크 후 리셋 전압 (mV)
            'd': 6.0,               # 스파이크 후 회복변수 증가량
            'v_init': -65.0,        # 초기 막전위 (mV)
        },
        
        # === 입력 전류 설정 (마우스 → 뉴런 변환) ===
        'input_current': {
            'click_mag': 12.0,              # 마우스 클릭 시 SA 뉴런 전류 강도
            'ra_click_scl_chg': 100.0,       # RA 클릭 뉴런 전류 스케일링
            'RA_CLICK_SUSTAIN_DURATION': 3, # RA 클릭 뉴런 자극 지속 프레임 수
            'ra_motion_scl_spd_dev': 0.02,  # RA 움직임 뉴런 전류 스케일링
            'ra_min_spd_for_input': 1.0,    # RA 움직임 뉴런 활성화 최소 마우스 속도
            'ra_click_clip_min': -40.0,     # RA 클릭 뉴런 입력 전류 최소값
            'ra_click_clip_max': 40.0,      # RA 클릭 뉴런 입력 전류 최대값
            'ra_motion_clip_min': -30.0,    # RA 움직임 뉴런 입력 전류 최소값
            'ra_motion_clip_max': 30.0,     # RA 움직임 뉴런 입력 전류 최대값
        },
        
        # === 사운드 설정 (뉴런 → 오디오 변환) ===
        'sound': {
            # SA 뉴런 사운드 (압력 피드백) - 피에조 진동감 있는 배경음
            'sa_hz': 60,                    # SA 뉴런 기본 주파수 (Hz) - 피에조 진동감을 위해 높게
            'sa_ms': 120,                   # SA 뉴런 사운드 지속시간 (ms) - 충분한 지속시간
            'sa_amp': 0.3,                  # SA 뉴런 사운드 진폭 - 훨씬 더 줄임
            'sa_sound_volume': 0.2,         # SA 뉴런 최종 볼륨 - 훨씬 더 줄임
            
            # RA 움직임 뉴런 사운드 (움직임 피드백) - 부드럽게
            'ra_motion_base_hz': 30,        # RA 움직임 뉴런 기본 주파수 - 더 낮게
            'ra_motion_ms': 100,            # RA 움직임 뉴런 사운드 지속시간
            'ra_motion_base_amp': 0.8,      # RA 움직임 뉴런 기본 진폭 - 더 크게
            'ra_motion_vol_min_spd': 100.0, # RA 움직임 뉴런 최소 볼륨 적용 마우스 속도
            'ra_motion_vol_max_spd': 5000.0,# RA 움직임 뉴런 최대 볼륨 적용 마우스 속도
            'ra_motion_min_vol_scl': 0.7,   # RA 움직임 뉴런 최소 볼륨 스케일 - 더 높게
            'ra_motion_max_vol_scl': 1.0,   # RA 움직임 뉴런 최대 볼륨 스케일 - 최대로
            
            # RA 클릭 뉴런 사운드 (클릭 순간 피드백) - 맥북 터치패드 스타일
            'ra_click_hz': 150,              # RA 클릭 뉴런 주파수 - 저주파로 (실제로는 20-30Hz로 제한됨)
            'ra_click_ms': 70,             # RA 클릭 뉴런 사운드 지속시간 - 더 길게
            'ra_click_amp': 2.5,            # RA 클릭 뉴런 진폭 - 훨씬 더 크게
            'ra_click_volume': 1.0,         # RA 클릭 뉴런 최종 볼륨 - 최대값으로 설정
        },
        
        # === 마우스 입력 설정 ===
        'mouse': {
            'max_spd_clamp': 100000.0,      # 마우스 속도 최대 제한값
            'm_stop_thresh': 0.02,          # 마우스 정지 감지 임계값 (초)
        },
        
        # === 그래프 표시 설정 ===
        'plot': {
            'update_interval': 8,           # 그래프 업데이트 간격 (프레임)
        },
        
        # === 재질별 설정 (키보드 1-7로 선택) ===
        'materials': {
            'Glass': {          # 유리 (키보드 1) - 매우 부드럽고 투명한
                'r': 0.05,          # 거칠기 - 극도로 매끄러운
                'f': 1.6,           # 주파수 계수 - 맑고 높은 소리
                'type': 'glass',    # 파형 타입
                'brightness': 3.0   # 유리 특성 - 투명하고 부드러운
            },
            'Metal': {          # 메탈 (키보드 2) - 날카로운 메탈 질감
                'r': 1.2,           # 거칠기 - 중간 정도의 날카로운 질감
                'f': 1.0,           # 주파수 계수 - 중후한 금속음
                'type': 'metal',    # 파형 타입
                'resonance': 2.2    # 메탈 특성 - 강한 울림
            },
            'Wood': {           # 나무 (키보드 3) - 자연스러운 거칠기
                'r': 1.8,           # 거칠기 - 자연스러운 나무 거칠기
                'f': 0.8,           # 주파수 계수 - 낮고 따뜻한 소리
                'type': 'wood',     # 파형 타입
                'warmth': 2.5       # 나무 특성 - 매우 따뜻하고 자연스러운 느낌
            },
            'Plastic': {        # 플라스틱 (키보드 4) - 부드러운 플라스틱
                'r': 0.3,           # 거칠기 - 매끄러운 플라스틱
                'f': 1.1,           # 주파수 계수 - 인공적 소리
                'type': 'plastic',  # 파형 타입
                'hardness': 1.5     # 플라스틱 특성 - 단단함
            },
            'Fabric': {         # 직물 (키보드 5) - 극도로 부드러운
                'r': 0.02,          # 거칠기 - 극도로 부드러운
                'f': 0.6,           # 주파수 계수 - 낮고 부드러운
                'type': 'fabric',   # 파형 타입
                'softness': 3.0     # 직물 특성 - 매우 부드러운
            },
            'Ceramic': {        # 세라믹 (키보드 6) - 부드러운 세라믹
                'r': 0.6,           # 거칠기 - 적당한 세라믹 질감
                'f': 1.3,           # 주파수 계수 - 맑은 세라믹 소리
                'type': 'ceramic',  # 파형 타입
                'brittleness': 1.8  # 세라믹 특성 - 취성
            },
            'Rubber': {         # 고무 (키보드 7) - 부드러운 고무
                'r': 0.4,           # 거칠기 - 부드러운 고무 질감
                'f': 0.7,           # 주파수 계수 - 낮고 둔탁한
                'type': 'rubber',   # 파형 타입
                'elasticity': 2.0   # 고무 특성 - 탄성적 느낌
            }
        },
        
        # === UI 설정 ===
        'ui': {
            'window_width': 1200,
            'window_height': 1200,
            'spike_threshold': 30.0,
            'fade_out_ms': 10,
            'plot_y_min': -90,
            'plot_y_max': 40,
            'spike_line_color': '#e60026',
            'sa_line_color': '#007aff',
            'ra_line_color': '#ff9500',
        }
    }
    
    _validate_config(config)
    return config

def _validate_config(config):
    """설정값 검증"""
    assert config['neuron_dt_ms'] > 0, "neuron_dt_ms must be positive"
    assert config['plot_hist_sz'] > 0, "plot_hist_sz must be positive"
    
    # 뉴런 파라미터 검증
    sa_cfg = config['sa_neuron']
    assert all(key in sa_cfg for key in ['a', 'b', 'c', 'd']), "SA neuron missing parameters"
    
    ra_cfg = config['ra_neuron']
    assert all(key in ra_cfg for key in ['base_a', 'base_b', 'base_c', 'base_d']), "RA motion neuron missing parameters"
    
    ra_click_cfg = config['ra_click_neuron']
    assert all(key in ra_click_cfg for key in ['a', 'b', 'c', 'd']), "RA click neuron missing parameters"
    
    # 사운드 설정 검증
    sound_cfg = config['sound']
    assert 0 < sound_cfg['sa_hz'] < 22050, "sa_hz must be in valid audio range"
    assert 0 < sound_cfg['ra_motion_base_hz'] < 22050, "ra_motion_base_hz must be in valid audio range"
    assert 0 < sound_cfg['ra_click_hz'] < 22050, "ra_click_hz must be in valid audio range"
    
    # 재질 설정 검증
    for mat_name, mat_props in config['materials'].items():
        assert 'r' in mat_props and 'f' in mat_props, f"Material {mat_name} missing properties"
        assert mat_props['r'] > 0, f"Material {mat_name} roughness must be positive"
        assert mat_props['f'] > 0, f"Material {mat_name} frequency factor must be positive"
    
    print("✅ Configuration validation passed!") 
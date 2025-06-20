# Haptic Ring Monitoring System

**생물학적 뉴런 모델을 활용한 햅틱 피드백 시뮬레이션 시스템**

이 프로젝트는 인간의 촉각 수용체를 Izhikevich 뉴런 모델로 시뮬레이션하여, 마우스 입력을 실시간 햅틱 오디오 피드백으로 변환하는 시스템입니다. 다양한 재질의 촉감을 사운드로 표현하며, 실시간 뉴런 활동을 시각화합니다.

## 시스템 아키텍처

### 주요 구성 요소

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mouse Input   │───▶│  Spike Encoder  │───▶│  Audio Output   │
│  (Click/Move)   │    │   (3 Neurons)   │    │  (Haptic Feed)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GUI Window    │    │ Haptic System   │    │ Haptic Renderer │
│ (Visualization) │    │ (Coordinator)   │    │ (Wave Generator)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 생물학적 뉴런 모델링

시스템은 인간 피부의 촉각 수용체를 3가지 뉴런으로 모델링합니다:

1. **SA 뉴런 (Slowly Adapting)** - 지속적인 압력 감지
   - 마우스 클릭 유지 시 활성화
   - 40-60Hz 진동감 있는 배경음 생성
   - 터치가 일어나고 있다는 느낌

2. **RA 움직임 뉴런 (Rapidly Adapting - Motion)** - 움직임/진동 감지
   - 마우스 드래그 시 활성화
   - 재질별 특화된 질감 사운드 생성
   - 유리처럼 부드러운 질감 구현

3. **RA 클릭 뉴런 (Rapidly Adapting - Click)** - 급격한 압력 변화 감지
   - 클릭 순간의 on/off 감지
   - 20-30Hz 저주파 "딸깍" 사운드
   - 맥북 터치패드 스타일

## 프로젝트 구조

```
HapticRingMonitoring/
├── main.py                    # 메인 실행 파일
├── core/                      # 핵심 시스템 모듈
│   ├── __init__.py
│   ├── config.py             # 전체 시스템 설정
│   ├── gui_window.py         # PyQt6 GUI 인터페이스
│   └── haptic_system.py      # 햅틱 시스템 코디네이터
├── neuron/                    # 뉴런 시뮬레이션 모듈
│   ├── __init__.py
│   ├── izhikevich_neuron.py  # Izhikevich 뉴런 모델
│   └── spike_encoder.py      # 입력→스파이크 변환기
├── audio/                     # 오디오 처리 모듈
│   ├── __init__.py
│   ├── audio_player.py       # 오디오 재생 관리
│   └── haptic_renderer.py    # 사운드 파형 생성기
└── backup/                    # 백업 및 데모 파일들
    ├── automotive_demo.py    # 자동차 데모
    ├── ac_touch_panel.py     # 에어컨 터치패널 데모
    └── simple_driving_simulator.py
```

## 사운드 디자인 특징

### SA 사운드 (배경음)
- **주파수**: 40-60Hz (실제 진동을 느낄 수 있는 범위)
- **특징**: 복잡한 파형 + AM 변조로 진동감 강화
- **필터링**: 3단계 스무딩으로 지직거림 완전 제거
- **용도**: 터치가 일어나고 있다는 은은한 배경 피드백

### RA 클릭 사운드 (딸깍음)
- **주파수**: 20-30Hz 저주파 (재질 무관하게 고정)
- **특징**: 맥북 터치패드 스타일의 정확한 클릭감
- **지속시간**: 60ms의 짧고 명확한 피드백
- **용도**: 클릭 순간의 촉각적 확인

### RA 움직임 사운드 (재질별 질감)
- **유리**: 극도로 부드럽고 투명한 질감 (roughness: 0.05)
- **메탈**: 부드러운 금속 질감 + 적당한 울림
- **나무**: 매우 따뜻하고 부드러운 자연 질감
- **플라스틱**: 매끄럽고 인공적인 느낌
- **직물**: 극도로 부드러운 섬유 질감
- **세라믹**: 맑고 부드러운 세라믹 특성
- **고무**: 탄성적이고 부드러운 느낌

## 설치 및 실행

### 필요한 패키지
```bash
pip install PyQt6 numpy matplotlib pygame
```

### 실행
```bash
python main.py
```

## 사용법

### 마우스 조작
- **클릭**: SA 뉴런 + RA 클릭 뉴런 활성화
- **드래그**: RA 움직임 뉴런 활성화 (재질별 질감)
- **속도**: 마우스 이동 속도에 따라 사운드 강도 변화

### 키보드 단축키
- **1-7**: 재질 변경 (Glass/Metal/Wood/Plastic/Fabric/Ceramic/Rubber)
- **+/-**: 전체 볼륨 조절
- **R**: 시뮬레이션 리셋
- **ESC**: 프로그램 종료

### 실시간 모니터링
- **3개 뉴런의 실시간 그래프** 표시
- **현재 재질, 마우스 속도, 발화율, 볼륨** 정보 표시
- **스파이크 이벤트** 빨간 선으로 표시

## 주요 기술적 특징

### 병렬 뉴런 시뮬레이션
- IzhikevichNeuronArray를 통한 벡터화된 계산
- 3개 뉴런을 동시에 처리하여 3배 성능 향상

### 고품질 사운드 렌더링
- 44.1kHz 샘플링 레이트
- 재질별 전용 파형 생성 함수
- 강력한 안티앨리어싱 필터링
- 자연스러운 어택/페이드아웃 처리

### 실시간 성능 최적화
- 효율적인 deque 기반 히스토리 관리
- 적응적 그래프 업데이트 주기
- 메모리 효율적인 사운드 버퍼 관리

### 설정 중심 아키텍처
- config.py에서 모든 파라미터 중앙 관리
- 뉴런 모델, 사운드, 재질 특성 완전 분리
- 쉬운 튜닝과 실험적 수정 가능

## 실시간 모니터링 정보

### 그래프 표시
- **SA 뉴런**: 막전위(V)와 회복변수(U) 실시간 그래프
- **RA 움직임**: 움직임 감지 뉴런의 활동
- **RA 클릭**: 클릭 감지 뉴런의 활동
- **스파이크 마커**: 발화 순간을 빨간 수직선으로 표시

### 상태 정보
- **현재 재질**: 선택된 재질과 거칠기(R) 값
- **마우스 속도**: 실시간 이동 속도
- **발화율**: 초당 스파이크 발생 빈도
- **볼륨**: 현재 오디오 출력 레벨

## 연구 및 실험 목적

이 시스템은 다음과 같은 연구 목적으로 활용될 수 있습니다:

- **햅틱 피드백 연구**: 다양한 재질 감각의 오디오 피드백 효과
- **뉴런 모델링**: Izhikevich 모델의 촉각 수용체 적용
- **인터페이스 디자인**: 터치 인터페이스의 사용자 경험 개선
- **접근성 연구**: 시각장애인을 위한 촉각 피드백 시스템

## 작동 원리

### 1. Izhikevich 뉴런 모델

시스템의 핵심은 생물학적 뉴런의 전기적 활동을 모사하는 Izhikevich 모델입니다:

```
dv/dt = 0.04*v² + 5*v + 140 - u + I    (막전위 변화)
du/dt = a(bv - u)                       (회복변수 변화)
```

**스파이크 발생 조건**: v ≥ 30mV 도달 시
- 막전위 v를 c로 리셋
- 회복변수 u에 d 추가 (후과분극 효과)

**파라미터 의미**:
- **a**: 회복속도 (작을수록 느린 회복)
- **b**: 막전위 민감도 (높을수록 민감한 반응)
- **c**: 스파이크 후 리셋 전압 (보통 -65mV)
- **d**: 후과분극 강도 (스파이크 후 억제 효과)

### 2. 3개 뉴런의 역할 분담

#### SA 뉴런 (압력 센서)
```
파라미터: a=0.05, b=0.25, c=-65, d=6
특성: 느린 적응, 지속적 반응
입력: 마우스 클릭 압력 (12.0 단위)
```
- 클릭 유지 시 지속적으로 발화
- 시간이 지날수록 적응하여 발화율 감소 (a값 점진적 감소)
- 40-60Hz 진동 배경음 생성

#### RA 움직임 뉴런 (속도 센서)
```
파라미터: a=0.4, b=0.25, c=-65, d=1.5
특성: 빠른 적응, 변화에 민감
입력: (마우스속도 × 재질거칠기) × 0.02
```
- 마우스 이동 시에만 반응
- 속도 변화에 비례하여 발화
- 재질별 특화된 질감 사운드 생성

#### RA 클릭 뉴런 (변화 감지)
```
파라미터: a=0.3, b=0.25, c=-65, d=6
특성: 매우 빠른 반응, 순간적 감지
입력: |압력변화| × 100 (3프레임 지속)
```
- 클릭 on/off 순간에만 반응
- 압력 변화량에 비례하여 발화
- 20-30Hz 저주파 클릭음 생성

### 3. 입력 처리 과정

#### 마우스 → 뉴런 전류 변환
```python
# SA 뉴런: 클릭 압력
I_sa = click_magnitude  # 12.0 (클릭 시)

# RA 움직임: 속도 × 재질
I_ra_motion = mouse_speed × material_roughness × 0.02
I_ra_motion = clip(I_ra_motion, -30, 30)

# RA 클릭: 압력 변화
pressure_delta = |current_pressure - previous_pressure|
I_ra_click = pressure_delta × 100 (3프레임 지속)
I_ra_click = clip(I_ra_click, -40, 40)
```

#### 병렬 뉴런 시뮬레이션
```python
# 3개 뉴런을 벡터화하여 동시 계산
I_array = [I_sa, I_ra_motion, I_ra_click]
fired_array = neuron_array.step(dt=1.0, I_array)
# 결과: [SA_fired, RA_motion_fired, RA_click_fired]
```

### 4. 사운드 생성 과정

#### 스파이크 → 사운드 변환
각 뉴런의 스파이크 발생 시 해당하는 사운드를 재생:

```python
if sa_fired:
    # 진동감 있는 배경음 (40-60Hz)
    play_sound(sa_background_sound, volume=0.3)

if ra_click_fired:
    # 저주파 클릭음 (20-30Hz)
    play_sound(ra_click_sound, volume=1.0)

if ra_motion_fired:
    # 연속 질감 사운드 볼륨 조절
    update_motion_volume(spike_rate)
```

#### 재질별 파형 생성
각 재질마다 고유한 파형 특성을 가집니다:

```python
# 유리: 맑고 투명한 파형
fundamental + 0.08*harmonic2 + 0.03*harmonic3 + subtle_texture

# 메탈: 울림이 있는 파형  
fundamental + metallic_harmonics + resonance_modulation

# 나무: 따뜻한 파형
fundamental + warm_harmonics + wood_texture
```

### 5. 실시간 볼륨 제어

#### 스파이크율 기반 볼륨 조절
RA 움직임 사운드는 스파이크 발생률에 따라 볼륨이 동적으로 변화:

```python
# 1초 윈도우 내 스파이크 개수 계산
spike_rate = spike_count / window_duration  # Hz

# 스파이크율 → 볼륨 매핑
if spike_rate < 20Hz: volume = 0.5
elif spike_rate > 120Hz: volume = 0.8
else: volume = linear_interpolation(20, 120, 0.5, 0.8)

# 부드러운 볼륨 변화 (스무딩)
current_volume += (target_volume - current_volume) * smooth_factor
```

### 6. 성능 최적화

#### 벡터화 계산
```python
# 기존: 3개 뉴런을 순차적으로 계산 (3배 시간)
for neuron in neurons:
    neuron.step(dt, I[i])

# 최적화: 3개 뉴런을 동시에 계산
neuron_array.step(dt, I_array)  # 벡터화로 3배 빠름
```

#### 사운드 캐싱
```python
# 재질별 사운드 미리 생성하여 캐싱
sound_cache = {
    "ra_motion_Glass_48": pregenerated_glass_sound,
    "ra_click_Metal_80": pregenerated_metal_click,
    ...
}
```

### 7. 실시간 피드백 루프

```
마우스 이벤트 (1ms) → 뉴런 시뮬레이션 (1ms) → 사운드 재생 (즉시)
       ↓                    ↓                    ↓
   입력 전류 계산     →   스파이크 생성      →   파형 출력
       ↓                    ↓                    ↓
   재질 특성 적용     →   발화율 계산       →   볼륨 조절
```

이 전체 과정이 1ms마다 반복되어 실시간 햅틱 피드백을 제공합니다.

## 기술 문서

### 핵심 클래스
- `HapticSystem`: 전체 시스템 조정 및 사운드 관리
- `SpikeEncoder`: 마우스 입력을 뉴런 스파이크로 변환
- `IzhikevichNeuronArray`: 병렬 뉴런 시뮬레이션
- `HapticRenderer`: 스파이크를 사운드 파형으로 렌더링
- `HapticGUI`: PyQt6 기반 실시간 시각화

### 데이터 플로우
```
마우스 입력 → SpikeEncoder → Izhikevich 뉴런들 → HapticRenderer → 사운드 출력
    ↓              ↓              ↓              ↓
GUI 이벤트 → 입력 전류 계산 → 스파이크 생성 → 파형 생성 → pygame 재생
```

**World Haptics Conference 2025** 발표를 위해 개발된 연구 프로젝트입니다.

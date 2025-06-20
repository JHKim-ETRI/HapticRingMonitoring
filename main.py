'''
Haptic Ring Monitoring - Main Entry Point
햅틱 피드백 시뮬레이션 메인 진입점

역할: 설정 정의 + 애플리케이션 실행
실제 기능은 모두 다른 모듈에서 담당
'''

import sys
from PyQt6.QtWidgets import QApplication
from core.gui_window import HapticGUI
from core.config import get_haptic_config

def main():
    """메인 실행 함수 - 설정 로드 후 GUI 시작"""
    print("🎵 Haptic Ring Monitoring System Starting...")
    
    # 설정 로드
    config = get_haptic_config()
    print("✅ Configuration loaded successfully!")
    
    # PyQt6 애플리케이션 시작
    app = QApplication(sys.argv)
    
    # GUI 윈도우 생성 및 실행
    window = HapticGUI(config)
    window.show()
    
    print("🚀 GUI launched! Ready for haptic feedback.")
    
    # 애플리케이션 실행
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 
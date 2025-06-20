import pygame
import sys
import numpy as np
import time
from collections import deque

# 기존 햅틱 시스템 모듈들 임포트
from core.config import get_haptic_config
from core.haptic_system import HapticSystem

class AutomotiveClimateGUI:
    def __init__(self):
        pygame.init()
        
        # 화면 설정
        self.width = 1600
        self.height = 600
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Vehicle Climate Control")
        
        # 색상 정의 - 실제 차량 스타일
        self.BLACK = (15, 15, 20)             # 어두운 배경
        self.WHITE = (255, 255, 255)          # 흰색 아이콘/텍스트
        self.BLUE_ACTIVE = (80, 150, 255)     # 파란색 활성화 (냉방)
        self.ORANGE_ACTIVE = (255, 140, 60)   # 주황색 활성화 (난방)
        self.GRAY_INACTIVE = (120, 120, 130)  # 비활성화
        self.GREEN_ACTIVE = (100, 255, 120)   # 초록색 (자동/에코)
        self.RED_ACTIVE = (255, 100, 100)     # 빨간색 (경고/디프로스트)
        
        # 폰트 설정
        self.font_large = pygame.font.Font(None, 48)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 28)
        self.font_icon = pygame.font.Font(None, 42)  # 아이콘용
        
        # 공조기 상태
        self.climate_state = {
            'temperature': 22,
            'fan_speed': 3,
            'ac_on': True,
            'heat_on': False,
            'auto_mode': False,
            'front_defrost': False,
            'rear_defrost': False,
            'circulation': 'external',  # external/internal
            'driver_only': False,
            'left_seat_heat': 0,   # 0-3 단계
            'right_seat_heat': 0,  # 0-3 단계
            'left_seat_cool': False,
            'right_seat_cool': False,
            'steering_heat': False
        }
        
        # 햅틱 시스템 초기화
        self.config = get_haptic_config()
        self.haptic_system = HapticSystem(self.config)
        self.haptic_system.change_material(3)  # Plastic (차량 내부)
        
        # 버튼들 생성 - 실제 차량 레이아웃
        self.buttons = self.create_vehicle_buttons()
        
        # 마우스 상태
        self.mouse_pressed = False
        self.last_mouse_pos = (0, 0)
        self.last_mouse_time = time.perf_counter()
        self.mouse_speed = 0.0
        self.speed_history = deque(maxlen=10)
        self.avg_mouse_speed = 0.0
        
        # 버튼 hover 상태 추적
        self.hovered_button = None
        self.prev_hovered_button = None
        self.hover_start_time = 0.0
        self.hover_feedback_sent = False  # hover 피드백 중복 방지
        
        # 설정
        self.max_speed_clamp = 100000.0
        self.mouse_stop_threshold = 0.02
        self.min_mouse_delta_time = 0.0001
        
        self.clock = pygame.time.Clock()
        print("Vehicle Climate Control initialized")
        
    def create_vehicle_buttons(self):
        """실제 차량 공조기 레이아웃 생성"""
        buttons = []
        
        # 화면 중앙 계산
        center_x = self.width // 2
        center_y = self.height // 2
        
        # 버튼 간격
        btn_spacing = 180
        
        # 상단 줄 버튼들
        top_y = center_y - 80
        top_buttons = [
            # 좌측 시트 히터 (레벨 표시)
            {"name": "left_seat_heat", "icon": "SEAT", "text": f"L-HEAT\nLV.{self.climate_state['left_seat_heat']}", 
             "x": center_x - btn_spacing*3, "active": self.climate_state['left_seat_heat'] > 0, 
             "color": "orange", "action": "toggle_left_seat_heat"},
            
            # 운전석 전용
            {"name": "driver_only", "icon": "DRIV", "text": "DRIVER\nONLY", 
             "x": center_x - btn_spacing*2, "active": self.climate_state['driver_only'], 
             "color": "green", "action": "toggle_driver_only"},
            
            # 팬 아이콘 (좌측)
            {"name": "fan_left", "icon": "FAN", "text": "FAN", 
             "x": center_x - btn_spacing//2, "action": "decrease_fan"},
            
            # 풍량 조절 바 (중앙) - 디스플레이만
            {"name": "fan_control", "icon": "||||", "text": f"LEVEL {self.climate_state['fan_speed']}", 
             "x": center_x, "type": "fan_display"},
            
            # 팬 아이콘 (우측)
            {"name": "fan_right", "icon": "FAN", "text": "FAN", 
             "x": center_x + btn_spacing//2, "action": "increase_fan"},
            
            # 스티어링 휠 히터
            {"name": "steering_heat", "icon": "HELM", "text": "WHEEL\nHEAT", 
             "x": center_x + btn_spacing*2, "active": self.climate_state['steering_heat'], 
             "color": "orange", "action": "toggle_steering_heat"},
            
            # 우측 시트 히터 (레벨 표시)
            {"name": "right_seat_heat", "icon": "SEAT", "text": f"R-HEAT\nLV.{self.climate_state['right_seat_heat']}", 
             "x": center_x + btn_spacing*3, "active": self.climate_state['right_seat_heat'] > 0, 
             "color": "orange", "action": "toggle_right_seat_heat"},
        ]
        
        # 하단 줄 버튼들
        bottom_y = center_y + 80
        bottom_buttons = [
            # 좌측 시트 쿨링 (상태 표시)
            {"name": "left_seat_cool", "icon": "COOL", "text": f"L-COOL\n{'ON' if self.climate_state['left_seat_cool'] else 'OFF'}", 
             "x": center_x - btn_spacing*3, "active": self.climate_state['left_seat_cool'], 
             "color": "blue", "action": "toggle_left_seat_cool"},
            
            # OFF
            {"name": "system_off", "icon": "OFF", "text": "OFF", 
             "x": center_x - btn_spacing*2, "active": False, 
             "color": "white", "action": "toggle_system_off"},
            
            # A/C
            {"name": "ac", "icon": "A/C", "text": "A/C", 
             "x": center_x - btn_spacing//2, "active": self.climate_state['ac_on'], 
             "color": "blue", "action": "toggle_ac"},
            
            # 온도 표시 (중앙)
            {"name": "temp_display", "icon": f"{self.climate_state['temperature']}°", "text": f"{self.climate_state['temperature']}°C", 
             "x": center_x, "type": "temp_display", "action": "temp_control"},
            
            # 순환 모드
            {"name": "circulation", "icon": "CIRC", "text": "CIRC", 
             "x": center_x + btn_spacing//2, "active": self.climate_state['circulation'] == 'internal', 
             "color": "blue", "action": "toggle_circulation"},
            
            # 앞유리 디프로스트
            {"name": "front_defrost", "icon": "DEF", "text": "F-DEF", 
             "x": center_x + btn_spacing*2, "active": self.climate_state['front_defrost'], 
             "color": "red", "action": "toggle_front_defrost"},
            
            # 우측 시트 쿨링 (상태 표시)
            {"name": "right_seat_cool", "icon": "COOL", "text": f"R-COOL\n{'ON' if self.climate_state['right_seat_cool'] else 'OFF'}", 
             "x": center_x + btn_spacing*3, "active": self.climate_state['right_seat_cool'], 
             "color": "blue", "action": "toggle_right_seat_cool"},
        ]
        
        # 상단 버튼들 추가
        for btn in top_buttons:
            btn.update({
                "y": top_y,
                "rect": pygame.Rect(btn["x"] - 80, top_y - 50, 160, 100),
                "type": btn.get("type", "control")
            })
            buttons.append(btn)
        
        # 하단 버튼들 추가
        for btn in bottom_buttons:
            btn.update({
                "y": bottom_y,
                "rect": pygame.Rect(btn["x"] - 80, bottom_y - 50, 160, 100),
                "type": btn.get("type", "control")
            })
            buttons.append(btn)
            
        return buttons
    
    def get_button_color(self, color_name):
        """버튼 색상 반환"""
        colors = {
            "blue": self.BLUE_ACTIVE,
            "orange": self.ORANGE_ACTIVE,
            "green": self.GREEN_ACTIVE,
            "red": self.RED_ACTIVE,
            "white": self.WHITE
        }
        return colors.get(color_name, self.WHITE)
    
    def draw_button(self, button):
        """버튼 그리기 - 실제 차량 스타일"""
        x, y = button["x"], button["y"]
        
        # 활성 상태에 따른 색상
        if button.get("type") in ["fan_display", "temp_display"]:
            # 디스플레이는 항상 밝게
            color = self.WHITE
            text_color = self.WHITE
            icon_scale = 1.1
        elif button.get("active"):
            color = self.get_button_color(button.get("color", "white"))
            text_color = color
            icon_scale = 1.2
        else:
            color = self.GRAY_INACTIVE
            text_color = self.GRAY_INACTIVE
            icon_scale = 1.0
        
        # 호버 상태 강조 (풍량 바는 호버 효과 없음)
        if self.hovered_button == button and button.get("type") != "fan_display":
            # 글로우 효과
            glow_color = tuple(min(255, c + 80) for c in color[:3])
            pygame.draw.rect(self.screen, glow_color, 
                           (x - 85, y - 55, 170, 110), 3)
            icon_scale *= 1.25
        
        # 버튼 배경 (미묘한 테두리) - 풍량 바는 배경 없음
        if (button.get("active") or self.hovered_button == button) and button.get("type") != "fan_display":
            pygame.draw.rect(self.screen, color, 
                           (x - 75, y - 45, 150, 90), 2)
        
        # 풍량 조절 바 특별 그리기
        if button["name"] == "fan_control":
            self.draw_fan_control_bar(x, y, text_color)
        else:
            # 일반 아이콘 그리기
            icon_size = int(32 * icon_scale)
            icon_font = pygame.font.Font(None, icon_size)
            icon_surface = icon_font.render(button["icon"], True, text_color)
            icon_rect = icon_surface.get_rect(center=(x, y - 10))
            self.screen.blit(icon_surface, icon_rect)
        
        # 텍스트 라벨 (작게)
        text_lines = button["text"].split('\n')
        for i, line in enumerate(text_lines):
            text_surface = self.font_small.render(line, True, text_color)
            text_rect = text_surface.get_rect(center=(x, y + 25 + i*15))
            self.screen.blit(text_surface, text_rect)
    
    def draw_fan_control_bar(self, x, y, color):
        """풍량 조절 바 그리기 - 이미지에 있던 스타일"""
        bar_width = 80
        bar_height = 8
        segments = 5
        
        # 배경 바
        pygame.draw.rect(self.screen, self.GRAY_INACTIVE, 
                        (x - bar_width//2, y - bar_height//2, bar_width, bar_height))
        
        # 활성화된 세그먼트들
        segment_width = bar_width / segments
        for i in range(self.climate_state['fan_speed']):
            segment_x = x - bar_width//2 + i * segment_width
            segment_color = self.BLUE_ACTIVE if i < self.climate_state['fan_speed'] else self.GRAY_INACTIVE
            pygame.draw.rect(self.screen, segment_color,
                           (segment_x + 2, y - bar_height//2 + 2, segment_width - 4, bar_height - 4))
    
    def send_hover_haptic_feedback(self):
        """버튼 hover 시 강한 햅틱 피드백"""
        # 강제로 클릭 피드백 발생 (hover 용)
        if not self.hover_feedback_sent:
            self.haptic_system.mouse_press()
            self.haptic_system.mouse_release()
            self.hover_feedback_sent = True
            print(f"🎯 STRONG HOVER FEEDBACK: {self.hovered_button['name']}")
    
    def send_exit_haptic_feedback(self, button_name):
        """버튼 hover 이탈 시 약한 햅틱 피드백"""
        # 이탈 시에도 클릭 피드백 (더 약하게)
        self.haptic_system.mouse_press()
        self.haptic_system.mouse_release()
        print(f"🔽 EXIT FEEDBACK: {button_name}")
    
    def handle_button_action(self, button):
        """버튼 액션 처리"""
        action = button.get("action")
        if not action:
            return
            
        if action == "toggle_left_seat_heat":
            self.climate_state['left_seat_heat'] = (self.climate_state['left_seat_heat'] + 1) % 4
            button["active"] = self.climate_state['left_seat_heat'] > 0
            print(f"Left Seat Heat: Level {self.climate_state['left_seat_heat']}")
            
        elif action == "toggle_right_seat_heat":
            self.climate_state['right_seat_heat'] = (self.climate_state['right_seat_heat'] + 1) % 4
            button["active"] = self.climate_state['right_seat_heat'] > 0
            print(f"Right Seat Heat: Level {self.climate_state['right_seat_heat']}")
            
        elif action == "toggle_driver_only":
            self.climate_state['driver_only'] = not self.climate_state['driver_only']
            button["active"] = self.climate_state['driver_only']
            print(f"Driver Only: {'ON' if self.climate_state['driver_only'] else 'OFF'}")
            
        elif action == "increase_fan":
            if self.climate_state['fan_speed'] < 5:
                self.climate_state['fan_speed'] += 1
                print(f"Fan Speed: {self.climate_state['fan_speed']}")
            
        elif action == "decrease_fan":
            if self.climate_state['fan_speed'] > 1:
                self.climate_state['fan_speed'] -= 1
                print(f"Fan Speed: {self.climate_state['fan_speed']}")
            
        elif action == "temp_control":
            # 온도 조절 (클릭할 때마다 +1)
            if self.climate_state['temperature'] < 30:
                self.climate_state['temperature'] += 1
            else:
                self.climate_state['temperature'] = 16
            print(f"Temperature: {self.climate_state['temperature']}°C")
            
        elif action == "toggle_steering_heat":
            self.climate_state['steering_heat'] = not self.climate_state['steering_heat']
            button["active"] = self.climate_state['steering_heat']
            print(f"Steering Wheel Heat: {'ON' if self.climate_state['steering_heat'] else 'OFF'}")
            
        elif action == "toggle_left_seat_cool":
            self.climate_state['left_seat_cool'] = not self.climate_state['left_seat_cool']
            button["active"] = self.climate_state['left_seat_cool']
            print(f"Left Seat Cool: {'ON' if self.climate_state['left_seat_cool'] else 'OFF'}")
            
        elif action == "toggle_right_seat_cool":
            self.climate_state['right_seat_cool'] = not self.climate_state['right_seat_cool']
            button["active"] = self.climate_state['right_seat_cool']
            print(f"Right Seat Cool: {'ON' if self.climate_state['right_seat_cool'] else 'OFF'}")
            
        elif action == "toggle_system_off":
            # 모든 시스템 끄기
            self.climate_state['ac_on'] = False
            self.climate_state['heat_on'] = False
            self.climate_state['auto_mode'] = False
            self.update_all_buttons()
            print("System OFF - All functions disabled")
            
        elif action == "toggle_ac":
            self.climate_state['ac_on'] = not self.climate_state['ac_on']
            button["active"] = self.climate_state['ac_on']
            if self.climate_state['ac_on']:
                self.climate_state['heat_on'] = False
                self.update_button_active('heat', False)
            print(f"A/C: {'ON' if self.climate_state['ac_on'] else 'OFF'}")
            
        elif action == "toggle_circulation":
            self.climate_state['circulation'] = 'internal' if self.climate_state['circulation'] == 'external' else 'external'
            button["active"] = self.climate_state['circulation'] == 'internal'
            print(f"Air Circulation: {self.climate_state['circulation'].upper()}")
            
        elif action == "toggle_front_defrost":
            self.climate_state['front_defrost'] = not self.climate_state['front_defrost']
            button["active"] = self.climate_state['front_defrost']
            print(f"Front Defrost: {'ON' if self.climate_state['front_defrost'] else 'OFF'}")
            
        self.update_display_buttons()
    
    def update_display_buttons(self):
        """디스플레이 버튼들 업데이트"""
        for btn in self.buttons:
            if btn["name"] == "fan_control":
                btn["text"] = f"LEVEL {self.climate_state['fan_speed']}"
            elif btn["name"] == "temp_display":
                btn["icon"] = f"{self.climate_state['temperature']}°"
                btn["text"] = f"{self.climate_state['temperature']}°C"
            elif btn["name"] == "left_seat_heat":
                btn["text"] = f"L-HEAT\nLV.{self.climate_state['left_seat_heat']}"
                btn["active"] = self.climate_state['left_seat_heat'] > 0
            elif btn["name"] == "right_seat_heat":
                btn["text"] = f"R-HEAT\nLV.{self.climate_state['right_seat_heat']}"
                btn["active"] = self.climate_state['right_seat_heat'] > 0
            elif btn["name"] == "left_seat_cool":
                btn["text"] = f"L-COOL\n{'ON' if self.climate_state['left_seat_cool'] else 'OFF'}"
            elif btn["name"] == "right_seat_cool":
                btn["text"] = f"R-COOL\n{'ON' if self.climate_state['right_seat_cool'] else 'OFF'}"
    
    def update_all_buttons(self):
        """모든 버튼 상태 업데이트"""
        for btn in self.buttons:
            name = btn["name"]
            if name == "ac":
                btn["active"] = self.climate_state['ac_on']
            elif name == "heat":
                btn["active"] = self.climate_state['heat_on']
            # 다른 버튼들도 필요시 추가
    
    def update_button_active(self, button_name, active):
        """특정 버튼의 활성 상태 업데이트"""
        for btn in self.buttons:
            if btn["name"] == button_name:
                btn["active"] = active
                break
    
    def handle_mouse_move(self, pos):
        """마우스 이동 처리"""
        current_time = time.perf_counter()
        
        # 버튼 hover 상태 확인
        self.prev_hovered_button = self.hovered_button
        self.hovered_button = None
        
        for button in self.buttons:
            if button["rect"].collidepoint(pos):
                # 풍량 바는 hover 불가
                if button.get("type") != "fan_display":
                    self.hovered_button = button
                break
        
        # 버튼 진입/이탈 감지
        if self.hovered_button != self.prev_hovered_button:
            if self.hovered_button:
                self.hover_start_time = current_time
                self.hover_feedback_sent = False  # 새 버튼이므로 피드백 리셋
                # 즉시 강한 hover 피드백 발생
                self.send_hover_haptic_feedback()
                print(f"⬆️ HOVER: {self.hovered_button['name']}")
            elif self.prev_hovered_button:
                # 이탈 시 피드백
                self.send_exit_haptic_feedback(self.prev_hovered_button['name'])
                print(f"⬇️ EXIT: {self.prev_hovered_button['name']}")
        
        # 마우스 속도 계산 (버튼 위에서만)
        if self.hovered_button and self.last_mouse_pos:
            dx = pos[0] - self.last_mouse_pos[0]
            dy = pos[1] - self.last_mouse_pos[1]
            distance = np.sqrt(dx**2 + dy**2)
            dt = current_time - self.last_mouse_time
            
            if dt > self.min_mouse_delta_time:
                self.mouse_speed = min(distance / dt, self.max_speed_clamp)
                self.speed_history.append(self.mouse_speed)
                self.avg_mouse_speed = np.mean(self.speed_history)
                
                self.last_mouse_pos = pos
                self.last_mouse_time = current_time
        elif not self.hovered_button:
            self.mouse_speed = 0.0
            self.avg_mouse_speed = 0.0
    
    def update_haptic_system(self):
        """햅틱 시스템 업데이트"""
        if (time.perf_counter() - self.last_mouse_time) > self.mouse_stop_threshold:
            self.mouse_speed = 0.0
        
        # 버튼 위에서만 햅틱 피드백
        if self.hovered_button:
            self.haptic_system.step(
                mouse_speed=self.mouse_speed,
                avg_mouse_speed=self.avg_mouse_speed
            )
    
    def draw_hud(self):
        """HUD 정보 표시"""
        # 제목
        title = self.font_large.render("Vehicle Climate Control System", True, self.WHITE)
        self.screen.blit(title, (50, 30))
        
        # 현재 상태 요약
        mode_text = []
        if self.climate_state['ac_on']:
            mode_text.append("A/C")
        if self.climate_state['driver_only']:
            mode_text.append("DRIVER-ONLY")
        if self.climate_state['front_defrost']:
            mode_text.append("DEFROST")
        if not mode_text:
            mode_text.append("OFF")
            
        status = f"Mode: {', '.join(mode_text)} | Temp: {self.climate_state['temperature']}°C | Fan: {self.climate_state['fan_speed']}"
        status_surface = self.font_medium.render(status, True, self.WHITE)
        self.screen.blit(status_surface, (50, 80))
        
        # 시트 상태
        seat_status = f"Seats - L.Heat:{self.climate_state['left_seat_heat']} L.Cool:{'ON' if self.climate_state['left_seat_cool'] else 'OFF'} | R.Heat:{self.climate_state['right_seat_heat']} R.Cool:{'ON' if self.climate_state['right_seat_cool'] else 'OFF'}"
        seat_surface = self.font_small.render(seat_status, True, self.GRAY_INACTIVE)
        self.screen.blit(seat_surface, (50, 110))
        
        # Hover 상태
        if self.hovered_button:
            hover_info = f"Hovering: {self.hovered_button['name'].replace('_', ' ').title()}"
            hover_color = self.get_button_color(self.hovered_button.get("color", "white"))
        else:
            hover_info = "Move cursor over buttons for haptic feedback"
            hover_color = self.GRAY_INACTIVE
            
        hover_text = self.font_small.render(hover_info, True, hover_color)
        self.screen.blit(hover_text, (50, self.height - 60))
        
        # 햅틱 상태
        haptic_text = f"Haptic Feedback: {'ACTIVE' if self.hovered_button else 'STANDBY'}"
        haptic_surface = self.font_small.render(haptic_text, True, 
                                              self.GREEN_ACTIVE if self.hovered_button else self.GRAY_INACTIVE)
        self.screen.blit(haptic_surface, (50, self.height - 30))
    
    def draw(self):
        """화면 그리기"""
        self.screen.fill(self.BLACK)
        
        # HUD 그리기
        self.draw_hud()
        
        # 버튼들 그리기
        for button in self.buttons:
            self.draw_button(button)
    
    def run(self):
        """메인 실행 루프"""
        print("Starting vehicle climate control system...")
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.mouse_pressed = True
                        self.last_mouse_pos = event.pos
                        self.last_mouse_time = time.perf_counter()
                        self.mouse_speed = 0.0
                        self.speed_history.clear()
                        self.avg_mouse_speed = 0.0
                        
                        if self.hovered_button:
                            self.haptic_system.mouse_press()
                        
                        # 클릭 처리 (풍량 바는 클릭 불가)
                        for button in self.buttons:
                            if button["rect"].collidepoint(event.pos):
                                if button.get("type") != "fan_display":  # 풍량 바 클릭 방지
                                    self.handle_button_action(button)
                                break
                        
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        self.mouse_pressed = False
                        self.mouse_speed = 0.0
                        self.haptic_system.mouse_release()
                        
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_move(event.pos)
            
            # 햅틱 시스템 업데이트
            self.update_haptic_system()
            
            # 화면 그리기
            self.draw()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        # 정리
        self.haptic_system.cleanup()
        pygame.quit()
        print("Vehicle climate control terminated")

if __name__ == "__main__":
    try:
        gui = AutomotiveClimateGUI()
        gui.run()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 
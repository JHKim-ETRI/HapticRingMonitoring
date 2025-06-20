#!/usr/bin/env python3
"""
Automotive Climate Control Demo
"""

import sys
import os

# 프로젝트 루트를 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

def main():
    """Automotive Climate Control Demo 실행"""
    try:
        from gui.automotive_climate_gui import AutomotiveClimateGUI
        
        print("Starting Automotive Climate Demo...")
        gui = AutomotiveClimateGUI()
        gui.run()
        
    except ImportError as e:
        print(f"Import error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 
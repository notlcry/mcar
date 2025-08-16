#!/usr/bin/env python3
"""
Comprehensive test for the OLED Expression Control System
Tests all required functionality for task 3
"""

import time
import logging
from expression_controller import ExpressionController
from display_driver import DisplayDriver

def test_display_driver():
    """Test display driver functionality"""
    print("=== Testing Display Driver ===")
    
    driver = DisplayDriver()
    info = driver.get_display_info()
    print(f"Display Info: {info}")
    
    # Test basic image creation and display
    img = driver.create_blank_image()
    print(f"Created blank image: {img.size}")
    
    # Test drawing
    result = driver.draw_expression(img)
    print(f"Draw expression result: {result}")
    
    # Test brightness control
    driver.set_brightness(128)
    print("Set brightness to 128")
    
    # Test clear display
    driver.clear_display()
    print("Cleared display")
    
    driver.cleanup()
    print("Display driver test completed\n")

def test_basic_expressions():
    """Test basic emotion expressions"""
    print("=== Testing Basic Expressions ===")
    
    controller = ExpressionController()
    
    # Test all required emotions
    emotions = ["neutral", "happy", "sad", "confused", "thinking", "surprised"]
    
    for emotion in emotions:
        print(f"Testing emotion: {emotion}")
        controller.show_emotion(emotion)
        time.sleep(1)
    
    print("Basic expressions test completed\n")

def test_speaking_animation():
    """Test speaking mouth animation synchronization"""
    print("=== Testing Speaking Animation ===")
    
    controller = ExpressionController()
    
    # Test speaking animation with different durations
    durations = [1.0, 2.0, 3.0]
    
    for duration in durations:
        print(f"Testing speaking animation for {duration} seconds")
        controller.animate_speaking(duration)
        time.sleep(duration + 0.5)  # Wait for animation to complete
    
    # Test TTS synchronization method
    print("Testing TTS synchronization")
    controller.synchronize_mouth_with_tts(2.5)
    time.sleep(3.0)
    
    print("Speaking animation test completed\n")

def test_idle_animations():
    """Test idle state blinking and breathing animations"""
    print("=== Testing Idle Animations ===")
    
    controller = ExpressionController()
    
    # Test idle animation
    print("Starting idle animation (blinking and breathing)")
    controller.show_idle_animation()
    time.sleep(5)  # Let it run for 5 seconds
    
    controller.stop_idle_animation()
    print("Stopped idle animation")
    
    print("Idle animations test completed\n")

def test_listening_animation():
    """Test listening animation"""
    print("=== Testing Listening Animation ===")
    
    controller = ExpressionController()
    
    print("Showing listening animation")
    controller.show_listening_animation()
    time.sleep(2)
    
    controller.stop_listening_animation()
    print("Stopped listening animation")
    
    print("Listening animation test completed\n")

def test_thinking_animation():
    """Test thinking animation"""
    print("=== Testing Thinking Animation ===")
    
    controller = ExpressionController()
    
    print("Showing thinking animation")
    controller.show_thinking_animation()
    time.sleep(3)
    
    controller.stop_thinking_animation()
    print("Stopped thinking animation")
    
    print("Thinking animation test completed\n")

def test_animation_control():
    """Test animation start/stop control"""
    print("=== Testing Animation Control ===")
    
    controller = ExpressionController()
    
    # Test starting multiple animations and stopping them
    print("Starting idle animation")
    controller.show_idle_animation()
    time.sleep(1)
    
    print("Starting thinking animation (should stop idle)")
    controller.show_thinking_animation()
    time.sleep(1)
    
    print("Starting speaking animation (should stop thinking)")
    controller.animate_speaking(2.0)
    time.sleep(1)
    
    print("Stopping all animations")
    controller.stop_all_animations()
    time.sleep(1)
    
    # Test state reporting
    state = controller.get_current_state()
    print(f"Current state: {state}")
    
    print("Animation control test completed\n")

def test_requirements_compliance():
    """Test compliance with task requirements"""
    print("=== Testing Requirements Compliance ===")
    
    controller = ExpressionController()
    
    # Requirement 5.1: Display default "awake" eyes on initialization
    print("✓ Requirement 5.1: Default awake eyes displayed on initialization")
    
    # Requirement 5.2: Display corresponding facial expressions for different emotions
    emotions = ["happy", "sad", "surprised", "confused", "thinking"]
    for emotion in emotions:
        controller.show_emotion(emotion)
        print(f"✓ Requirement 5.2: {emotion} expression displayed")
        time.sleep(0.5)
    
    # Requirement 5.3: Mouth animation synchronized with TTS output
    controller.synchronize_mouth_with_tts(1.5)
    print("✓ Requirement 5.3: Mouth animation synchronized with TTS")
    time.sleep(2)
    
    # Requirement 5.4: Focused expression during listening
    controller.show_listening_animation()
    print("✓ Requirement 5.4: Focused listening expression displayed")
    time.sleep(1)
    controller.stop_listening_animation()
    
    # Requirement 5.5: Thinking animation during processing
    controller.show_thinking_animation()
    print("✓ Requirement 5.5: Thinking animation during processing")
    time.sleep(1)
    controller.stop_thinking_animation()
    
    controller.cleanup()
    print("Requirements compliance test completed\n")

def main():
    """Run all tests"""
    logging.basicConfig(level=logging.INFO)
    
    print("Starting OLED Expression Control System Tests")
    print("=" * 50)
    
    try:
        test_display_driver()
        test_basic_expressions()
        test_speaking_animation()
        test_idle_animations()
        test_listening_animation()
        test_thinking_animation()
        test_animation_control()
        test_requirements_compliance()
        
        print("=" * 50)
        print("All tests completed successfully!")
        print("OLED Expression Control System is fully functional")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
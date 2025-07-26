#!/usr/bin/env python3
"""
Expression Controller for AI Pet OLED Display
Manages facial expressions, animations, and emotional states
"""

import time
import math
import threading
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from PIL import Image, ImageDraw
import logging

from display_driver import DisplayDriver, DisplayConfig

@dataclass
class ExpressionConfig:
    """Configuration for expression animations"""
    eye_center_x: int = 32
    eye_center_y: int = 25
    eye_width: int = 20
    eye_height: int = 15
    eye_spacing: int = 64
    mouth_center_x: int = 64
    mouth_center_y: int = 45
    mouth_width: int = 30
    mouth_height: int = 8
    animation_fps: float = 10.0

class ExpressionController:
    """Manages OLED display animations and facial expressions synchronized with conversation states"""
    
    def __init__(self, display_driver: DisplayDriver = None, config: ExpressionConfig = None):
        self.display_driver = display_driver or DisplayDriver()
        self.config = config or ExpressionConfig()
        
        self.current_emotion = "neutral"
        self.is_speaking = False
        self.is_listening = False
        self.is_thinking = False
        
        self.idle_animation_thread = None
        self.idle_animation_running = False
        self.speaking_animation_thread = None
        self.speaking_animation_running = False
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize with neutral expression
        self.show_emotion("neutral")
    
    def _create_eyes(self, draw: ImageDraw.Draw, emotion: str, 
                    blink_state: float = 1.0, look_direction: Tuple[int, int] = (0, 0)) -> None:
        """Draw eyes based on emotion and state"""
        left_eye_x = self.config.eye_center_x
        right_eye_x = self.config.eye_center_x + self.config.eye_spacing
        eye_y = self.config.eye_center_y
        
        # Apply look direction offset
        left_eye_x += look_direction[0]
        right_eye_x += look_direction[0]
        eye_y += look_direction[1]
        
        eye_width = self.config.eye_width
        eye_height = int(self.config.eye_height * blink_state)
        
        if emotion == "happy":
            # Happy eyes - curved upward
            self._draw_happy_eyes(draw, left_eye_x, right_eye_x, eye_y, eye_width, eye_height)
        elif emotion == "sad":
            # Sad eyes - curved downward
            self._draw_sad_eyes(draw, left_eye_x, right_eye_x, eye_y, eye_width, eye_height)
        elif emotion == "surprised":
            # Wide open eyes
            self._draw_surprised_eyes(draw, left_eye_x, right_eye_x, eye_y, eye_width, eye_height)
        elif emotion == "confused":
            # Asymmetric eyes
            self._draw_confused_eyes(draw, left_eye_x, right_eye_x, eye_y, eye_width, eye_height)
        elif emotion == "thinking":
            # Slightly squinted eyes
            self._draw_thinking_eyes(draw, left_eye_x, right_eye_x, eye_y, eye_width, eye_height)
        else:  # neutral
            # Normal oval eyes
            self._draw_neutral_eyes(draw, left_eye_x, right_eye_x, eye_y, eye_width, eye_height)
    
    def _draw_neutral_eyes(self, draw: ImageDraw.Draw, left_x: int, right_x: int, 
                          y: int, width: int, height: int) -> None:
        """Draw neutral oval eyes"""
        # Left eye
        draw.ellipse([left_x - width//2, y - height//2, 
                     left_x + width//2, y + height//2], fill=1)
        # Right eye  
        draw.ellipse([right_x - width//2, y - height//2,
                     right_x + width//2, y + height//2], fill=1)
    
    def _draw_happy_eyes(self, draw: ImageDraw.Draw, left_x: int, right_x: int,
                        y: int, width: int, height: int) -> None:
        """Draw happy curved eyes"""
        # Happy eyes are arcs curving upward
        for eye_x in [left_x, right_x]:
            # Draw curved line for happy eye
            points = []
            for i in range(width):
                x = eye_x - width//2 + i
                curve_y = y + int(3 * math.sin(math.pi * i / width))
                points.append((x, curve_y))
            
            # Draw the curve
            for i in range(len(points) - 1):
                draw.line([points[i], points[i+1]], fill=1, width=2)
    
    def _draw_sad_eyes(self, draw: ImageDraw.Draw, left_x: int, right_x: int,
                      y: int, width: int, height: int) -> None:
        """Draw sad droopy eyes"""
        # Sad eyes droop downward
        for eye_x in [left_x, right_x]:
            # Draw droopy ellipse
            draw.ellipse([eye_x - width//2, y - height//4,
                         eye_x + width//2, y + height], fill=1)
    
    def _draw_surprised_eyes(self, draw: ImageDraw.Draw, left_x: int, right_x: int,
                           y: int, width: int, height: int) -> None:
        """Draw wide surprised eyes"""
        # Surprised eyes are larger circles
        radius = max(width, height) // 2 + 3
        draw.ellipse([left_x - radius, y - radius, left_x + radius, y + radius], fill=1)
        draw.ellipse([right_x - radius, y - radius, right_x + radius, y + radius], fill=1)
    
    def _draw_confused_eyes(self, draw: ImageDraw.Draw, left_x: int, right_x: int,
                           y: int, width: int, height: int) -> None:
        """Draw confused asymmetric eyes"""
        # Left eye normal
        draw.ellipse([left_x - width//2, y - height//2,
                     left_x + width//2, y + height//2], fill=1)
        # Right eye smaller and offset
        draw.ellipse([right_x - width//3, y - height//3 - 2,
                     right_x + width//3, y + height//3 - 2], fill=1)
    
    def _draw_thinking_eyes(self, draw: ImageDraw.Draw, left_x: int, right_x: int,
                           y: int, width: int, height: int) -> None:
        """Draw thinking squinted eyes"""
        # Squinted eyes - reduced height
        squint_height = max(2, height // 3)
        draw.ellipse([left_x - width//2, y - squint_height//2,
                     left_x + width//2, y + squint_height//2], fill=1)
        draw.ellipse([right_x - width//2, y - squint_height//2,
                     right_x + width//2, y + squint_height//2], fill=1)
    
    def _create_mouth(self, draw: ImageDraw.Draw, emotion: str, 
                     speaking_phase: float = 0.0) -> None:
        """Draw mouth based on emotion and speaking state"""
        mouth_x = self.config.mouth_center_x
        mouth_y = self.config.mouth_center_y
        mouth_width = self.config.mouth_width
        mouth_height = self.config.mouth_height
        
        if self.is_speaking:
            # Animate mouth for speaking
            open_amount = abs(math.sin(speaking_phase)) * 0.7 + 0.3
            mouth_height = int(mouth_height * open_amount)
            
            # Draw oval mouth opening
            draw.ellipse([mouth_x - mouth_width//2, mouth_y - mouth_height//2,
                         mouth_x + mouth_width//2, mouth_y + mouth_height//2], fill=1)
        else:
            # Static mouth based on emotion
            if emotion == "happy":
                # Smile - upward curve
                self._draw_smile(draw, mouth_x, mouth_y, mouth_width)
            elif emotion == "sad":
                # Frown - downward curve  
                self._draw_frown(draw, mouth_x, mouth_y, mouth_width)
            elif emotion == "surprised":
                # Open mouth - small circle
                draw.ellipse([mouth_x - 4, mouth_y - 6, mouth_x + 4, mouth_y + 6], fill=1)
            else:
                # Neutral - small line
                draw.line([mouth_x - mouth_width//4, mouth_y,
                          mouth_x + mouth_width//4, mouth_y], fill=1, width=2)
    
    def _draw_smile(self, draw: ImageDraw.Draw, x: int, y: int, width: int) -> None:
        """Draw a smile curve"""
        points = []
        for i in range(width):
            curve_x = x - width//2 + i
            curve_y = y - int(3 * math.sin(math.pi * i / width))
            points.append((curve_x, curve_y))
        
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=1, width=2)
    
    def _draw_frown(self, draw: ImageDraw.Draw, x: int, y: int, width: int) -> None:
        """Draw a frown curve"""
        points = []
        for i in range(width):
            curve_x = x - width//2 + i
            curve_y = y + int(3 * math.sin(math.pi * i / width))
            points.append((curve_x, curve_y))
        
        for i in range(len(points) - 1):
            draw.line([points[i], points[i+1]], fill=1, width=2)
    
    def show_emotion(self, emotion_type: str) -> None:
        """Display specific emotion expression"""
        self.current_emotion = emotion_type
        
        # Only stop animations if we're not already in the middle of stopping them
        if not hasattr(self, '_stopping_animations'):
            self._stopping_animations = True
            self.stop_all_animations()
            delattr(self, '_stopping_animations')
        
        # Create expression image
        img = self.display_driver.create_blank_image()
        draw = ImageDraw.Draw(img)
        
        # Draw face components
        self._create_eyes(draw, emotion_type)
        self._create_mouth(draw, emotion_type)
        
        # Draw special indicators for safety states
        if emotion_type in ["low_battery", "critical_battery"]:
            self._draw_battery_indicator(draw, emotion_type)
        elif emotion_type == "network_error":
            self._draw_network_indicator(draw)
        
        # Display the expression
        self.display_driver.draw_expression(img)
        
        self.logger.info(f"Showing emotion: {emotion_type}")
    
    def animate_speaking(self, duration: float) -> None:
        """Animate mouth movement for speaking"""
        self.is_speaking = True
        
        def speaking_worker():
            self.speaking_animation_running = True
            start_time = time.time()
            
            try:
                while (time.time() - start_time < duration and 
                       self.speaking_animation_running):
                    
                    # Calculate speaking phase
                    elapsed = time.time() - start_time
                    phase = elapsed * 8 * math.pi  # 4 Hz mouth movement
                    
                    # Create frame
                    img = self.display_driver.create_blank_image()
                    draw = ImageDraw.Draw(img)
                    
                    # Draw eyes (current emotion)
                    self._create_eyes(draw, self.current_emotion)
                    
                    # Draw animated mouth
                    self._create_mouth(draw, self.current_emotion, phase)
                    
                    # Display frame
                    self.display_driver.draw_expression(img)
                    
                    time.sleep(1.0 / self.config.animation_fps)
                    
            except Exception as e:
                self.logger.error(f"Speaking animation error: {e}")
            finally:
                self.is_speaking = False
                self.speaking_animation_running = False
                # Return to static expression without stopping animations
                img = self.display_driver.create_blank_image()
                draw = ImageDraw.Draw(img)
                self._create_eyes(draw, self.current_emotion)
                self._create_mouth(draw, self.current_emotion)
                self.display_driver.draw_expression(img)
        
        self.speaking_animation_thread = threading.Thread(target=speaking_worker, daemon=True)
        self.speaking_animation_thread.start()
    
    def show_listening_animation(self) -> None:
        """Show focused listening expression"""
        self.is_listening = True
        self.stop_idle_animation()
        
        # Create listening expression with focused eyes
        img = self.display_driver.create_blank_image()
        draw = ImageDraw.Draw(img)
        
        # Draw focused eyes (slightly larger)
        self._create_eyes(draw, "neutral", blink_state=1.0, look_direction=(0, -2))
        self._create_mouth(draw, "neutral")
        
        # Add listening indicator (small dots near ears)
        draw.ellipse([10, 20, 14, 24], fill=1)
        draw.ellipse([114, 20, 118, 24], fill=1)
        
        self.display_driver.draw_expression(img)
        self.logger.info("Showing listening animation")
    
    def show_thinking_animation(self) -> None:
        """Show thinking animation with moving dots"""
        self.is_thinking = True
        self.stop_idle_animation()
        
        def thinking_worker():
            try:
                dot_phase = 0
                while self.is_thinking:
                    img = self.display_driver.create_blank_image()
                    draw = ImageDraw.Draw(img)
                    
                    # Draw thinking eyes
                    self._create_eyes(draw, "thinking")
                    self._create_mouth(draw, "neutral")
                    
                    # Draw animated thinking dots
                    for i in range(3):
                        dot_x = 50 + i * 15
                        dot_y = 15 + int(3 * math.sin(dot_phase + i * 0.5))
                        draw.ellipse([dot_x, dot_y, dot_x + 4, dot_y + 4], fill=1)
                    
                    self.display_driver.draw_expression(img)
                    
                    dot_phase += 0.3
                    time.sleep(0.2)
                    
            except Exception as e:
                self.logger.error(f"Thinking animation error: {e}")
        
        thinking_thread = threading.Thread(target=thinking_worker, daemon=True)
        thinking_thread.start()
        
        self.logger.info("Showing thinking animation")
    
    def show_idle_animation(self) -> None:
        """Show idle blinking and breathing animation"""
        if self.idle_animation_running:
            return
            
        self.idle_animation_running = True
        
        def idle_worker():
            try:
                blink_timer = 0
                breath_timer = 0
                
                while self.idle_animation_running:
                    # Calculate blink state (blink every 3-5 seconds)
                    blink_timer += 0.1
                    if blink_timer > 4.0:  # Time to blink
                        blink_state = max(0, 1 - abs(blink_timer - 4.2) * 10)
                        if blink_timer > 4.4:
                            blink_timer = 0
                    else:
                        blink_state = 1.0
                    
                    # Calculate breathing effect
                    breath_timer += 0.1
                    breath_offset = int(2 * math.sin(breath_timer * 0.5))
                    
                    # Create frame
                    img = self.display_driver.create_blank_image()
                    draw = ImageDraw.Draw(img)
                    
                    # Draw eyes with blink and breath
                    self._create_eyes(draw, self.current_emotion, 
                                    blink_state, (0, breath_offset))
                    self._create_mouth(draw, self.current_emotion)
                    
                    self.display_driver.draw_expression(img)
                    
                    time.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"Idle animation error: {e}")
            finally:
                self.idle_animation_running = False
        
        self.idle_animation_thread = threading.Thread(target=idle_worker, daemon=True)
        self.idle_animation_thread.start()
        
        self.logger.info("Started idle animation")
    
    def stop_idle_animation(self) -> None:
        """Stop idle animation"""
        self.idle_animation_running = False
        if self.idle_animation_thread and self.idle_animation_thread.is_alive():
            self.idle_animation_thread.join(timeout=0.5)
    
    def stop_thinking_animation(self) -> None:
        """Stop thinking animation"""
        self.is_thinking = False
    
    def stop_listening_animation(self) -> None:
        """Stop listening animation"""
        self.is_listening = False
        # Don't call show_emotion here to avoid recursion
    
    def stop_speaking_animation(self) -> None:
        """Stop speaking animation"""
        self.speaking_animation_running = False
        if self.speaking_animation_thread and self.speaking_animation_thread.is_alive():
            self.speaking_animation_thread.join(timeout=0.5)
    
    def stop_all_animations(self) -> None:
        """Stop all running animations"""
        # Stop animations without triggering recursive calls
        self.idle_animation_running = False
        if (self.idle_animation_thread and 
            self.idle_animation_thread.is_alive() and 
            self.idle_animation_thread != threading.current_thread()):
            self.idle_animation_thread.join(timeout=0.5)
            
        self.is_thinking = False
        self.is_listening = False
        
        self.speaking_animation_running = False
        if (self.speaking_animation_thread and 
            self.speaking_animation_thread.is_alive() and 
            self.speaking_animation_thread != threading.current_thread()):
            self.speaking_animation_thread.join(timeout=0.5)
    
    def synchronize_mouth_with_tts(self, audio_duration: float) -> None:
        """Synchronize mouth animation with TTS audio output"""
        self.animate_speaking(audio_duration)
    
    def get_current_state(self) -> dict:
        """Get current expression state"""
        return {
            'emotion': self.current_emotion,
            'is_speaking': self.is_speaking,
            'is_listening': self.is_listening,
            'is_thinking': self.is_thinking,
            'idle_animation_running': self.idle_animation_running
        }
    
    def cleanup(self) -> None:
        """Cleanup expression controller"""
        self.stop_all_animations()
        self.display_driver.cleanup()
        self.logger.info("Expression controller cleanup completed")
    
    def _draw_battery_indicator(self, draw: ImageDraw.Draw, battery_type: str) -> None:
        """Draw battery level indicator"""
        try:
            # Battery outline position (top-right corner)
            battery_x = 100
            battery_y = 5
            battery_width = 20
            battery_height = 10
            
            # Draw battery outline
            draw.rectangle([battery_x, battery_y, 
                          battery_x + battery_width, battery_y + battery_height], 
                         outline=1, fill=0)
            
            # Draw battery terminal
            draw.rectangle([battery_x + battery_width, battery_y + 2,
                          battery_x + battery_width + 2, battery_y + battery_height - 2],
                         outline=1, fill=1)
            
            # Draw battery level based on type
            if battery_type == "low_battery":
                # Show 1/3 battery level
                fill_width = battery_width // 3
                draw.rectangle([battery_x + 1, battery_y + 1,
                              battery_x + fill_width, battery_y + battery_height - 1],
                             outline=0, fill=1)
            elif battery_type == "critical_battery":
                # Show flashing empty battery
                current_time = time.time()
                if int(current_time * 2) % 2:  # Flash every 0.5 seconds
                    # Draw exclamation mark in battery
                    center_x = battery_x + battery_width // 2
                    center_y = battery_y + battery_height // 2
                    draw.line([center_x, battery_y + 2, center_x, center_y], fill=1, width=1)
                    draw.point([center_x, center_y + 2], fill=1)
            
            self.logger.debug(f"Drew battery indicator: {battery_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to draw battery indicator: {e}")
    
    def _draw_network_indicator(self, draw: ImageDraw.Draw) -> None:
        """Draw network error indicator"""
        try:
            # Network icon position (top-left corner)
            net_x = 5
            net_y = 5
            
            # Draw WiFi-like icon with X
            # WiFi arcs
            draw.arc([net_x, net_y, net_x + 15, net_y + 15], 0, 180, fill=1)
            draw.arc([net_x + 3, net_y + 3, net_x + 12, net_y + 12], 0, 180, fill=1)
            
            # X mark to indicate no connection
            draw.line([net_x + 2, net_y + 2, net_x + 13, net_y + 13], fill=1, width=2)
            draw.line([net_x + 13, net_y + 2, net_x + 2, net_y + 13], fill=1, width=2)
            
            self.logger.debug("Drew network error indicator")
            
        except Exception as e:
            self.logger.error(f"Failed to draw network indicator: {e}")

if __name__ == "__main__":
    # Test the expression controller
    logging.basicConfig(level=logging.INFO)
    
    controller = ExpressionController()
    
    # Test different emotions
    emotions = ["neutral", "happy", "sad", "surprised", "confused", "thinking"]
    
    for emotion in emotions:
        print(f"Testing emotion: {emotion}")
        controller.show_emotion(emotion)
        time.sleep(2)
    
    # Test speaking animation
    print("Testing speaking animation")
    controller.animate_speaking(3.0)
    time.sleep(4)
    
    # Test idle animation
    print("Testing idle animation")
    controller.show_idle_animation()
    time.sleep(5)
    
    controller.cleanup()
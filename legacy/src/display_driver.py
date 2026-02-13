#!/usr/bin/env python3
"""
OLED Display Driver for SSD1306
Handles low-level display operations for the AI pet expression system
"""

import time
import threading
from typing import Optional, List, Tuple
from dataclasses import dataclass
from PIL import Image, ImageDraw, ImageFont
import logging

try:
    import board
    import digitalio
    from adafruit_ssd1306 import SSD1306_I2C
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    logging.warning("Hardware libraries not available. Running in simulation mode.")

@dataclass
class DisplayConfig:
    """Configuration for OLED display"""
    width: int = 128
    height: int = 64
    i2c_address: int = 0x3C
    reset_pin: Optional[int] = None

class DisplayDriver:
    """Low-level OLED display control for rendering expressions and animations"""
    
    def __init__(self, config: DisplayConfig = None):
        self.config = config or DisplayConfig()
        self.display = None
        self.current_image = None
        self.animation_thread = None
        self.animation_running = False
        self.brightness = 255
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize display
        self.initialize_display()
    
    def initialize_display(self) -> bool:
        """Initialize the SSD1306 OLED display"""
        try:
            if HARDWARE_AVAILABLE:
                # Initialize I2C and display
                i2c = board.I2C()
                
                # Setup reset pin if specified
                reset = None
                if self.config.reset_pin:
                    reset = digitalio.DigitalInOut(getattr(board, f'D{self.config.reset_pin}'))
                
                # Create display object
                self.display = SSD1306_I2C(
                    self.config.width, 
                    self.config.height, 
                    i2c, 
                    addr=self.config.i2c_address,
                    reset=reset
                )
                
                # Clear display
                self.display.fill(0)
                self.display.show()
                
                self.logger.info(f"OLED display initialized: {self.config.width}x{self.config.height}")
                return True
            else:
                self.logger.info("Running in simulation mode - no hardware display")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to initialize display: {e}")
            return False
    
    def create_blank_image(self) -> Image.Image:
        """Create a blank PIL image for drawing"""
        return Image.new('1', (self.config.width, self.config.height))
    
    def draw_expression(self, expression_data: Image.Image) -> bool:
        """Draw expression image to display"""
        try:
            if HARDWARE_AVAILABLE and self.display:
                # Convert PIL image to display buffer
                self.display.image(expression_data)
                self.display.show()
            
            # Store current image for reference
            self.current_image = expression_data.copy()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to draw expression: {e}")
            return False
    
    def animate_sequence(self, animation_frames: List[Image.Image], 
                        duration_per_frame: float = 0.1, 
                        loop_count: int = 1) -> None:
        """Animate a sequence of frames"""
        if self.animation_running:
            self.stop_animation()
        
        def animation_worker():
            self.animation_running = True
            try:
                for _ in range(loop_count):
                    if not self.animation_running:
                        break
                    
                    for frame in animation_frames:
                        if not self.animation_running:
                            break
                        
                        self.draw_expression(frame)
                        time.sleep(duration_per_frame)
                        
            except Exception as e:
                self.logger.error(f"Animation error: {e}")
            finally:
                self.animation_running = False
        
        self.animation_thread = threading.Thread(target=animation_worker, daemon=True)
        self.animation_thread.start()
    
    def stop_animation(self) -> None:
        """Stop current animation"""
        self.animation_running = False
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join(timeout=1.0)
    
    def clear_display(self) -> None:
        """Clear the display"""
        try:
            if HARDWARE_AVAILABLE and self.display:
                self.display.fill(0)
                self.display.show()
            
            # Create blank image
            self.current_image = self.create_blank_image()
            
        except Exception as e:
            self.logger.error(f"Failed to clear display: {e}")
    
    def set_brightness(self, level: int) -> None:
        """Set display brightness (0-255)"""
        self.brightness = max(0, min(255, level))
        
        try:
            if HARDWARE_AVAILABLE and self.display:
                # SSD1306 doesn't have direct brightness control
                # This would need to be implemented through contrast
                pass
                
        except Exception as e:
            self.logger.error(f"Failed to set brightness: {e}")
    
    def get_display_info(self) -> dict:
        """Get display information"""
        return {
            'width': self.config.width,
            'height': self.config.height,
            'hardware_available': HARDWARE_AVAILABLE,
            'initialized': self.display is not None,
            'brightness': self.brightness,
            'animation_running': self.animation_running
        }
    
    def cleanup(self) -> None:
        """Cleanup display resources"""
        self.stop_animation()
        self.clear_display()
        self.logger.info("Display driver cleanup completed")

if __name__ == "__main__":
    # Test the display driver
    logging.basicConfig(level=logging.INFO)
    
    driver = DisplayDriver()
    
    # Test basic functionality
    print("Display Info:", driver.get_display_info())
    
    # Create test image
    img = driver.create_blank_image()
    draw = ImageDraw.Draw(img)
    
    # Draw simple test pattern
    draw.rectangle([10, 10, 50, 50], fill=1)
    draw.text((60, 20), "TEST", fill=1)
    
    # Display test image
    driver.draw_expression(img)
    
    time.sleep(2)
    driver.cleanup()
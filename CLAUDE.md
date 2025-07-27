# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raspberry Pi-based AI-enabled robot control system (MCAR - Mobile Car AI Robot) that combines web interface control, voice commands, AI conversation, and autonomous behaviors. The robot supports multiple control modes: manual web control, Chinese voice commands, AI conversation mode, and automatic obstacle avoidance.

## Development Commands

### Installation and Setup
```bash
# Install system dependencies for voice control
cd src
chmod +x install_voice_dependencies.sh
./install_voice_dependencies.sh

# Install AI desktop pet system
chmod +x ../install_ai_desktop_pet.sh
../install_ai_desktop_pet.sh

# Setup API keys (requires manual configuration)
../setup_api_keys.sh
```

### Running the System
```bash
# Start the main web control system
cd src
python3 robot_voice_web_control.py

# Start with suppressed ALSA audio warnings
../start_ai_pet_quiet.sh

# Test individual components
python3 test_enhanced_voice_system.py     # Test voice system
python3 test_integration_suite.py         # Full integration tests
python3 test_ai_conversation.py           # Test AI conversation
```

### Testing Commands
```bash
# Quick system test
./quick_test.sh

# Test all components
./test_all_components.sh

# Hardware-specific tests
cd src
python3 test_hardware.py                  # GPIO and sensors
python3 test_camera.py                    # Camera functionality
python3 test_audio_simple.py              # Audio system
```

## Architecture

### Core Components

1. **Main Entry Point**: `src/robot_voice_web_control.py`
   - Flask web server providing REST APIs and WebSocket communication
   - Integrates all subsystems: robot control, voice, AI, sensors
   - Manages multiple threads for concurrent operations

2. **Hardware Control**: `src/LOBOROBOT.py`
   - Hardware abstraction layer for PCA9685 PWM motor controller
   - I2C communication via smbus library
   - Provides high-level movement commands (forward, backward, turn, etc.)

3. **Voice Control System**:
   - `src/voice_control.py`: Basic voice recognition using PocketSphinx
   - `src/enhanced_voice_control.py`: Advanced voice with wake word detection
   - `src/wake_word_detector.py`: Wake word detection using Picovoice Porcupine
   - `src/whisper_integration.py`: OpenAI Whisper for improved recognition
   - `src/vosk_recognizer.py`: Vosk offline speech recognition

4. **AI Conversation**: `src/ai_conversation.py`
   - Google Gemini AI integration for natural language conversations
   - Context-aware responses with robot state awareness
   - TTS output using edge-tts library

5. **Emotion & Personality**:
   - `src/emotion_engine.py`: Emotion state management
   - `src/personality_manager.py`: Personality traits and responses
   - `src/expression_controller.py`: Physical expression through movements

6. **Safety & Memory**:
   - `src/safety_manager.py`: Safety protocols and monitoring
   - `src/memory_manager.py`: Persistent conversation memory

### Hardware Integration

- **Motor Control**: PCA9685 I2C PWM driver for omnidirectional movement
- **Sensors**: 
  - HC-SR04 ultrasonic sensor (front obstacle detection)
  - IR sensors (left/right obstacle detection)
- **Audio**: USB microphone + speaker for voice interaction
- **Vision**: PiCamera or USB webcam for real-time video streaming
- **Display**: Optional OLED display for status information

### Web Interface

- **Frontend**: `src/templates/voice_index.html`
  - Bootstrap-based responsive UI
  - Virtual joystick control using NippleJS
  - Real-time video streaming
  - Voice control toggle and status indicators

## Configuration Files

- `src/ai_pet_config.json`: AI personality and behavior settings
- `src/data/ai_memory/user_config.json`: User preferences and memory
- `src/requirements.txt`: Python dependencies
- `requirements_*.txt`: Platform-specific dependency variants

## Dependencies

### System Requirements
- Raspberry Pi OS (recommended) or Ubuntu
- ALSA audio system
- I2C enabled for motor control
- Camera interface enabled

### Key Python Libraries
- `flask`: Web server framework
- `RPi.GPIO`: GPIO control for sensors
- `smbus`: I2C communication
- `opencv-python-headless`: Computer vision
- `SpeechRecognition`: Voice recognition
- `google-generativeai`: AI conversation
- `pvporcupine`: Wake word detection
- `edge-tts`: Text-to-speech synthesis

## Development Notes

### Audio System Setup
The project includes extensive audio troubleshooting scripts due to common ALSA/PulseAudio configuration issues on Raspberry Pi. Use the provided fix scripts if encountering audio problems.

### Testing Strategy
- Use `test_integration_*.py` files for comprehensive system testing
- Hardware tests require actual GPIO connections
- Many test files exist for debugging specific audio/voice issues

### AI Integration
- Requires Google Gemini API key configuration
- Memory system persists conversations in SQLite database
- Personality system affects response style and robot behaviors

### Safety Features
- Automatic timeout stops robot if no commands received
- Obstacle avoidance using sensor fusion
- Safety manager monitors system health

## Common Development Tasks

1. **Adding new voice commands**: Modify command recognition in `enhanced_voice_control.py`
2. **Customizing AI personality**: Edit `ai_pet_config.json` and `personality_manager.py`
3. **Adding new movements**: Extend `LOBOROBOT.py` movement methods
4. **Testing voice recognition**: Use `test_enhanced_voice_system.py` with actual microphone
5. **Debugging audio issues**: Run audio fix scripts in sequence (fix_alsa_*.sh)
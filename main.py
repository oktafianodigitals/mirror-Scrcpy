import sys
import subprocess
import os
import platform
import threading
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QTextEdit, QLineEdit, QComboBox, 
                           QCheckBox, QLabel, QFrame, QSplitter, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

class CommandThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    
    def __init__(self, command, cmd_prefix=""):
        super().__init__()
        self.command = command
        self.cmd_prefix = cmd_prefix
        self.process = None
        
    def run(self):
        try:
            # Prepend command prefix if the command starts with adb or scrcpy
            if re.match(r'^(adb|scrcpy)', self.command):
                full_command = f"{self.cmd_prefix}{self.command}"
                # If in scrcpy folder, navigate to it
                if os.path.isdir("scrcpy"):
                    full_command = f"cd scrcpy && {full_command}"
            else:
                full_command = self.command
                
            self.process = subprocess.Popen(
                full_command, shell=True, stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, text=True, bufsize=1, 
                universal_newlines=True
            )
            
            while True:
                line = self.process.stdout.readline()
                if not line and self.process.poll() is not None:
                    break
                if line:
                    self.output_signal.emit(line)
            
            # Check for errors
            stderr = self.process.stderr.read()
            if stderr:
                self.output_signal.emit(f"ERROR: {stderr}\n")
                
            return_code = self.process.wait()
            self.output_signal.emit(f"Command completed with return code: {return_code}\n")
            self.finished_signal.emit(return_code)
            
        except Exception as e:
            self.output_signal.emit(f"Exception: {str(e)}\n")
            self.finished_signal.emit(-1)
    
    def terminate_process(self):
        if self.process:
            try:
                if platform.system() == 'Windows':
                    subprocess.run(f"taskkill /F /T /PID {self.process.pid}", shell=True)
                else:
                    self.process.terminate()
                    self.process.wait(timeout=5)
            except:
                pass

class ScrcpyController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mirror v1.2")  # <- Ubah title di sini
        self.setWindowIcon(QIcon("scrcpy/icon.ico"))  # <- Tambahkan icon di sini
        self.setGeometry(100, 100, 1000, 700)
        
        # Detect OS and command prefix
        self.os_name = platform.system()
        self.cmd_prefix = '.\\' if self.os_name == 'Windows' else './'
        self.running_processes = []
        self.device_list = []
        
        # Check command prefix
        self.check_command_prefix()
        
        # Set up the UI
        self.init_ui()
        self.apply_dark_theme()
        
        
    def check_command_prefix(self):
        """Test whether we need to use .\ prefix for commands"""
        try:
            # Try without prefix first
            result = subprocess.run("adb --version", shell=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                self.cmd_prefix = ''
                return
            
            # Try with prefix
            result = subprocess.run(".\\adb --version", shell=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                self.cmd_prefix = '.\\'
                return
                
            # Default fallback
            self.cmd_prefix = '.\\' if self.os_name == 'Windows' else './'
            
        except Exception:
            # Default fallback
            self.cmd_prefix = '.\\' if self.os_name == 'Windows' else './'

    def init_ui(self):
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with splitter
        main_layout = QVBoxLayout(central_widget)
        splitter = QSplitter(Qt.Orientation.Vertical)
        main_layout.addWidget(splitter)
        
        # Top section - Scrcpy Configuration
        config_frame = self.create_config_section()
        splitter.addWidget(config_frame)
        
        # Middle section - Terminal Output
        terminal_frame = self.create_terminal_section()
        splitter.addWidget(terminal_frame)
        
        # Bottom section - Command Input and Controls
        control_frame = self.create_control_section()
        splitter.addWidget(control_frame)
        
        # Set splitter proportions
        splitter.setSizes([300, 300, 100])
        
    def create_config_section(self):
        group_box = QGroupBox("Scrcpy Configuration")
        group_box.setObjectName("configSection")
        layout = QGridLayout(group_box)
        
        # Bit Rate dropdown
        layout.addWidget(QLabel("Bit Rate:"), 0, 0)
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.addItems(["NONE", "4M", "8M", "12M", "16M", "24M"])
        self.bitrate_combo.setCurrentText("8M")
        layout.addWidget(self.bitrate_combo, 0, 1)
        
        # FPS dropdown
        layout.addWidget(QLabel("Max FPS:"), 0, 2)
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["NONE", "60", "90", "120", "144"])
        self.fps_combo.setCurrentText("90")
        layout.addWidget(self.fps_combo, 0, 3)
        
        # Window Title input
        layout.addWidget(QLabel("Window Title:"), 1, 0)
        self.window_title_input = QLineEdit()
        self.window_title_input.setText("POCO X5 5G")
        self.window_title_input.setPlaceholderText("Enter window title...")
        layout.addWidget(self.window_title_input, 1, 1, 1, 2)
        
        # Max Size dropdown
        layout.addWidget(QLabel("Max Size:"), 1, 3)
        self.maxsize_combo = QComboBox()
        self.maxsize_combo.addItems(["NONE", "1080", "1440", "1600", "1920", "2160"])
        self.maxsize_combo.setCurrentText("1600")
        layout.addWidget(self.maxsize_combo, 1, 4)
        
        # Show FPS checkbox
        self.show_fps_checkbox = QCheckBox("Show FPS")
        self.show_fps_checkbox.setChecked(True)
        layout.addWidget(self.show_fps_checkbox, 2, 0)
        
        # Device selection dropdown
        layout.addWidget(QLabel("Select Device:"), 2, 1)
        self.device_combo = QComboBox()
        self.device_combo.addItem("No devices detected")
        layout.addWidget(self.device_combo, 2, 2, 1, 2)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.test_device_btn = QPushButton("🔍 Test Devices")
        self.test_device_btn.setObjectName("testButton")
        self.test_device_btn.clicked.connect(self.test_devices)
        button_layout.addWidget(self.test_device_btn)
        
        self.start_btn = QPushButton("▶️ Start Scrcpy")
        self.start_btn.setObjectName("startButton")
        self.start_btn.clicked.connect(self.start_scrcpy)
        button_layout.addWidget(self.start_btn)
        
        self.run_sndcpy_btn = QPushButton("🔊 Run Audio")
        self.run_sndcpy_btn.setObjectName("audioButton")
        self.run_sndcpy_btn.clicked.connect(self.run_sndcpy)
        button_layout.addWidget(self.run_sndcpy_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop All")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.clicked.connect(self.stop_all_processes)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        layout.addLayout(button_layout, 3, 0, 1, 5)
        
        return group_box
    
    def create_terminal_section(self):
        group_box = QGroupBox("Terminal Output")
        group_box.setObjectName("terminalSection")
        layout = QVBoxLayout(group_box)
        
        self.terminal_output = QTextEdit()
        self.terminal_output.setObjectName("terminal")
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setFont(QFont("Consolas", 10))
        self.terminal_output.append("🚀 Scrcpy Controller Ready!")
        self.terminal_output.append("📱 Connect your Android device and click 'Test Devices' to begin.")
        
        layout.addWidget(self.terminal_output)
        
        return group_box
    
    def create_control_section(self):
        group_box = QGroupBox("Manual Command Input")
        group_box.setObjectName("controlSection")
        layout = QHBoxLayout(group_box)
        
        self.command_input = QLineEdit()
        self.command_input.setObjectName("commandInput")
        self.command_input.setPlaceholderText("Enter custom command here (e.g., adb devices, scrcpy --help)")
        self.command_input.returnPressed.connect(self.submit_command)
        layout.addWidget(self.command_input)
        
        self.submit_btn = QPushButton("📤 Submit")
        self.submit_btn.setObjectName("submitButton")
        self.submit_btn.clicked.connect(self.submit_command)
        layout.addWidget(self.submit_btn)
        
        return group_box
    
    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #ffffff;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3a3a3a;
                border-radius: 8px;
                margin-top: 1ex;
                padding: 10px;
                background-color: #2d2d2d;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #00d4aa;
            }
            
            #configSection {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #2d2d2d, stop: 1 #252525);
            }
            
            #terminalSection {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #1a1a1a, stop: 1 #0f0f0f);
            }
            
            #controlSection {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #2d2d2d, stop: 1 #252525);
            }
            
            #terminal {
                background-color: #0a0a0a;
                color: #00ff41;
                border: 2px solid #333333;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', monospace;
            }
            
            QLabel {
                color: #ffffff;
                font-weight: bold;
            }
            
            QComboBox {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 6px;
                min-width: 80px;
            }
            
            QComboBox:hover {
                border-color: #00d4aa;
                background-color: #404040;
            }
            
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left: 2px solid #555555;
                background-color: #4a4a4a;
            }
            
            QComboBox::down-arrow {
                width: 12px;
                height: 12px;
                background-color: #00d4aa;
            }
            
            QLineEdit {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 8px;
                font-size: 11px;
            }
            
            QLineEdit:focus {
                border-color: #00d4aa;
                background-color: #404040;
            }
            
            #commandInput {
                background-color: #2a2a2a;
                color: #00ff41;
                font-family: 'Consolas', monospace;
            }
            
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #4a4a4a, stop: 1 #3a3a3a);
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 11px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #5a5a5a, stop: 1 #4a4a4a);
                border-color: #00d4aa;
            }
            
            QPushButton:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #3a3a3a, stop: 1 #2a2a2a);
            }
            
            #startButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #00aa44, stop: 1 #008833);
            }
            
            #startButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #00cc55, stop: 1 #00aa44);
            }
            
            #stopButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #cc4444, stop: 1 #aa3333);
            }
            
            #stopButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #dd5555, stop: 1 #cc4444);
            }
            
            #testButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #4488cc, stop: 1 #3377bb);
            }
            
            #testButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #5599dd, stop: 1 #4488cc);
            }
            
            #audioButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #cc8844, stop: 1 #bb7733);
            }
            
            #audioButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #dd9955, stop: 1 #cc8844);
            }
            
            #submitButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #6644cc, stop: 1 #5533bb);
            }
            
            #submitButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                          stop: 0 #7755dd, stop: 1 #6644cc);
            }
            
            QCheckBox {
                color: #ffffff;
                font-weight: bold;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555555;
                border-radius: 4px;
                background-color: #3a3a3a;
            }
            
            QCheckBox::indicator:checked {
                background-color: #00d4aa;
                border-color: #00d4aa;
            }
            
            QCheckBox::indicator:hover {
                border-color: #00d4aa;
            }
        """)
    
    def write_to_terminal(self, text):
        """Write text to terminal output"""
        self.terminal_output.append(text.rstrip())
        self.terminal_output.ensureCursorVisible()
    
    def submit_command(self):
        """Execute command from input field"""
        command = self.command_input.text().strip()
        if not command:
            return
        
        self.write_to_terminal(f"💻 > {command}")
        self.command_input.clear()
        
        # Execute command in thread
        thread = CommandThread(command, self.cmd_prefix)
        thread.output_signal.connect(self.write_to_terminal)
        thread.finished_signal.connect(lambda code: self.write_to_terminal(f"✅ Command finished with code: {code}"))
        thread.start()
        self.running_processes.append(thread)
    
    def test_devices(self):
        """Test connected Android devices"""
        self.write_to_terminal("🔍 Testing connected devices...")
        
        # Create adb devices command
        if os.path.isdir("scrcpy"):
            adb_cmd = f"cd scrcpy && {self.cmd_prefix}adb devices"
        else:
            adb_cmd = f"{self.cmd_prefix}adb devices"
        
        thread = CommandThread(adb_cmd, self.cmd_prefix)
        thread.output_signal.connect(self.write_to_terminal)
        thread.finished_signal.connect(self.parse_devices)
        thread.start()
        self.running_processes.append(thread)
    
    def parse_devices(self, return_code):
        """Parse device list from adb devices output"""
        if return_code == 0:
            # Parse terminal output to extract device list
            terminal_text = self.terminal_output.toPlainText()
            lines = terminal_text.split('\n')
            
            devices = []
            for line in lines:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0].strip()
                    if device_id and device_id != "List of devices attached":
                        devices.append(device_id)
            
            self.device_combo.clear()
            if devices:
                self.device_combo.addItems(devices)
                self.write_to_terminal(f"📱 Found {len(devices)} device(s)")
            else:
                self.device_combo.addItem("No devices detected")
                self.write_to_terminal("❌ No devices found. Check USB debugging is enabled.")
    
    def build_scrcpy_command(self):
        """Build scrcpy command from UI selections"""
        command_parts = ["scrcpy"]
        
        # Video bit rate
        if self.bitrate_combo.currentText() != "NONE":
            command_parts.append(f"--video-bit-rate {self.bitrate_combo.currentText()}")
        
        # Max FPS
        if self.fps_combo.currentText() != "NONE":
            command_parts.append(f"--max-fps {self.fps_combo.currentText()}")
        
        # Window title
        window_title = self.window_title_input.text().strip()
        if window_title:
            command_parts.append(f'--window-title "{window_title}"')
        
        # Max size
        if self.maxsize_combo.currentText() != "NONE":
            command_parts.append(f"--max-size {self.maxsize_combo.currentText()}")
        
        # Render driver
        command_parts.append("--render-driver=opengl")
        
        # Show FPS
        if self.show_fps_checkbox.isChecked():
            command_parts.append("--print-fps")
        
        # Device selection - either USB or specific serial
        if (self.device_combo.currentText() != "No devices detected" and 
            self.device_combo.currentText()):
            command_parts.append(f"--serial={self.device_combo.currentText()}")
        else:
            command_parts.append("--select-usb")
        
        return " ".join(command_parts)
    
    def start_scrcpy(self):
        """Start scrcpy with configured options"""
        command = self.build_scrcpy_command()
        self.write_to_terminal(f"🚀 Starting: {command}")
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Run in scrcpy folder if it exists
        if os.path.isdir("scrcpy"):
            full_command = f"cd scrcpy && {self.cmd_prefix}{command}"
        else:
            full_command = f"{self.cmd_prefix}{command}"
        
        thread = CommandThread(full_command, self.cmd_prefix)
        thread.output_signal.connect(self.write_to_terminal)
        thread.finished_signal.connect(self.on_scrcpy_finished)
        thread.start()
        self.running_processes.append(thread)
    
    def on_scrcpy_finished(self, return_code):
        """Handle scrcpy process completion"""
        self.start_btn.setEnabled(True)
        if not self.running_processes:
            self.stop_btn.setEnabled(False)
        self.write_to_terminal(f"📱 Scrcpy finished with code: {return_code}")
    
    def run_sndcpy(self):
        """Run sndcpy in a separate terminal window"""
        self.write_to_terminal("🔊 Running sndcpy in separate terminal...")
        
        try:
            if self.os_name == 'Windows':
                if os.path.isdir("scrcpy"):
                    cmd = f'start cmd.exe /k "cd /d {os.path.abspath("scrcpy")} && {self.cmd_prefix}sndcpy.bat"'
                else:
                    cmd = f'start cmd.exe /k "{self.cmd_prefix}sndcpy.bat"'
            else:
                terminal_cmd = "xterm" if os.system("which xterm > /dev/null") == 0 else "gnome-terminal"
                
                if os.path.isdir("scrcpy"):
                    cmd = f'{terminal_cmd} -e "cd {os.path.abspath("scrcpy")} && {self.cmd_prefix}sndcpy.bat"'
                else:
                    cmd = f'{terminal_cmd} -e "{self.cmd_prefix}sndcpy.bat"'
            
            subprocess.Popen(cmd, shell=True)
            self.write_to_terminal("✅ sndcpy launched in separate terminal")
            
        except Exception as e:
            self.write_to_terminal(f"❌ Failed to launch sndcpy: {str(e)}")
    
    def stop_all_processes(self):
        """Stop all running processes including sndcpy"""
        self.write_to_terminal("⏹️ Stopping all processes...")
        
        # Stop scrcpy and other processes
        for thread in self.running_processes:
            if thread.isRunning():
                thread.terminate_process()
                thread.terminate()
        
        # Stop sndcpy processes
        try:
            if self.os_name == 'Windows':
                subprocess.run("taskkill /F /IM sndcpy.exe", shell=True, capture_output=True)
                subprocess.run("taskkill /F /IM scrcpy.exe", shell=True, capture_output=True)
            else:
                subprocess.run("pkill -f sndcpy", shell=True, capture_output=True)
                subprocess.run("pkill -f scrcpy", shell=True, capture_output=True)
        except:
            pass
        
        self.running_processes.clear()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.write_to_terminal("✅ All processes stopped")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Scrcpy Controller")
    
    window = ScrcpyController()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
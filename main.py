import sys
import os
import json
import winreg
import random
import datetime
from PyQt5.QtGui import QIcon, QMovie, QCursor, QPixmap

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state.json')
APP_NAME = 'MalteseDesktopPet'
from PyQt5.QtWidgets import (QWidget, QApplication, QSystemTrayIcon, 
                             QMenu, QAction, QLabel, QDesktopWidget,
                             QProgressBar, QVBoxLayout, QHBoxLayout,
                             QDialog)
from PyQt5.QtCore import Qt, QSize, QTimer, QPoint

class ClockDialog(QDialog):
    def __init__(self, message, parent=None):
        super(ClockDialog, self).__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        layout = QVBoxLayout()
        self.message_label = QLabel(message)
        self.message_label.setStyleSheet("""
            background-color: rgba(255, 255, 255, 225);
            border: 2px solid #FF69B4;
            border-radius: 10px;
            padding: 10px;
            color: #333;
            font-size: 14px;
        """)
        layout.addWidget(self.message_label)
        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close)
        self.timer.start(9500)

class DesktopPet(QWidget):
    def __init__(self, parent=None, **kwargs):
        super(DesktopPet, self).__init__(parent)
        self.init()
        self.initPall()
        self.action_timer = QTimer(self)
        self.action_timer.setSingleShot(True)
        self.action_timer.timeout.connect(self.checkInitialGif)
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.statusTimer)
        self.happiness_accumulated = 0
        self.energy_accumulated = 0
        self.working_timer = QTimer(self)
        self.working_timer.timeout.connect(self.updateWorking)
        self.boring_timer = QTimer(self)
        self.boring_timer.setSingleShot(True)
        self.boring_timer.timeout.connect(self.setBoring)
        self.is_boring = False
        self.resetBoringTimer()
        self.resurrect_timer = QTimer(self)
        self.resurrect_timer.setSingleShot(True)
        self.resurrect_timer.timeout.connect(self.resurrectPet)
        loaded = self.load_state()
        self._init_happiness, self._init_energy, self._init_is_dead, self._init_resurrect_ms, self._init_stats_visible = loaded
        self.is_dead = self._init_is_dead
        self.hour_timer = QTimer(self)
        self.hour_timer.timeout.connect(self.hourAlert)
        self.hour_timer.start(1000)
        self.last_hour = -1
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.save_state)
        self.save_timer.start(5 * 60 * 1000)
        self.initPetImage()
        
    def init(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.repaint()
        
    def initPall(self):
        icons = os.path.join('Image/MenuIcon.jpg')
        self.quit_action = QAction(u'退出', self, triggered=self.quit)
        self.showing = QAction(u'显示', self, triggered=self.showup)
        self.hideup = QAction(u'隐藏', self, triggered=self.hide)
        self.hidestats = QAction(u'显示/隐藏状态栏', self, triggered=self.hideStatsBar)
        self.tray_icon_menu = QMenu(self)
        self.tray_icon_menu.setStyleSheet("""
            QMenu {
                background-color: #FFFAF9;
                border: 1.5px solid #FF69B4;
                padding: 5px 3px;
                font-family: "幼圆", "YouYuan", "Microsoft YaHei";
                font-size: 13px;
                color: #555555;
            }
            QMenu::item {
                padding: 6px 22px 6px 14px;
                border-radius: 6px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #FFE2DE;
                color: #FF69B4;
            }
            QMenu::separator {
                height: 1px;
                background-color: #FFD6E7;
                margin: 4px 8px;
            }
        """)
        self.autostart_action = QAction(u'开机自启动', self)
        self.autostart_action.setCheckable(True)
        self.autostart_action.setChecked(self.is_autostart_enabled())
        self.autostart_action.triggered.connect(self.toggleAutostart)
        self.tray_icon_menu.addAction(self.quit_action)
        self.tray_icon_menu.addAction(self.showing)
        self.tray_icon_menu.addAction(self.hideup)
        self.tray_icon_menu.addAction(self.hidestats)
        self.tray_icon_menu.addAction(self.autostart_action)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icons))
        self.tray_icon.setContextMenu(self.tray_icon_menu)
        self.tray_icon.show()
        
    def initPetImage(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.normal_form = random.random()
        
        self.stats_visible = True
        self.happiness_layout = QHBoxLayout()
        self.happiness_layout.setContentsMargins(0, 0, 0, 0)
        self.happiness_layout.setSpacing(0)
        self.happiness_icon = QLabel()
        self.happiness_icon.setContentsMargins(0, 0, 0, 0)
        self.happiness_icon_pixmap = QPixmap("Image/Happiness.svg")
        self.happiness_icon_pixmap = self.happiness_icon_pixmap.scaled(QSize(20, 20), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.happiness_icon.setPixmap(self.happiness_icon_pixmap)
        self.happiness_layout.addWidget(self.happiness_icon, alignment=Qt.AlignCenter)
        self.happiness_bar = QProgressBar()
        self.happiness_bar.setRange(0, 100)
        self.happiness_bar.setValue(self._init_happiness)
        self.happiness_bar.setTextVisible(False)
        self.happiness_bar.setFixedHeight(16)
        self.happiness_bar.setFixedWidth(150)
        self.happiness_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 8px;
            }
            QProgressBar::chunk {
                background-color: #FF69B4;
                border-radius: 8px;
            }
        """)
        self.happiness_layout.addWidget(self.happiness_bar, alignment=Qt.AlignCenter)
        self.happiness_pct_label = QLabel(f"{self._init_happiness}%")
        self.happiness_pct_label.setStyleSheet("""
            font-family: "幼圆", "YouYuan", "Microsoft YaHei";
            font-size: 13px;
            color: #FF69B4;
        """)
        self.happiness_layout.addWidget(self.happiness_pct_label, alignment=Qt.AlignCenter)

        self.energy_layout = QHBoxLayout()
        self.energy_layout.setContentsMargins(0, 0, 0, 0)
        self.energy_layout.setSpacing(0)
        self.energy_label = QLabel()
        self.energy_label.setContentsMargins(0, 0, 0, 0)
        self.energy_icon_pixmap = QPixmap("Image/Energy.svg")
        self.energy_icon_pixmap = self.energy_icon_pixmap.scaled(QSize(20, 20), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.energy_label.setPixmap(self.energy_icon_pixmap)
        self.energy_layout.addWidget(self.energy_label, alignment=Qt.AlignCenter)
        self.energy_bar = QProgressBar()
        self.energy_bar.setRange(0, 100)
        self.energy_bar.setValue(self._init_energy)
        self.energy_bar.setTextVisible(False)
        self.energy_bar.setFixedHeight(16)
        self.energy_bar.setFixedWidth(150)
        self.energy_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 8px;
            }
            QProgressBar::chunk {
                background-color: #1E90FF;
                border-radius: 8px;
            }
        """)
        self.energy_layout.addWidget(self.energy_bar, alignment=Qt.AlignCenter)
        self.energy_pct_label = QLabel(f"{self._init_energy}%")
        self.energy_pct_label.setStyleSheet("""
            font-family: "幼圆", "YouYuan", "Microsoft YaHei";
            font-size: 13px;
            color: #77cbf6;
        """)
        self.energy_layout.addWidget(self.energy_pct_label, alignment=Qt.AlignCenter)
        
        self.image = QLabel(self)
        self.image.setContentsMargins(0, 0, 0, 0)
        self.checkInitialGif()
        
        self.main_layout.addWidget(self.image)
        self.main_layout.addLayout(self.happiness_layout)
        self.main_layout.addLayout(self.energy_layout)
        
        self.resize(200, 240)
        self.randomPosition()
        self.show()
        self.pet1 = []
        for filename in os.listdir("GIF"):
            self.pet1.append(os.path.join("GIF", filename))
        if not self._init_stats_visible:
            self.stats_visible = True
            self.hideStatsBar()
        if self._init_is_dead:
            self.working_timer.stop()
            self.boring_timer.stop()
            self.action_timer.stop()
            self.status_timer.stop()
            self.showing.setEnabled(False)
            self.hidestats.setEnabled(False)
            self.hideup.setEnabled(False)
            self.hide()
            self.resurrect_timer.start(self._init_resurrect_ms)

    def showMenu(self):
        menu_style = """
            QMenu {
                background-color: #FFFAF9;
                border: 1.5px solid #FF69B4;
                padding: 5px 3px;
                font-family: "幼圆", "YouYuan", "Microsoft YaHei";
                font-size: 13px;
                color: #555555;
            }
            QMenu::item {
                padding: 6px 22px 6px 14px;
                border-radius: 6px;
                margin: 2px 4px;
            }
            QMenu::item:selected {
                background-color: #FFE2DE;
                color: #FF69B4;
            }
            QMenu::separator {
                height: 1px;
                background-color: #FFD6E7;
                margin: 4px 8px;
            }
        """
        menu = QMenu()
        menu.setStyleSheet(menu_style)
        menu.addAction(u"贴贴", self.stick)
        menu.addAction(u"拍一拍", self.call)
        menu.addAction(u"锻炼", self.exercise)
        menu.addAction(u"充电", self.charge)
        menu.addAction(u"投喂小白", self.cake)
        menu.addAction(u"吧唧", self.baji)
        menu.addAction(u"鸡毛丸子", self.baji2)
        menu.addAction(u"随机出现", self.appear)
        menu.addAction(u"遛小鸡毛", self.walkDog)
        menu.addSeparator()
        status_menu = menu.addMenu(u"状态切换")
        status_menu.addAction(u"显示", self.showup)
        status_menu.addAction(u"隐藏", self.hide)
        status_menu.addAction(u"显示/隐藏状态栏", self.hideStatsBar)
        autostart_action = QAction(u"开机自启动", menu)
        autostart_action.setCheckable(True)
        autostart_action.setChecked(self.is_autostart_enabled())
        autostart_action.triggered.connect(self.toggleAutostart)
        status_menu.addAction(autostart_action)
        status_menu.addSeparator()
        status_menu.addAction(u"关闭应用", self.quit)
        right_pos = self.mapToGlobal(self.rect().topRight())
        menu.exec_(right_pos)

    def stick(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        self.changeGif("GIF/stick.gif")
        self.action_timer.start(10 * 60 * 1000)
        self.updateStatus(15, -5, 10 * 60 * 1000)
        
    def call(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        self.changeGif("GIF/call.gif")
        self.action_timer.start(2000)
        
    def exercise(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        self.changeGif("GIF/exercise.gif")
        self.action_timer.start(10 * 60 * 1000)
        self.updateStatus(5, -15, 10 * 60 * 1000)
        
    def charge(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        self.changeGif("GIF/charge.gif")
        self.action_timer.start(60 * 60 * 1000)
        self.updateStatus(30, 30, 30 * 60 * 1000)
    
    def cake(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        if self.energy_bar.value() >= 80:
            self.changeGif("GIF/full.gif")
            self.action_timer.start(5 * 1000)
        else:
            self.changeGif("GIF/cake.gif")
            self.action_timer.start(5 * 60 * 1000)
            self.updateStatus(10, 5, 5 * 60 * 1000)
        
    def baji(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        self.changeGif("GIF/baji.gif")
        self.action_timer.start(5 * 60 * 1000)
        self.updateStatus(10, 0, 5 * 60 * 1000)
        
    def appear(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        self.changeGif("GIF/appear.gif")
        self.action_timer.start(3500)
        self.randomPosition()
    
    def walkDog(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        self.changeGif("GIF/walkdog.gif")
        self.action_timer.start(10 * 60 * 1000)
        self.updateStatus(15, -10, 10 * 60 * 1000)
        
    def baji2(self):
        if self.is_dead:
            return
        self.resetBoringTimer()
        self.working_timer.stop()
        self.changeGif("GIF/baji2.gif")
        self.action_timer.start(5 * 60 * 1000)
        self.updateStatus(15, -10, 5 * 60 * 1000)

    def checkInitialGif(self):
        current_time = datetime.datetime.now()
        current_hour = current_time.hour
        weekday = current_time.weekday()
        self.is_working_time = (0 <= weekday <= 4) and (10 <= current_hour < 18)
        happiness = self.happiness_bar.value()
        energy = self.energy_bar.value()
        
        if happiness == 0 and energy == 0:
            self.petDied()
        elif happiness < 20 and energy < 20:
            if self.is_working_time:
                self.working_timer.stop()
            self.working_timer.start(60 * 1000)
            return self.changeGif("GIF/angry.gif")
        elif happiness < 20:
            if self.is_working_time:
                self.working_timer.stop()
            self.working_timer.start(2 * 60 * 1000)
            return self.changeGif("GIF/crying2.gif")
        elif energy < 20:
            if self.is_working_time:
                self.working_timer.stop()
            self.working_timer.start(2 * 10 * 1000)
            return self.changeGif("GIF/crying.gif")
        elif energy >= 20 and energy < 40:
            return self.changeGif("GIF/hungry.gif")
        
        if self.is_working_time:
            self.working_timer.start(3 * 60 * 1000)
            return self.changeGif("GIF/working2.gif")
        else:
            self.working_timer.stop()
            if self.normal_form < 0.5:
                return self.changeGif("GIF/normal.gif")
            else:
                return self.changeGif("GIF/normal2.gif")
        
    def updateWorking(self):
        self.updateHappiness(-1)
        self.updateEnergy(-1)
        if self.happiness_bar.value() <= 20 or self.energy_bar.value() <= 20:
            self.checkInitialGif()
        
    def updateStatus(self, happinesschange, energychange, duration):
        self.total_happiness_change = happinesschange
        self.total_energy_change = energychange
        interval = 100
        self.remaining = duration / interval
        self.happiness_change_step = happinesschange / self.remaining
        self.energy_change_step = energychange / self.remaining
        self.status_timer.start(interval)
        
    def statusTimer(self):
        if self.remaining <= 0:
            self.status_timer.stop()
            return
        self.happiness_accumulated += self.happiness_change_step
        self.energy_accumulated += self.energy_change_step
        if self.happiness_accumulated >= 1 or self.happiness_accumulated <= -1:
            self.updateHappiness(int(self.happiness_accumulated))
            self.happiness_accumulated = 0
        if self.energy_accumulated >= 1 or self.energy_accumulated <= -1:
            self.updateEnergy(int(self.energy_accumulated))
            self.energy_accumulated = 0
        self.remaining -= 1
        
    def setBoring(self):
        if not self.is_boring and not self.is_working_time:
            self.is_boring = True
            self.changeGif("GIF/boring.gif")
            self.updateHappiness(-5)
            
    def resetBoringTimer(self):
        if self.is_boring:
            self.is_boring = False
            self.checkInitialGif()
        self.boring_timer.stop()
        self.boring_timer.start(60 * 60 * 1000)
        
    def petDied(self):
        if self.is_dead:
            return
        self.is_dead = True
        self.death_time = datetime.datetime.now()
        self.working_timer.stop()
        self.boring_timer.stop()
        self.action_timer.stop()
        self.status_timer.stop()
        self.showing.setEnabled(False)
        self.hidestats.setEnabled(False)
        self.hideup.setEnabled(False)
        self.hide()
        self.resurrect_timer.start(30 * 60 * 1000)
        
    def resurrectPet(self):
        self.is_dead = False
        self.happiness_bar.setValue(30)
        self.happiness_pct_label.setText("30%")
        self.energy_bar.setValue(30)
        self.energy_pct_label.setText("30%")
        self.showing.setEnabled(True)
        self.hidestats.setEnabled(True)
        self.hideup.setEnabled(True)
        self.showup()
        self.resetBoringTimer()
        self.checkInitialGif()
        
    def hourAlert(self):
        if self.is_dead or self.action_timer.isActive():
            return
        current_time = datetime.datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        if current_minute == 0 and current_hour != self.last_hour:
            self.last_hour = current_hour
            self.working_timer.stop()
            self.changeGif("GIF/clock.gif")
            self.clock_dialog = ClockDialog(
                message=f"现在是北京时间 {current_hour} 点整噢！",
                parent=self
            )
            self.clock_dialog.move(self.updateDialogPosition())
            self.clock_dialog.show()
            self.action_timer.start(9500)
            
    def randomPosition(self):
        screen_geometry = QDesktopWidget().screenGeometry()
        pet_geometry = self.geometry()
        width = int((screen_geometry.width() - pet_geometry.width()) * random.random())
        height  = int((screen_geometry.height() - pet_geometry.height()) * random.random())
        self.move(width, height)
        
    def changeGif(self, path):
        self.movie = QMovie(path)
        self.movie.setScaledSize(QSize(200, 200))
        self.image.setMovie(self.movie)
        self.movie.start()
        
    def mousePressEvent(self, event):
        self.condition = 1
        if event.button() == Qt.LeftButton:
            self.is_follow_mouse = True
            self.mouse_drag_pos = event.globalPos() - self.pos()
            self.setCursor(QCursor(Qt.OpenHandCursor))
        elif event.button() == Qt.RightButton:
            self.showMenu()
        event.accept()
 
    def mouseMoveEvent(self, event):
        if Qt.LeftButton and self.is_follow_mouse:
            self.move(event.globalPos() - self.mouse_drag_pos)
            if hasattr(self, 'clock_dialog') and self.clock_dialog.isVisible():
                self.clock_dialog.move(self.updateDialogPosition())
        event.accept()
 
    def mouseReleaseEvent(self, event):
        self.is_follow_mouse = False
        self.setCursor(QCursor(Qt.ArrowCursor))
 
    def enterEvent(self, event):
        self.setCursor(Qt.ClosedHandCursor)
        
    def updateHappiness(self, value):
        current_value = self.happiness_bar.value()
        new_value = max(0, min(100, current_value + value))
        self.happiness_bar.setValue(new_value)
        self.happiness_pct_label.setText(f"{new_value}%")

    def updateEnergy(self, value):
        current_value = self.energy_bar.value()
        new_value = max(0, min(100, current_value + value))
        self.energy_bar.setValue(new_value)
        self.energy_pct_label.setText(f"{new_value}%")
        
    def hideStatsBar(self):
        if self.is_dead:
            return
        self.stats_visible = not self.stats_visible
        self.happiness_icon.setVisible(self.stats_visible)
        self.happiness_bar.setVisible(self.stats_visible)
        self.happiness_pct_label.setVisible(self.stats_visible)
        self.energy_label.setVisible(self.stats_visible)
        self.energy_bar.setVisible(self.stats_visible)
        self.energy_pct_label.setVisible(self.stats_visible)
        
    def updateDialogPosition(self):
        screen = QDesktopWidget().screenGeometry()
        screen_width = screen.width()
        screen_height = screen.height()
        pet_pos = self.pos()
        pet_width = self.width()
        pet_height = self.height()
        if hasattr(self, 'clock_dialog'):
            dialog_width = self.clock_dialog.width()
            dialog_height = self.clock_dialog.height()
        x = pet_pos.x() + pet_width // 2
        y = pet_pos.y()
        if x + dialog_width > screen_width:
            x = pet_pos.x() - dialog_width // 2
        if y < 0:
            y = 0
        return QPoint(x, y)
        
    def load_state(self):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
            happiness = state.get('happiness', 80)
            energy = state.get('energy', 80)
            is_dead = state.get('is_dead', False)
            death_time_str = state.get('death_time')
            stats_visible = state.get('stats_visible', True)
            remaining_ms = 0
            if is_dead and death_time_str:
                death_time = datetime.datetime.fromisoformat(death_time_str)
                elapsed = (datetime.datetime.now() - death_time).total_seconds()
                if elapsed >= 30 * 60:
                    is_dead = False
                    happiness = 30
                    energy = 30
                else:
                    remaining_ms = int((30 * 60 - elapsed) * 1000)
            return happiness, energy, is_dead, remaining_ms, stats_visible
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return 80, 80, False, 0, True

    def save_state(self):
        state = {
            'happiness': self.happiness_bar.value(),
            'energy': self.energy_bar.value(),
            'is_dead': self.is_dead,
            'death_time': self.death_time.isoformat() if self.is_dead and hasattr(self, 'death_time') else None,
            'stats_visible': self.stats_visible,
        }
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False)

    def is_autostart_enabled(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r'Software\Microsoft\Windows\CurrentVersion\Run',
                                 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except (FileNotFoundError, OSError):
            return False

    def set_autostart(self, enabled):
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r'Software\Microsoft\Windows\CurrentVersion\Run',
                             0, winreg.KEY_WRITE)
        if enabled:
            script = os.path.abspath(__file__)
            python = sys.executable
            if python.lower().endswith('python.exe'):
                pythonw = python[:-len('python.exe')] + 'pythonw.exe'
                if os.path.exists(pythonw):
                    python = pythonw
            cmd = f'"{python}" "{script}"'
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)

    def toggleAutostart(self):
        self.set_autostart(not self.is_autostart_enabled())
        if hasattr(self, 'autostart_action'):
            self.autostart_action.setChecked(self.is_autostart_enabled())

    def quit(self):
        self.save_state()
        self.close()
        sys.exit()
        
    def showup(self):
        self.setWindowOpacity(1)
        
    def hide(self):
        self.setWindowOpacity(0)

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    app = QApplication(sys.argv)
    pet = DesktopPet()
    sys.exit(app.exec_())
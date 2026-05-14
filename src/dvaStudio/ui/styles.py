APP_QSS = """
* { font-family: 'Segoe UI', 'Inter', Arial; color: #F7F8FF; }
QMainWindow { background: #070A16; }
QWidget#Root { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #070A16, stop:0.55 #0D1024, stop:1 #130B22); }
QFrame#Sidebar { background: rgba(255,255,255,0.055); border: 1px solid rgba(255,255,255,0.08); border-radius: 24px; }
QFrame#Card { background: rgba(255,255,255,0.075); border: 1px solid rgba(255,255,255,0.10); border-radius: 22px; }
QLabel#AppTitle { font-size: 25px; font-weight: 800; letter-spacing: 0.5px; }
QLabel#Muted { color: #AAB0C5; font-size: 12px; }
QLabel#SectionTitle { font-size: 22px; font-weight: 800; }
QPushButton { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: 15px; padding: 11px 16px; font-weight: 700; }
QPushButton:hover { background: rgba(255,255,255,0.14); border: 1px solid rgba(32,227,255,0.38); }
QPushButton:pressed { background: rgba(32,227,255,0.16); }
QPushButton#Primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #20E3FF, stop:0.55 #8F3DFF, stop:1 #FF2FB3); color: white; border: none; }
QPushButton#Primary:hover { opacity: 0.95; }
QPushButton#NavButton { text-align: left; padding: 13px 18px; border-radius: 16px; background: transparent; border: none; color: #B7BDD1; }
QPushButton#NavButton:checked { background: rgba(32,227,255,0.14); color: white; border: 1px solid rgba(32,227,255,0.32); }
QLineEdit, QComboBox { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.13); border-radius: 16px; padding: 12px 14px; selection-background-color: #8F3DFF; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #20E3FF; }
QComboBox { background: #FFFFFF; color: #111111; }
QComboBox QAbstractItemView { background: #FFFFFF; color: #111111; selection-background-color: #8F3DFF; selection-color: #FFFFFF; }
QProgressBar { background: rgba(255,255,255,0.08); border: none; border-radius: 9px; height: 18px; text-align: center; color: white; font-weight: 700; }
QProgressBar::chunk { border-radius: 9px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #20E3FF, stop:1 #FF2FB3); }
QListWidget { background: transparent; border: none; }
QListWidget::item { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 14px; margin: 7px; }
QTabWidget::pane { border: none; }
"""

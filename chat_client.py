import socket
import sys
import time
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QMessageBox, QHBoxLayout, QInputDialog,
    QComboBox, QListWidget
)
from PyQt5.QtCore import QThread, pyqtSignal

HOST = '127.0.0.1'
PORT = 10346


class ServerMonitorThread(QThread):
    server_down = pyqtSignal()

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True
        self.was_online = False

    def run(self):
        while self.running:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1.0)
                result = sock.connect_ex((self.host, self.port))
                sock.close()

                if result == 0:
                    self.was_online = True
                else:
                    if self.was_online:
                        self.server_down.emit()
                        break
            except:
                if self.was_online:
                    self.server_down.emit()
                    break
            time.sleep(1)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class ReceiveThread(QThread):
    new_message = pyqtSignal(str)
    connection_closed = pyqtSignal()

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.running = True

    def run(self):
        while self.running:
            try:
                data = self.client.recv(1024)
                if not data:
                    self.connection_closed.emit()
                    break
                msg = data.decode('utf-8')
                self.new_message.emit(msg)
                if msg == "SHUTDOWN":
                    self.running = False
            except:
                self.connection_closed.emit()
                break

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class Client(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyChat Multi-Temas Client")
        self.resize(900, 600)
        self._apply_styles()

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receive_thread = None
        self.nickname = None
        self._setup_ui()
        self._show_initial_instruction()

        self.monitor_thread = ServerMonitorThread(HOST, PORT)
        self.monitor_thread.server_down.connect(self.on_server_shutdown)
        self.monitor_thread.start()

    def _show_initial_instruction(self):
        instruction = (
            "<div style='color: #3498db; font-size: 13px; line-height: 1.6;'>"
            "<b>[ORIENTAÇÃO DE CONEXÃO]</b><br>"
            "Para entrar na sala de bate-papo:<br>"
            "1. Insira seu apelido no campo <b>Nickname</b> na barra superior (canto esquerdo).<br>"
            "2. Se for o usuário <b>Admin</b>, preencha também o campo de <b>Senha</b>.<br>"
            "3. Clique no botão verde <b>Conectar</b> para iniciar a sessão."
            "</div>"
        )
        self.chat_display.setHtml(instruction)

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #12131b;
                color: #e1e1e6;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLineEdit {
                background-color: #1e1f2c;
                border: 1px solid #2a2c3d;
                border-radius: 16px;
                padding: 8px 15px;
                color: #ffffff;
            }
            QLineEdit:focus {
                border: 1px solid #5865f2;
            }
            QTextEdit {
                background-color: #191a24;
                border: 1px solid #27293a;
                border-radius: 12px;
                color: #ffffff;
                padding: 10px;
                font-size: 13px;
            }
            QListWidget {
                background-color: #191a24;
                border: 1px solid #27293a;
                border-radius: 12px;
                color: #2ecc71;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton {
                font-weight: bold;
                border-radius: 18px;
                padding: 8px 16px;
            }
            QPushButton#btnSend {
                background-color: #5865f2;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 22px;
            }
            QPushButton#btnSend:hover {
                background-color: #4752c4;
            }
            QPushButton#btnRecord {
                background-color: #f35543;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 10px 22px;
            }
            QPushButton#btnRecord:hover {
                background-color: #d94332;
            }
            QPushButton#btnFile {
                background-color: #262838;
                color: white;
                border: 1px solid #363950;
                border-radius: 20px;
                padding: 10px 22px;
            }
            QPushButton#btnFile:hover {
                background-color: #313448;
            }
            QPushButton#btnConnect {
                background-color: #2ecc71;
                color: white;
                border-radius: 8px;
                padding: 4px 10px;
            }
            QComboBox {
                background-color: #1e1f2c;
                border: 1px solid #2d3045;
                border-radius: 6px;
                padding: 4px 8px;
                color: white;
            }
        """)

    def _setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        header_layout = QHBoxLayout()

        self.nick_input = QLineEdit()
        self.nick_input.setPlaceholderText("Nickname")
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Senha (apenas admin)")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.connect_button = QPushButton("Conectar")
        self.connect_button.setObjectName("btnConnect")
        self.connect_button.clicked.connect(self.start_connection)

        status_label = QLabel("Status:")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Online", "Ausente", "Ocupado"])

        btn_options = QPushButton("Opções")
        btn_options.setFlat(True)
        btn_folder = QPushButton("Pasta")
        btn_folder.setFlat(True)

        header_layout.addWidget(QLabel("Usuário:"))
        header_layout.addWidget(self.nick_input)
        header_layout.addWidget(self.pass_input)
        header_layout.addWidget(self.connect_button)
        header_layout.addWidget(status_label)
        header_layout.addWidget(self.status_combo)
        header_layout.addStretch()
        header_layout.addWidget(btn_options)
        header_layout.addWidget(btn_folder)

        body_layout = QHBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)

        users_panel = QVBoxLayout()
        users_title = QLabel("ONLINE")
        users_title.setStyleSheet("font-weight: bold; color: #8e9297; font-size: 11px;")
        self.users_list = QListWidget()

        users_container = QWidget()
        users_container.setLayout(users_panel)
        users_panel.addWidget(users_title)
        users_panel.addWidget(self.users_list)
        users_panel.setContentsMargins(0, 0, 0, 0)

        body_layout.addWidget(self.chat_display, stretch=3)
        body_layout.addWidget(users_container, stretch=1)

        msg_input_layout = QHBoxLayout()

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Digite sua mensagem (ou 'q' para sair)...")
        self.msg_input.returnPressed.connect(self.send_message)

        self.btn_record = QPushButton("Gravar")
        self.btn_record.setObjectName("btnRecord")

        self.btn_file = QPushButton("Arquivo")
        self.btn_file.setObjectName("btnFile")

        self.send_button = QPushButton("Enviar Geral")
        self.send_button.setObjectName("btnSend")
        self.send_button.clicked.connect(self.send_message)

        msg_input_layout.addWidget(self.msg_input, stretch=1)
        msg_input_layout.addWidget(self.btn_record)
        msg_input_layout.addWidget(self.btn_file)
        msg_input_layout.addWidget(self.send_button)

        self.tip_label = QLabel("Comandos Admin: /kick NOME, /ban NOME, /unban NOME")
        self.tip_label.setStyleSheet("color: #72767d; font-size: 11px;")

        main_layout.addLayout(header_layout)
        main_layout.addLayout(body_layout)
        main_layout.addLayout(msg_input_layout)
        main_layout.addWidget(self.tip_label)
        self.setLayout(main_layout)

    def start_connection(self):
        nick = self.nick_input.text().strip()
        pwd = self.pass_input.text()

        if not nick:
            QMessageBox.warning(self, "Erro", "Nickname obrigatório")
            return

        if nick.lower() != "admin" and pwd:
            QMessageBox.warning(self, "Erro", "Apenas o Admin deve inserir senha.")
            return

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.client.connect((HOST, PORT))
            recv = self.client.recv(1024).decode('utf-8')
            if recv == "NICK":
                self.client.send(nick.encode('utf-8'))

            recv = self.client.recv(1024).decode('utf-8')
            if recv == "PASS":
                if not pwd:
                    QMessageBox.warning(self, "Erro", "Senha de Admin obrigatória.")
                    self.client.close()
                    return
                while True:
                    self.client.send(pwd.encode('utf-8'))
                    resp = self.client.recv(1024).decode('utf-8')
                    if resp == "REFUSE":
                        self.client.close()
                        pwd, ok = QInputDialog.getText(self, "Senha Incorreta", "Tente a senha de admin novamente:",
                                                       echo=QLineEdit.Password)
                        if not ok or not pwd:
                            return
                        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.client.connect((HOST, PORT))
                        self.client.recv(1024)
                        self.client.send(nick.encode('utf-8'))
                        self.client.recv(1024)
                        continue
                    break

            elif recv == "BAN":
                self.chat_display.append("<span style='color: #e74c3c;'><i>[!] Você está banido.</i></span>")
                self.client.close()
                return

            self.nickname = nick.capitalize()
        except Exception as e:
            self.chat_display.append(f"<span style='color: #e74c3c;'><i>[!] Erro de conexão: {e}</i></span>")
            return

        self.chat_display.clear()
        self.chat_display.append(f"<span style='color: #f1c40f;'>[SISTEMA]: Bem-vindo ao bate-papo, {self.nickname}! Digite /ajuda para ver os comandos.</span>")

        self.connect_button.setEnabled(False)
        self.nick_input.setEnabled(False)
        self.pass_input.setEnabled(False)

        self.receive_thread = ReceiveThread(self.client)
        self.receive_thread.new_message.connect(self.handle_received)
        self.receive_thread.connection_closed.connect(self.handle_disconnected)
        self.receive_thread.start()

    # MODIFICAÇÃO: Fecha a janela imediatamente sem exibir qualquer caixa de mensagem (QMessageBox)
    def on_server_shutdown(self):
        self.close()

    def handle_received(self, msg):
        if msg.startswith("NICK"):
            return

        # MODIFICAÇÃO: Fechamento direto da janela ao receber comando SHUTDOWN do servidor
        if msg == "SHUTDOWN":
            self.close()
            return

        if msg.startswith("USERS:"):
            users = msg[6:].split(',')
            self.users_list.clear()
            for user in users:
                if user.strip():
                    self.users_list.addItem(f"• {user.strip()} (Online)")
            return

        if "Você foi expulso pelo Administrador!" in msg or "Você está banido" in msg:
            self.close()
            return

        if (
                msg.startswith("Comando recusado")
                or msg.startswith("[!]")
                or "entrou no chat" in msg
                or "saiu do chat" in msg
                or "foi expulso pelo Administrador!" in msg
                or "foi banido" in msg
                or "foi desbanido" in msg
        ):
            self.chat_display.append(f"<span style='color: #f1c40f;'>[SISTEMA]: {msg}</span>")
        else:
            self.chat_display.append(f"<span style='color: #ffffff;'>{msg}</span>")

    def handle_disconnected(self):
        self.chat_display.append("<span style='color: #e74c3c;'><i>[!] Desconectado do servidor.</i></span>")
        self.users_list.clear()
        if self.receive_thread:
            self.receive_thread.stop()
        self.connect_button.setEnabled(True)
        self.nick_input.setEnabled(True)
        self.pass_input.setEnabled(True)
        self._show_initial_instruction()

    def closeEvent(self, event):
        if hasattr(self, 'monitor_thread') and self.monitor_thread:
            self.monitor_thread.stop()
        if self.receive_thread:
            self.receive_thread.stop()
        try:
            self.client.close()
        except:
            pass
        event.accept()

    def send_message(self):
        if self.connect_button.isEnabled():
            return

        text = self.msg_input.text().strip()
        if not text:
            return

        if text.lower() == 'q':
            self.client.close()
            self.chat_display.append("<i>Você saiu do chat.</i>")
            if self.receive_thread:
                self.receive_thread.stop()
            self.close()
            self.connect_button.setEnabled(True)
            self.nick_input.setEnabled(True)
            self.pass_input.setEnabled(True)
            return

        if text.startswith('/'):
            if self.nickname.lower() == "admin":
                if text.startswith('/kick'):
                    self.client.send(f"KICK {text[6:].strip()}".encode('utf-8'))
                elif text.startswith('/ban'):
                    self.client.send(f"BAN {text[5:].strip()}".encode('utf-8'))
                elif text.startswith('/unban'):
                    self.client.send(f"UNBAN {text[7:].strip()}".encode('utf-8'))
                else:
                    self.chat_display.append("<span style='color: #f1c40f;'><i>[SISTEMA]: Comando de admin desconhecido.</i></span>")
            else:
                self.chat_display.append("<span style='color: #f1c40f;'><i>[SISTEMA]: Apenas o Admin pode usar comandos.</i></span>")
        else:
            self.client.send(f"{self.nickname}: {text}".encode('utf-8'))

        self.msg_input.clear()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Client()
    win.show()
    sys.exit(app.exec_())
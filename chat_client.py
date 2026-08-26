import socket
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QMessageBox, QHBoxLayout, QInputDialog,
    QComboBox, QListWidget
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont

HOST = '127.0.0.1'
PORT = 10346


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
        # MODIFICAÇÃO: Título da janela e dimensões iniciais ajustados
        self.setWindowTitle("PyChat Multi-Temas Client")
        self.resize(900, 600)
        # MODIFICAÇÃO: Aplicação de folha de estilos (QSS) Dark Theme
        self._apply_styles()

        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receive_thread = None
        self.nickname = None
        self._setup_ui()

    # MODIFICAÇÃO: Método exclusivo para personalização estética dos componentes
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

        # --- BARRA SUPERIOR (HEADER) ---
        header_layout = QHBoxLayout()

        # MODIFICAÇÃO: Tradução dos Placeholders e textos do cabeçalho
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

        # --- CORPO PRINCIPAL (CHAT + LISTA ONLINE) ---
        body_layout = QHBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)

        # MODIFICAÇÃO: Painel lateral para exibição dos usuários conectados em tempo real
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

        # --- BARRA INFERIOR (ENTRADA E BOTÕES) ---
        msg_input_layout = QHBoxLayout()

        # MODIFICAÇÃO: Tradução dos rótulos dos botões e do campo de mensagem
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

        # MODIFICAÇÃO: Dica de comandos de admin em português
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

        # MODIFICAÇÃO: Tradução das mensagens de erro na conexão
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

        # MODIFICAÇÃO: Tradução da mensagem de boas-vindas do sistema
        self.chat_display.append(f"<span style='color: #f1c40f;'>[SISTEMA]: Bem-vindo ao bate-papo, {self.nickname}! Digite /ajuda para ver os comandos.</span>")
        
        self.connect_button.setEnabled(False)
        self.nick_input.setEnabled(False)
        self.pass_input.setEnabled(False)

        self.receive_thread = ReceiveThread(self.client)
        self.receive_thread.new_message.connect(self.handle_received)
        self.receive_thread.connection_closed.connect(self.handle_disconnected)
        self.receive_thread.start()

    def handle_received(self, msg):
        if msg.startswith("NICK"):
            return

        # MODIFICAÇÃO: Leitura do sinal USERS: para preenchimento automático da lista lateral
        if msg.startswith("USERS:"):
            users = msg[6:].split(',')
            self.users_list.clear()
            for user in users:
                if user.strip():
                    self.users_list.addItem(f"• {user.strip()} (Online)")
            return

        # MODIFICAÇÃO: Tratamento de expulsão ou banimento com diálogos em português
        if "Você foi expulso pelo Administrador!" in msg or "Você está banido" in msg:
            QMessageBox.information(self, "Desconectado", msg)
            self.close()
            return

        # MODIFICAÇÃO: Formatação de mensagens do sistema e eventos traduzidos
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
        # MODIFICAÇÃO: Tradução da notificação de desconexão e limpeza da lista online
        self.chat_display.append("<span style='color: #e74c3c;'><i>[!] Desconectado do servidor.</i></span>")
        self.users_list.clear()
        if self.receive_thread:
            self.receive_thread.stop()
        self.connect_button.setEnabled(True)
        self.nick_input.setEnabled(True)
        self.pass_input.setEnabled(True)

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

        # MODIFICAÇÃO: Mensagens de resposta a comandos tratadas em português
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
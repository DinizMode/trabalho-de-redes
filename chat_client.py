import socket
import sys
# [MODIFICAÇÃO]: Importados módulos 'time' e 'datetime' para monitoramento do servidor e marcação de tempo (timestamps) nas mensagens.
import time
from datetime import datetime

# [MODIFICAÇÃO]: Importados novos componentes gráficos (QComboBox, QListWidget, QListWidgetItem, QColor, Qt) para montar a lista de usuários e seletores de status.
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QMessageBox, QHBoxLayout, QInputDialog,
    QComboBox, QListWidget, QListWidgetItem
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QColor

HOST = '127.0.0.1'
PORT = 10346


# [NOVA CLASSE]: Thread dedicada a monitorar a saúde do servidor via TCP em segundo plano.
# Se o servidor cair repentinamente, ela emite um sinal para fechar a aplicação graciosamente.
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
                    if self.was_online and self.running:
                        self.server_down.emit()
                        break
            except:
                if self.was_online and self.running:
                    self.server_down.emit()
                    break

            for _ in range(10):
                if not self.running:
                    break
                time.sleep(0.1)

    def stop(self):
        self.running = False
        self.quit()
        self.wait(1000)


class ReceiveThread(QThread):
    new_message = pyqtSignal(str)
    connection_closed = pyqtSignal()

    # [MODIFICAÇÃO]: Adicionado o parâmetro 'initial_buffer' para receber sobras do handshake inicial de conexão.
    def __init__(self, client, initial_buffer=""):
        super().__init__()
        self.client = client
        self.running = True
        self.buffer = initial_buffer

    def run(self):
        # [MODIFICAÇÃO]: Processa qualquer mensagem que já tenha chegado durante o handshake no buffer inicial.
        while '\n' in self.buffer:
            msg, self.buffer = self.buffer.split('\n', 1)
            msg = msg.strip()
            if msg:
                if self.running:
                    self.new_message.emit(msg)
                if msg == "SHUTDOWN":
                    self.running = False
                    return

        # [MODIFICAÇÃO]: Implementada leitura orientada a linhas com delimitador '\n' para evitar colisão/fragmentação de pacotes no socket.
        while self.running:
            try:
                data = self.client.recv(1024)
                if not data:
                    if self.running:
                        self.connection_closed.emit()
                    break

                self.buffer += data.decode('utf-8')
                while '\n' in self.buffer:
                    msg, self.buffer = self.buffer.split('\n', 1)
                    msg = msg.strip()
                    if msg:
                        if self.running:
                            self.new_message.emit(msg)
                        if msg == "SHUTDOWN":
                            self.running = False
                            break
            except:
                if self.running:
                    self.connection_closed.emit()
                break

    def stop(self):
        self.running = False
        self.quit()
        self.wait(1000) # [MODIFICAÇÃO]: Adicionado timeout de 1s para encerrar a thread com segurança sem travar a interface.


class Client(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyChat Multi-Temas Client")
        self.resize(900, 600)
        
        # [NOVO]: Aplica estilo Dark Theme moderno via CSS no PyQt.
        self._apply_styles()

        self.client = None
        self.receive_thread = None
        self.nickname = None
        self._setup_ui()
        
        # [NOVO]: Exibe mensagem estilizada de orientações na tela inicial.
        self._show_initial_instruction()

        # [NOVO]: Inicializa a thread de monitoramento do servidor.
        self.monitor_thread = ServerMonitorThread(HOST, PORT)
        self.monitor_thread.server_down.connect(self.on_server_shutdown)
        self.monitor_thread.start()

    # [NOVO MÉTODO]: Exibe um banner de ajuda na caixa de texto formatado com HTML.
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

    # [NOVO MÉTODO]: Define folha de estilos CSS para todos os componentes (Dark Theme).
    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #12131b;
                color: #e1e1e6;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel#lblUser {
                color: #7289da;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #1e1f2c;
                border: 1px solid #2a2c3d;
                border-radius: 18px;
                padding: 0px 15px;
                height: 36px;
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
                font-weight: bold;
                padding: 10px;
            }
            QPushButton {
                font-weight: bold;
                border: none;
                border-radius: 18px;
                height: 36px;
            }
            QPushButton#btnSend {
                background-color: #5865f2;
                color: white;
            }
            QPushButton#btnSend:hover {
                background-color: #4752c4;
            }
            QPushButton#btnRecord {
                background-color: #f35543;
                color: white;
            }
            QPushButton#btnRecord:hover {
                background-color: #d94332;
            }
            QPushButton#btnFile {
                background-color: #262838;
                color: white;
                border: 1px solid #363950;
            }
            QPushButton#btnFile:hover {
                background-color: #313448;
            }
            QPushButton#btnConnect {
                background-color: #23a55a;
                color: white;
                padding: 0px 16px;
                font-size: 12px;
            }
            QPushButton#btnConnect:hover {
                background-color: #1d8a4b;
            }
            QPushButton#btnConnect:disabled {
                background-color: #2b2d31;
                color: #4e5058;
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

        self.lbl_user = QLabel("<span style='color: #7289da; font-size: 13px;'>Usuário:</span>")
        self.lbl_user.setObjectName("lblUser")

        self.nick_input = QLineEdit()
        self.nick_input.setPlaceholderText("Nickname")
        self.nick_input.setFixedHeight(36)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Senha (apenas admin)")
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setFixedHeight(36)

        self.connect_button = QPushButton("Conectar")
        self.connect_button.setObjectName("btnConnect")
        self.connect_button.setFixedHeight(36)
        self.connect_button.clicked.connect(self.start_connection)

        # [NOVO]: Adicionado seletor de status de usuário (Online, Ausente, Ocupado).
        status_label = QLabel("Status:")
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Online", "Ausente", "Ocupado"])
        self.status_combo.currentTextChanged.connect(self.on_status_changed)

        btn_options = QPushButton("Opções")
        btn_options.setFlat(True)
        btn_folder = QPushButton("Pasta")
        btn_folder.setFlat(True)

        header_layout.addWidget(self.lbl_user)
        header_layout.addWidget(self.nick_input)
        header_layout.addWidget(self.pass_input)
        header_layout.addWidget(self.connect_button)
        header_layout.addStretch()
        header_layout.addWidget(status_label)
        header_layout.addWidget(self.status_combo)
        header_layout.addSpacing(40)
        header_layout.addWidget(btn_options)
        header_layout.addWidget(btn_folder)

        body_layout = QHBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)

        # [NOVO]: Adicionado painel lateral com QListWidget para exibir usuários conectados em tempo real.
        users_panel = QVBoxLayout()
        users_title = QLabel("ONLINE")
        users_title.setStyleSheet("font-weight: bold; color: #8e9297; font-size: 11px;")
        self.users_list = QListWidget()
        self.users_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        users_container = QWidget()
        users_container.setLayout(users_panel)
        users_panel.addWidget(users_title)
        users_panel.addWidget(self.users_list)
        users_panel.setContentsMargins(0, 0, 0, 0)

        body_layout.addWidget(self.chat_display, stretch=3)
        body_layout.addWidget(users_container, stretch=1)

        msg_input_layout = QHBoxLayout()

        # [NOVO]: Botões adicionais de arquivo e áudio na interface.
        self.btn_file = QPushButton("📁 Arquivo")
        self.btn_file.setObjectName("btnFile")
        self.btn_file.setFixedWidth(85)
        self.btn_file.setFixedHeight(36)

        self.btn_record = QPushButton("🎤 Gravar áudio")
        self.btn_record.setObjectName("btnRecord")
        self.btn_record.setFixedWidth(115)
        self.btn_record.setFixedHeight(36)

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Digite sua mensagem (ou 'q' para sair)...")
        self.msg_input.setFixedHeight(36)
        self.msg_input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Enviar")
        self.send_button.setObjectName("btnSend")
        self.send_button.setFixedWidth(75)
        self.send_button.setFixedHeight(36)
        self.send_button.clicked.connect(self.send_message)

        msg_input_layout.addWidget(self.btn_file)
        msg_input_layout.addWidget(self.btn_record)
        msg_input_layout.addWidget(self.msg_input, stretch=1)
        msg_input_layout.addWidget(self.send_button)

        self.tip_label = QLabel("Comandos Admin: /kick NOME, /ban NOME, /unban NOME")
        self.tip_label.setStyleSheet("color: #72767d; font-size: 11px;")
        self.tip_label.hide()

        main_layout.addLayout(header_layout)
        main_layout.addLayout(body_layout)
        main_layout.addLayout(msg_input_layout)
        main_layout.addWidget(self.tip_label)
        self.setLayout(main_layout)

    # [NOVO MÉTODO]: Método auxiliar para fazer a leitura socket buffer por linha durante a conexão inicial.
    def _recv_line(self, buf):
        while '\n' not in buf:
            data = self.client.recv(1024)
            if not data:
                break
            buf += data.decode('utf-8')
        if '\n' in buf:
            line, buf = buf.split('\n', 1)
            return line.strip(), buf
        return buf.strip(), ""

    # [NOVO MÉTODO]: Notifica o servidor sobre mudanças de status (Online, Ausente, Ocupado).
    def on_status_changed(self, new_status):
        if hasattr(self, 'client') and self.client:
            try:
                self.client.send(f"STATUS:{new_status}\n".encode('utf-8'))
            except:
                pass

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
        # [MODIFICAÇÃO]: Define timeout na conexão para não congelar a interface gráfica caso o servidor esteja indisponível.
        self.client.settimeout(3.0)
        buf = ""

        try:
            self.client.connect((HOST, PORT))
            # [MODIFICAÇÃO]: Atualizado fluxo de handshake adicionando quebras de linha '\n' aos pacotes transmitidos.
            line, buf = self._recv_line(buf)
            if line == "NICK":
                self.client.send(f"{nick}\n".encode('utf-8'))

            line, buf = self._recv_line(buf)
            if line == "PASS":
                if not pwd:
                    QMessageBox.warning(self, "Erro", "Senha de Admin obrigatória.")
                    self.client.close()
                    return
                while True:
                    self.client.send(f"{pwd}\n".encode('utf-8'))
                    line, buf = self._recv_line(buf)
                    if line == "REFUSE":
                        self.client.close()
                        pwd, ok = QInputDialog.getText(self, "Senha Incorreta", "Tente a senha de admin novamente:",
                                                       echo=QLineEdit.Password)
                        if not ok or not pwd:
                            return
                        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.client.settimeout(3.0)
                        self.client.connect((HOST, PORT))
                        buf = ""
                        _, buf = self._recv_line(buf)
                        self.client.send(f"{nick}\n".encode('utf-8'))
                        _, buf = self._recv_line(buf)
                        continue
                    break

            elif line == "BAN":
                self.chat_display.append("<span style='color: #e74c3c;'><i>[!] Você está banido.</i></span>")
                self.client.close()
                return

            self.nickname = nick.capitalize()
            # [MODIFICAÇÃO]: Limpa o timeout para permitir a leitura contínua na thread separada.
            self.client.settimeout(None)
        except Exception as e:
            self.chat_display.append(f"<span style='color: #e74c3c;'><i>[!] Erro de conexão: {e}</i></span>")
            return

        if self.nickname.lower() == "admin":
            self.tip_label.show()
        else:
            self.tip_label.hide()

        # [MODIFICAÇÃO]: Oculta a barra de login e exibe o crachá do usuário logado na tela.
        self.lbl_user.setText(
            f"<span style='color: #7289da; font-size: 13px; font-weight: normal;'>Usuário:</span> "
            f"<span style='color: #5865f2; font-size: 16px; font-weight: bold;'>{self.nickname}</span>"
        )
        self.nick_input.hide()
        self.pass_input.hide()
        self.connect_button.hide()

        # [MODIFICAÇÃO]: Adicionado timestamp na mensagem de boas-vindas.
        now = datetime.now().strftime("%H:%M")
        self.chat_display.clear()
        self.chat_display.append(
            f"<span style='color: #72767d; font-size: 11px;'>[{now}]</span> "
            f"<span style='color: #f1c40f;'>[SISTEMA]: Bem-vindo ao bate-papo, {self.nickname}!</span>"
        )

        self.receive_thread = ReceiveThread(self.client, initial_buffer=buf)
        self.receive_thread.new_message.connect(self.handle_received)
        self.receive_thread.connection_closed.connect(self.handle_disconnected)
        self.receive_thread.start()

        self.on_status_changed(self.status_combo.currentText())

    # [NOVO MÉTODO]: Handler para fechar a janela se o monitor detectar queda do servidor.
    def on_server_shutdown(self):
        self.close()

    def handle_received(self, msg):
        if msg == "NICK":
            return

        if msg == "SHUTDOWN":
            self.close()
            return

        # [NOVO]: Intercepta a lista de usuários 'USERS:' enviada pelo servidor e atualiza o QListWidget lateral.
        if msg.startswith("USERS:"):
            users_data = msg[6:].split(',')
            self.users_list.clear()
            for user_info in users_data:
                user_info = user_info.strip()
                if not user_info:
                    continue
                item = QListWidgetItem(f"• {user_info}")
                if "(Ausente)" in user_info:
                    item.setForeground(QColor("#f1c40f"))
                elif "(Ocupado)" in user_info:
                    item.setForeground(QColor("#e74c3c"))
                else:
                    item.setForeground(QColor("#2ecc71"))
                self.users_list.addItem(item)
            return

        if "Você foi expulso pelo Administrador!" in msg or "Você está banido" in msg:
            self.close()
            return

        # [MODIFICAÇÃO]: Adicionado timestamp em formato HH:MM e formatação de cores em HTML para cada mensagem recebida.
        now = datetime.now().strftime("%H:%M")
        timestamp_html = f"<span style='color: #72767d; font-size: 11px;'>[{now}]</span> "

        if (
                msg.startswith("Comando recusado")
                or msg.startswith("[!]")
                or "entrou no chat" in msg
                or "saiu do chat" in msg
                or "foi expulso pelo Administrador!" in msg
                or "foi banido" in msg
                or "foi desbanido" in msg
        ):
            self.chat_display.append(f"{timestamp_html}<span style='color: #f1c40f;'>[SISTEMA]: {msg}</span>")
        else:
            self.chat_display.append(f"{timestamp_html}<span style='color: #ffffff;'>{msg}</span>")

    def handle_disconnected(self):
        self.chat_display.append("<span style='color: #e74c3c;'><i>[!] Desconectado do servidor.</i></span>")
        self.users_list.clear()
        if self.receive_thread:
            self.receive_thread.stop()

        # [MODIFICAÇÃO]: Restaura os controles de conexão (inputs e botões) em caso de queda.
        self.lbl_user.setText("<span style='color: #7289da; font-size: 13px;'>Usuário:</span>")
        self.nick_input.show()
        self.pass_input.show()
        self.connect_button.show()
        self.connect_button.setEnabled(True)
        self.nick_input.setEnabled(True)
        self.pass_input.setEnabled(True)

        self.tip_label.hide()
        self._show_initial_instruction()

    # [NOVO MÉTODO]: Intercepta o encerramento da janela para fechar threads e sockets de forma limpa.
    def closeEvent(self, event):
        if hasattr(self, 'client') and self.client:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.client.close()
            except:
                pass

        if hasattr(self, 'monitor_thread') and self.monitor_thread:
            self.monitor_thread.stop()
        if hasattr(self, 'receive_thread') and self.receive_thread:
            self.receive_thread.stop()

        event.accept()

    def send_message(self):
        if not self.connect_button.isHidden() and self.connect_button.isEnabled():
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
            return

        # [MODIFICAÇÃO]: Adicionado delimitador '\n' no final do envio de todas as mensagens e comandos via socket.
        if text.startswith('/'):
            if self.nickname.lower() == "admin":
                if text.startswith('/kick'):
                    self.client.send(f"KICK {text[6:].strip()}\n".encode('utf-8'))
                elif text.startswith('/ban'):
                    self.client.send(f"BAN {text[5:].strip()}\n".encode('utf-8'))
                elif text.startswith('/unban'):
                    self.client.send(f"UNBAN {text[7:].strip()}\n".encode('utf-8'))
                else:
                    self.chat_display.append("<span style='color: #f1c40f;'><i>[SISTEMA]: Comando de admin desconhecido.</i></span>")
            else:
                self.chat_display.append("<span style='color: #f1c40f;'><i>[SISTEMA]: Apenas o Admin pode usar comandos.</i></span>")
        else:
            self.client.send(f"{self.nickname}: {text}\n".encode('utf-8'))

        self.msg_input.clear()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = Client()
    win.show()
    sys.exit(app.exec_())
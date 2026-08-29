import socket
import sys
import time
import os
import base64
import shutil
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QTextEdit, QTextBrowser, QLineEdit,
    QPushButton, QLabel, QMessageBox, QHBoxLayout, QInputDialog,
    QComboBox, QListWidget, QListWidgetItem, QFileDialog
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QUrl
from PyQt5.QtGui import QColor, QDesktopServices

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

    def __init__(self, client, initial_buffer=""):
        super().__init__()
        self.client = client
        self.running = True
        self.buffer = initial_buffer

    def run(self):
        while '\n' in self.buffer:
            msg, self.buffer = self.buffer.split('\n', 1)
            msg = msg.strip()
            if msg:
                if self.running:
                    self.new_message.emit(msg)
                if msg == "SHUTDOWN":
                    self.running = False
                    return

        while self.running:
            try:
                data = self.client.recv(8192)
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
        self.wait(1000)


class Client(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyChat Multi-Temas Client")
        self.resize(900, 600)
        
        self._apply_styles()

        self.client = None
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
            QTextBrowser {
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

        self.chat_display = QTextBrowser()
        self.chat_display.setOpenLinks(False) 
        self.chat_display.setReadOnly(True)
        self.chat_display.anchorClicked.connect(self.abrir_link_externo)

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

        self.btn_file = QPushButton("📁 Arquivo")
        self.btn_file.setObjectName("btnFile")
        self.btn_file.setFixedWidth(85)
        self.btn_file.setFixedHeight(36)
        self.btn_file.clicked.connect(self.handle_file_button)

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

    def abrir_link_externo(self, url):
        QDesktopServices.openUrl(url)

    def handle_file_button(self):
        if not hasattr(self, 'client') or self.client is None or self.connect_button.isVisible():
            QMessageBox.warning(self, "Aviso", "Você precisa estar conectado para enviar arquivos.")
            return

        reply = QMessageBox.question(
            self, "Tipo de Envio",
            "Deseja enviar um Arquivo/Imagem (Sim) ou uma Pasta inteira (Não)?\n\n(Pastas serão convertidas para .zip)",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )

        if reply == QMessageBox.Cancel:
            return

        if reply == QMessageBox.Yes:
            filepath, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo ou Imagem", "", "Todos os Arquivos (*);;Imagens (*.png *.jpg *.jpeg *.gif)")
            if filepath:
                self._process_and_send_file(filepath)
        elif reply == QMessageBox.No:
            dirpath = QFileDialog.getExistingDirectory(self, "Selecionar Pasta")
            if dirpath:
                try:
                    self.chat_display.append(f"<span style='color: #72767d; font-size: 11px;'>[{datetime.now().strftime('%H:%M')}]</span> <i>Compactando pasta para envio...</i>")
                    QApplication.processEvents()
                    zip_path = shutil.make_archive(dirpath, 'zip', dirpath)
                    self._process_and_send_file(zip_path)
                except Exception as e:
                    QMessageBox.warning(self, "Erro", f"Falha ao compactar pasta: {e}")

    def _process_and_send_file(self, filepath):
        try:
            filename = os.path.basename(filepath)
            if os.path.getsize(filepath) > 50 * 1024 * 1024:
                QMessageBox.warning(self, "Erro", "O arquivo/pasta excede o limite de 50MB estabelecido para o chat.")
                return
            
            with open(filepath, "rb") as f:
                data = f.read()
            
            b64_data = base64.b64encode(data).decode('utf-8')
            msg = f"FILE|{self.nickname}|{filename}|{b64_data}\n"
            
            self.client.send(msg.encode('utf-8'))
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Falha ao ler e enviar o arquivo: {e}")

    def display_file(self, sender, filename, b64data):
        now = datetime.now().strftime("%H:%M")
        timestamp_html = f"<span style='color: #72767d; font-size: 11px;'>[{now}]</span>"
        
        try:
            b64data = b64data.strip()
            b64data += "=" * ((4 - len(b64data) % 4) % 4)
            
            raw_data = base64.b64decode(b64data)
            ext = filename.split('.')[-1].lower() if '.' in filename else ''
            
            if ext in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp']:
                html = (f"{timestamp_html} <b>{sender}</b> enviou uma imagem:<br>"
                        f"<img src='data:image/{ext};base64,{b64data}' width='250'><br>")
                self.chat_display.append(html)
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                downloads_dir = os.path.join(base_dir, "downloads")
                
                os.makedirs(downloads_dir, exist_ok=True)
                filepath = os.path.join(downloads_dir, f"{int(time.time())}_{filename}")
                
                with open(filepath, "wb") as f:
                    f.write(raw_data)
                
                abs_path = os.path.abspath(filepath).replace('\\', '/')
                file_url = f"file:///{abs_path}"
                
                html = (f"{timestamp_html} <b>{sender}</b> enviou um arquivo/pasta: <b>{filename}</b><br>"
                        f"📁 <a href='{file_url}' style='color: #2ecc71; font-size: 11px; text-decoration: underline;'>Clique aqui para abrir o arquivo</a>")
                self.chat_display.append(html)
        except Exception as e:
            self.chat_display.append(f"{timestamp_html} <span style='color: #e74c3c;'>Erro ao processar arquivo recebido de {sender}: {e}</span>")

    def _recv_line(self, buf):
        while '\n' not in buf:
            data = self.client.recv(8192)
            if not data:
                break
            buf += data.decode('utf-8')
        if '\n' in buf:
            line, buf = buf.split('\n', 1)
            return line.strip(), buf
        return buf.strip(), ""

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
        self.client.settimeout(3.0)
        buf = ""

        try:
            self.client.connect((HOST, PORT))
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
            self.client.settimeout(None)
        except Exception as e:
            self.chat_display.append(f"<span style='color: #e74c3c;'><i>[!] Erro de conexão: {e}</i></span>")
            return

        if self.nickname.lower() == "admin":
            self.tip_label.show()
        else:
            self.tip_label.hide()

        self.lbl_user.setText(
            f"<span style='color: #7289da; font-size: 13px; font-weight: normal;'>Usuário:</span> "
            f"<span style='color: #5865f2; font-size: 16px; font-weight: bold;'>{self.nickname}</span>"
        )
        self.nick_input.hide()
        self.pass_input.hide()
        self.connect_button.hide()

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

    def on_server_shutdown(self):
        self.close()

    def handle_received(self, msg):
        if msg == "NICK":
            return

        if msg == "SHUTDOWN":
            self.close()
            return

        if msg.startswith("FILE|"):
            parts = msg.split('|', 3)
            if len(parts) == 4:
                _, sender, filename, b64data = parts
                self.display_file(sender, filename, b64data)
            return

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

        self.lbl_user.setText("<span style='color: #7289da; font-size: 13px;'>Usuário:</span>")
        self.nick_input.show()
        self.pass_input.show()
        self.connect_button.show()
        self.connect_button.setEnabled(True)
        self.nick_input.setEnabled(True)
        self.pass_input.setEnabled(True)

        self.tip_label.hide()
        self._show_initial_instruction()

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
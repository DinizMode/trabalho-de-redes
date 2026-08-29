import socket
import threading
# [MODIFICAÇÃO]: Importados módulos 'sys' e 'time' para encerramento limpo da aplicação e gerenciamento de loops.
import sys
import time

HOST = '127.0.0.1'
PORT = 10346

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# [CORREÇÃO ADICIONADA AQUI]: Força o Windows a liberar a porta imediatamente ao fechar
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind((HOST, PORT))
server.listen()
# [MODIFICAÇÃO]: Adicionado timeout de 1 segundo no accept do servidor para permitir interrupção graciosa sem travar o loop principal.
server.settimeout(1.0)

clients = []
nicknames = []
# [NOVO]: Lista paralela para armazenar os status ("Online", "Ausente", "Ocupado") dos usuários conectados.
statuses = []


def broadcast(message, exclude=None):
    if isinstance(message, str):
        message = message.encode('utf-8')
    for client in clients[:]:
        if client == exclude:
            continue
        try:
            client.send(message)
        except:
            try:
                index = clients.index(client)
                nickname = nicknames[index]
                clients.remove(client)
                nicknames.remove(nickname)
                # [MODIFICAÇÃO]: Remove o status correspondente quando um cliente cai.
                if index < len(statuses):
                    statuses.pop(index)
                print(f"Cliente desconectado removido: {nickname}")
                client.close()
                # [MODIFICAÇÃO]: Atualiza a lista de usuários para os demais após queda.
                broadcast_user_list()
            except ValueError:
                pass


# [NOVA FUNÇÃO]: Transmite a lista formatada de todos os usuários com seus respectivos status para todos os clientes ativos.
def broadcast_user_list():
    users_info = [f"{nick} ({stat})" for nick, stat in zip(nicknames, statuses)]
    # [CORREÇÃO]: Garantido o delimitador '\n' no final da mensagem de lista de usuários.
    user_list_msg = f"USERS:{','.join(users_info)}\n"
    broadcast(user_list_msg.encode('utf-8'))


def kick_user(name):
    try:
        lower_nicks = [n.lower() for n in nicknames]
        if name.lower() in lower_nicks:
            name_index = lower_nicks.index(name.lower())
            client_to_kick = clients[name_index]
            # [MODIFICAÇÃO]: Adicionado '\n' nos envios diretos de expulsão.
            client_to_kick.send("Você foi expulso pelo Administrador!\n".encode("utf-8"))
            clients.remove(client_to_kick)
            nicknames.pop(name_index)
            # [MODIFICAÇÃO]: Remove o status do usuário expulso.
            if name_index < len(statuses):
                statuses.pop(name_index)
            client_to_kick.close()
            name = name.capitalize()
            broadcast(f"{name} foi expulso pelo Administrador!\n".encode('utf-8'))
            print(f"{name} foi expulso pelo Administrador!")
            # [MODIFICAÇÃO]: Atualiza a lista dos clientes após a expulsão.
            broadcast_user_list()
        else:
            admin_index = lower_nicks.index("admin")
            admin_client = clients[admin_index]
            admin_client.send(f"{name} não está no chat!\n".encode('utf-8'))
            return
    except:
        print("Erro ao expulsar usuário.")


def unban_user(name):
    try:
        lower_nicks = [n.lower() for n in nicknames]
        with open("bans.txt", "r") as f:
            bans = [line.strip().lower() for line in f.readlines()]
        if name.lower() not in bans:
            if "admin" in lower_nicks:
                admin_index = lower_nicks.index("admin")
                admin_client = clients[admin_index]
                admin_client.send(f"{name} não está banido.\n".encode('utf-8'))
            return

        bans = [ban for ban in bans if ban != name.lower()]
        with open("bans.txt", "w") as f:
            for ban in bans:
                f.write(ban + "\n")

        # [MODIFICAÇÃO]: Adicionada quebra de linha '\n' na mensagem de desbanimento.
        broadcast(f"{name} foi desbanido pelo Administrador!\n")
        print(f"{name} foi desbanido pelo Administrador!")

    except Exception as e:
        print(f"Erro ao desbanir usuário: {e}")


def handle(client):
    nickname = None
    try:
        index = clients.index(client)
        nickname = nicknames[index]
    except ValueError:
        return

    try:
        # [MODIFICAÇÃO CRUCIAL]: Criado um buffer para acumular pacotes de dados grandes (imagens e arquivos).
        buffer = ""
        while True:
            # [MODIFICAÇÃO]: Aumentado o tamanho de recebimento para 8192 para maior eficiência em arquivos grandes.
            data = client.recv(8192)
            if not data:
                break
            
            buffer += data.decode('utf-8')

            # [MODIFICAÇÃO]: Só processa e envia a mensagem quando encontrar o delimitador '\n', garantindo integridade.
            while '\n' in buffer:
                msg, buffer = buffer.split('\n', 1)
                message = msg.strip()
                
                if not message:
                    continue

                if message.lower() == 'q':
                    # Levanta um erro genérico apenas para quebrar o loop e cair no 'finally' para desconectar.
                    raise ConnectionAbortedError 
                
                # [NOVO]: Trata o comando de alteração de status enviado pelos clientes.
                elif message.startswith("STATUS:"):
                    new_status = message[7:].strip()
                    if client in clients:
                        idx = clients.index(client)
                        statuses[idx] = new_status
                        broadcast_user_list()
                elif message.startswith("KICK"):
                    if nickname.lower() == "admin":
                        name = message[5:].strip()
                        kick_user(name)
                    else:
                        client.send("Comando recusado!\n".encode("utf-8"))
                elif message.startswith("BAN"):
                    if nickname.lower() == "admin":
                        name = message[4:].strip()
                        kick_user(name)
                        with open("bans.txt", "a") as f:
                            f.write(name.lower() + "\n")
                        broadcast(f"{name} foi banido do chat pelo Administrador!\n")
                    else:
                        client.send("Comando recusado!\n".encode("utf-8"))
                elif message.startswith("UNBAN"):
                    if nickname.lower() == "admin":
                        name = message[6:].strip()
                        unban_user(name)
                    else:
                        client.send("Comando recusado!\n".encode("utf-8"))
                else:
                    # [MODIFICAÇÃO]: Garante que toda mensagem retransmitida termine em '\n'.
                    broadcast(f"{message}\n")
    except:
        pass
    finally:
        if client in clients:
            try:
                index = clients.index(client)
                nickname = nicknames[index]
                clients.pop(index)
                nicknames.pop(index)
                # [MODIFICAÇÃO]: Pop no array de status ao desconectar.
                if index < len(statuses):
                    statuses.pop(index)
                broadcast(f"{nickname} saiu do chat.\n")
                print(f"{nickname} foi removido.")
                # [MODIFICAÇÃO]: Atualiza a lista dos clientes remanescentes.
                broadcast_user_list()
            except ValueError:
                pass
        client.close()


# [NOVA FUNÇÃO]: Encaminha aviso de SHUTDOWN e fecha sockets abertos de forma segura.
def close_all_connections():
    broadcast("SHUTDOWN\n".encode("utf-8"))
    for client in clients[:]:
        try:
            client.shutdown(socket.SHUT_RDWR)
        except:
            pass
        client.close()
    try:
        server.close()
    except:
        pass


def receive():
    while True:
        try:
            client, address = server.accept()
        # [MODIFICAÇÃO]: Captura timeout do socket para evitar travamento da rotina principal de escuta.
        except socket.timeout:
            continue
        except (OSError, KeyboardInterrupt, ValueError):
            break

        try:
            client.settimeout(None)
            # [MODIFICAÇÃO]: Adicionado '\n' nos comandos de protocolo de autenticação.
            client.send("NICK\n".encode("utf-8"))
            nickname = client.recv(1024).decode("utf-8").strip()
            nickname = nickname[0].upper() + nickname[1:].lower()

            if nickname.lower() in [n.lower() for n in nicknames]:
                client.send("Este usuário já está na sala de chat.\n".encode("utf-8"))
                client.close()
                continue

            # [MODIFICAÇÃO]: Tratamento com try-except caso o arquivo 'bans.txt' ainda não exista.
            try:
                with open("bans.txt", "r") as f:
                    bans = [line.strip().lower() for line in f.readlines()]
            except FileNotFoundError:
                bans = []

            if nickname.lower() in bans:
                client.send("BAN\n".encode("utf-8"))
                client.close()
                continue

            if nickname.lower() == "admin":
                client.send("PASS\n".encode("utf-8"))
                password = client.recv(1024).decode("utf-8").strip()
                if password != "adminpass":
                    client.send("REFUSE\n".encode("utf-8"))
                    client.close()
                    continue

            clients.append(client)
            nicknames.append(nickname)
            # [NOVO]: Registra o status padrão "Online" para o usuário recém-conectado.
            statuses.append("Online")
            client.send("OK\n".encode("utf-8"))

            print(f"{nickname} conectado de {address}")
            broadcast(f"{nickname} entrou no chat!\n", exclude=client)
            
            # [MODIFICAÇÃO]: Notifica a lista atualizada de participantes a todos na sala.
            broadcast_user_list()

            thread = threading.Thread(target=handle, args=(client,))
            thread.start()
        except:
            client.close()


# [MODIFICAÇÃO]: Thread de encerramento do servidor aprimorada para fechar portas e threads graciosamente.
def server_shutdown():
    while True:
        try:
            cmd = input().lower()
            if cmd == 'q':
                close_all_connections()
                break
        except (EOFError, KeyboardInterrupt):
            time.sleep(1)


if __name__ == "__main__":
    print("Servidor iniciando...")
    threading.Thread(target=server_shutdown, daemon=True).start()
    try:
        receive()
    except KeyboardInterrupt:
        pass
    finally:
        close_all_connections()
        print("\nServidor encerrado com sucesso pelo usuário.")
        sys.exit(0)
import socket
import threading

HOST = '127.0.0.1'
PORT = 10346

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

clients = []
nicknames = []


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
                # MODIFICAÇÃO: Tradução das mensagens do console do servidor
                print(f"Cliente desconectado removido: {nickname}")
                client.close()
                # MODIFICAÇÃO: Notifica alteração na lista de online quando um cliente cai por falha
                broadcast_user_list()
            except ValueError:
                pass


# MODIFICAÇÃO: Transmite a lista atualizada de usuários conectados via socket (Protocolo USERS:)
def broadcast_user_list():
    user_list_msg = f"USERS:{','.join(nicknames)}"
    broadcast(user_list_msg.encode('utf-8'))


def kick_user(name):
    try:
        lower_nicks = [n.lower() for n in nicknames]
        if name.lower() in lower_nicks:
            name_index = lower_nicks.index(name.lower())
            client_to_kick = clients[name_index]
            # MODIFICAÇÃO: Tradução de mensagens de moderação
            client_to_kick.send("Você foi expulso pelo Administrador!".encode("utf-8"))
            clients.remove(client_to_kick)
            nicknames.pop(name_index)
            client_to_kick.close()
            name = name.capitalize()
            broadcast(f"{name} foi expulso pelo Administrador!".encode('utf-8'))
            print(f"{name} foi expulso pelo Administrador!")
            # MODIFICAÇÃO: Atualização da lista de online após expulsão
            broadcast_user_list()
        else:
            admin_index = lower_nicks.index("admin")
            admin_client = clients[admin_index]
            admin_client.send(f"{name} não está no chat!".encode('utf-8'))
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
                admin_client.send(f"{name} não está banido.".encode('utf-8'))
            return

        bans = [ban for ban in bans if ban != name.lower()]
        with open("bans.txt", "w") as f:
            for ban in bans:
                f.write(ban + "\n")

        # MODIFICAÇÃO: Tradução das notificações de desbanimento
        broadcast(f"{name} foi desbanido pelo Administrador!")
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
        while True:
            msg = client.recv(1024)
            if not msg:
                break
            message = msg.decode().strip()

            if message.lower() == 'q':
                break
            elif message.startswith("KICK"):
                if nickname.lower() == "admin":
                    name = message[5:].strip()
                    kick_user(name)
                else:
                    client.send("Comando recusado!".encode("utf-8"))
            elif message.startswith("BAN"):
                if nickname.lower() == "admin":
                    name = message[4:].strip()
                    kick_user(name)
                    with open("bans.txt", "a") as f:
                        f.write(name.lower() + "\n")
                    # MODIFICAÇÃO: Tradução da mensagem de banimento
                    broadcast(f"{name} foi banido do chat pelo Administrador!")
                else:
                    client.send("Comando recusado!".encode("utf-8"))
            elif message.startswith("UNBAN"):
                if nickname.lower() == "admin":
                    name = message[6:].strip()
                    unban_user(name)
                else:
                    client.send("Comando recusado!".encode("utf-8"))
            else:
                broadcast(message)
    except:
        pass
    finally:
        if client in clients:
            try:
                index = clients.index(client)
                nickname = nicknames[index]
                clients.pop(index)
                nicknames.pop(index)
                # MODIFICAÇÃO: Tradução do aviso de saída
                broadcast(f"{nickname} saiu do chat.")
                print(f"{nickname} foi removido.")
                # MODIFICAÇÃO: Atualiza lista ao desconectar
                broadcast_user_list()
            except ValueError:
                pass
        client.close()


def receive():
    while True:
        try:
            client, address = server.accept()
        except OSError:
            break

        client.send("NICK".encode("utf-8"))
        nickname = client.recv(1024).decode("utf-8").strip()
        nickname = nickname[0].upper() + nickname[1:].lower()

        if nickname.lower() in [n.lower() for n in nicknames]:
            # MODIFICAÇÃO: Tradução do aviso de usuário já logado
            client.send("Este usuário já está na sala de chat.".encode("utf-8"))
            client.close()
            continue

        try:
            with open("bans.txt", "r") as f:
                bans = [line.strip().lower() for line in f.readlines()]
        except FileNotFoundError:
            bans = []

        if nickname.lower() in bans:
            client.send("BAN".encode("utf-8"))
            client.close()
            continue

        if nickname.lower() == "admin":
            client.send("PASS".encode("utf-8"))
            password = client.recv(1024).decode("utf-8")
            if password != "adminpass":
                client.send("REFUSE".encode("utf-8"))
                client.close()
                continue

        clients.append(client)
        nicknames.append(nickname)
        client.send("OK".encode("utf-8"))

        # MODIFICAÇÃO: Tradução dos prints e broadcasts de nova entrada
        print(f"{nickname} conectado de {address}")
        broadcast(f"{nickname} entrou no chat!\n", exclude=client)

        # MODIFICAÇÃO: Envia a nova lista de usuários a todos após nova conexão
        broadcast_user_list()

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()


def server_shutdown():
    while True:
        try:
            cmd = input().lower()
            if cmd == 'q':
                print("Encerrando o servidor...")
                broadcast("SHUTDOWN".encode("utf-8"))
                for client in clients:
                    try:
                        client.shutdown(socket.SHUT_RDWR)
                    except:
                        pass
                    client.close()
                server.close()
                break
        # MODIFICAÇÃO: Captura Ctrl+C (KeyboardInterrupt) e EOFError para encerrar o servidor sem erros no console
        except (KeyboardInterrupt, EOFError):
            print("\nServidor encerrado pelo usuário via terminal.")
            broadcast("SHUTDOWN".encode("utf-8"))
            for client in clients:
                try:
                    client.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                client.close()
            server.close()
            break


print("Servidor iniciando...")
threading.Thread(target=server_shutdown, daemon=True).start()
receive()
import socket
import threading
import time
import json
from logic import UnoGame, Card
from network import send_json, recv_json
from security import AuthManager

# Configurações
HOST = '0.0.0.0'
PORT = 5555

class GameServer:
    def __init__(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen()
        
        self.clients = [] # Lista de conexões
        self.players = {} # Mapa: conn -> player_data
        
        self.game = UnoGame() # Lógica do jogo (Estado Global)
        self.auth = AuthManager() # Gerenciador de Login/Tokens
        self.game_started = False
        
        print(f"[SERVIDOR] Iniciado em {HOST}:{PORT}")

    def broadcast(self, message_dict, exclude=None):
        """Envia mensagem para todos os clientes conectados."""
        for client in self.clients:
            if client != exclude:
                try:
                    send_json(client, message_dict)
                except:
                    self.remove_client(client)

    def remove_client(self, client):
        if client in self.clients:
            self.clients.remove(client)
            if client in self.players:
                print(f"[SERVIDOR] {self.players[client]['name']} desconectou.")
                del self.players[client]

    def handle_client(self, conn, addr):
        print(f"[CONEXÃO] Nova conexão de {addr}")
        client_name = f"Player_{len(self.clients)+1}"
        
        # 1. Handshake de Autenticação (Simulado)
        try:
            # Solicita Login
            send_json(conn, {"type": "AUTH_REQ"})
            creds = recv_json(conn)
            
            # Valida Token/Senha
            if creds['type'] == 'LOGIN':
                token = self.auth.login(creds['username'], creds.get('password', ''))
                if token:
                    client_name = creds['username']
                    send_json(conn, {"type": "AUTH_SUCCESS", "token": token, "player_id": len(self.clients)})
                else:
                    send_json(conn, {"type": "ERROR", "msg": "Auth Failed"})
                    conn.close()
                    return
            else:
                conn.close()
                return
                
        except Exception as e:
            print(f"Erro na auth: {e}")
            conn.close()
            return

        self.clients.append(conn)
        self.players[conn] = {"name": client_name, "id": len(self.clients)-1}
        
        # Se juntou e o jogo não começou, adiciona na lógica
        if not self.game_started:
            self.game.add_player(client_name)

        # Loop principal de escuta do cliente
        while True:
            try:
                msg = recv_json(conn)
                if not msg: break
                
                if msg['type'] == 'START_GAME' and len(self.clients) >= 2:
                    self.game_started = True
                    self.game.start_game()
                    self.broadcast_state()

                elif msg['type'] == 'MOVE':
                    # Processa jogada no estado global
                    success, message = self.game.play_card(
                        player_index=msg['player_id'], 
                        card_idx=msg['card_idx'], 
                        wild_color=msg.get('color')
                    )
                    # Envia feedback apenas para quem jogou se erro
                    if not success:
                        send_json(conn, {"type": "ERROR", "msg": message})
                    else:
                        self.broadcast_state()

                elif msg['type'] == 'DRAW':
                    self.game.draw_card(msg['player_id'])
                    self.broadcast_state()

                elif msg['type'] == 'CHAT':
                    # Relay de mensagem criptografada (O servidor não desencripta E2E)
                    print(f"[CHAT RELAY] De {client_name}: {msg['content'][:10]}...")
                    self.broadcast({
                        "type": "CHAT",
                        "sender": client_name,
                        "content": msg['content'], # Texto cifrado
                        "iv": msg.get('iv')       # Vetor de inicialização (se houver)
                    }, exclude=conn)

            except Exception as e:
                print(f"[ERRO] {e}")
                break

        self.remove_client(conn)
        conn.close()

    def broadcast_state(self):
        """Serializa o estado do jogo e envia para todos."""
        state = self.game.get_state_dict()
        self.broadcast({"type": "GAME_STATE", "state": state})

    def start(self):
        while True:
            conn, addr = self.server_socket.accept()
            thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    server = GameServer()
    server.start()
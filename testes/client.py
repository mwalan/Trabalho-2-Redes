import pygame
import socket
import threading
from network import send_json, recv_json
from security import ChatSecurity

# Configurações de Rede
HOST = '127.0.0.1' # Mude para o IP do servidor se for outra máquina
PORT = 5555

# Cores
C_FUNDO = (30, 30, 30)
C_VERDE_MESA = (34, 139, 34)
C_BRANCO = (255, 255, 255)
C_PRETO = (0, 0, 0)
C_CHAT_BG = (0, 0, 0, 150)

class UnoClient:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1000, 700))
        pygame.display.set_caption("Uno Online - Cliente")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 20)
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        self.player_id = -1
        self.token = None
        self.username = ""
        
        self.game_state = None
        self.chat_history = []
        self.security = ChatSecurity() # Modulo de Criptografia
        
        self.input_text = ""
        self.chat_active = False

    def connect(self, username):
        try:
            self.socket.connect((HOST, PORT))
            
            # 1. Login
            msg = recv_json(self.socket) # AUTH_REQ
            if msg['type'] == 'AUTH_REQ':
                send_json(self.socket, {"type": "LOGIN", "username": username, "password": "123"})
                
                resp = recv_json(self.socket)
                if resp['type'] == 'AUTH_SUCCESS':
                    self.token = resp['token']
                    self.player_id = resp['player_id']
                    self.username = username
                    self.connected = True
                    pygame.display.set_caption(f"Uno Online - {username}")
                    print(f"Logado com Token: {self.token[:8]}...")
                    
                    # Inicia Thread de Escuta
                    threading.Thread(target=self.listen_server, daemon=True).start()
                    return True
        except Exception as e:
            print(f"Erro ao conectar: {e}")
        return False

    def listen_server(self):
        """Escuta atualizações do servidor (Estado do Jogo e Chat)."""
        while self.connected:
            try:
                msg = recv_json(self.socket)
                if not msg: break
                
                if msg['type'] == 'GAME_STATE':
                    self.game_state = msg['state']
                    
                elif msg['type'] == 'CHAT':
                    # Descriptografa mensagem recebida (E2E)
                    decrypted = self.security.decrypt(msg['content'])
                    self.chat_history.append(f"{msg['sender']}: {decrypted}")
                    
            except:
                self.connected = False
                break

    def draw_card(self, x, y, card_dict, hover=False):
        """Renderiza uma carta baseada no dicionário recebido do servidor."""
        cor_map = {'red': (255,50,50), 'blue': (50,50,255), 'green': (50,200,50), 'yellow': (255,215,0), 'black': (50,50,50)}
        
        rect = pygame.Rect(x, y, 80, 120)
        if hover: rect.y -= 20
        
        color = cor_map.get(card_dict['color'], (100,100,100))
        pygame.draw.rect(self.screen, color, rect, border_radius=8)
        pygame.draw.rect(self.screen, C_BRANCO, rect, 2, border_radius=8)
        
        # Texto da carta
        txt = self.font.render(str(card_dict['symbol']), True, C_BRANCO)
        self.screen.blit(txt, (x+25, y+50))

    def run(self):
        # Tela de Login simples no console ou fixa
        name = "Player" + str(pygame.time.get_ticks() % 1000)
        if not self.connect(name): return

        running = True
        while running:
            self.screen.fill(C_FUNDO)
            
            if not self.game_state:
                # Lobby
                t = self.font.render("Aguardando Jogo... [Pressione ENTER para iniciar]", True, C_BRANCO)
                self.screen.blit(t, (300, 300))
                t2 = self.font.render(f"Logado como: {self.username}", True, (200,200,200))
                self.screen.blit(t2, (300, 340))
            else:
                # Mesa de Jogo
                self.screen.fill(C_VERDE_MESA)
                
                # Info
                info = f"Turno: {self.game_state['current_player_name']} | Cor: {self.game_state['current_color']}"
                self.screen.blit(self.font.render(info, True, C_BRANCO), (10, 10))
                
                # Descarte
                if self.game_state['discard_top']:
                    self.draw_card(460, 290, self.game_state['discard_top'])

                # Minha Mão
                if self.player_id < len(self.game_state['hands']):
                    my_hand = self.game_state['hands'][self.player_id]
                    for i, card in enumerate(my_hand):
                        mx, my = pygame.mouse.get_pos()
                        x_pos = 100 + i * 90
                        y_pos = 550
                        
                        # Hover check
                        hover = pygame.Rect(x_pos, y_pos, 80, 120).collidepoint(mx, my)
                        self.draw_card(x_pos, y_pos, card, hover)
                        
                        # Input de Clique (Jogar Carta)
                        if hover and pygame.mouse.get_pressed()[0]:
                            send_json(self.socket, {
                                "type": "MOVE", 
                                "player_id": self.player_id, 
                                "card_idx": i,
                                "color": "red" # Simplificação: sempre escolhe vermelho pra wild
                            })
                            pygame.time.delay(200)

                # Monte (Comprar)
                pygame.draw.rect(self.screen, C_PRETO, (350, 290, 80, 120))
                if pygame.Rect(350, 290, 80, 120).collidepoint(pygame.mouse.get_pos()):
                     if pygame.mouse.get_pressed()[0]:
                        send_json(self.socket, {"type": "DRAW", "player_id": self.player_id})
                        pygame.time.delay(200)

            # --- Interface de Chat ---
            self.draw_chat()

            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if not self.game_state and event.key == pygame.K_RETURN:
                        send_json(self.socket, {"type": "START_GAME"})
                    
                    # Logica de digitação do chat
                    if event.key == pygame.K_t: self.chat_active = True
                    elif self.chat_active:
                        if event.key == pygame.K_RETURN:
                            # Criptografa antes de enviar
                            encrypted = self.security.encrypt(self.input_text)
                            send_json(self.socket, {"type": "CHAT", "content": encrypted})
                            self.chat_history.append(f"Eu: {self.input_text}")
                            self.input_text = ""
                            self.chat_active = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.input_text = self.input_text[:-1]
                        else:
                            self.input_text += event.unicode

            pygame.display.flip()
            self.clock.tick(60)

    def draw_chat(self):
        # Renderiza Overlay de Chat
        s = pygame.Surface((300, 200))
        s.set_alpha(180)
        s.fill(C_PRETO)
        self.screen.blit(s, (10, 500))
        
        # Historico
        for i, line in enumerate(self.chat_history[-8:]):
            txt = self.font.render(line, True, (200, 200, 200))
            self.screen.blit(txt, (15, 510 + i * 20))
            
        # Input
        if self.chat_active:
            pygame.draw.rect(self.screen, C_BRANCO, (10, 680, 300, 20), 2)
            txt = self.font.render(self.input_text, True, C_BRANCO)
            self.screen.blit(txt, (15, 680))

if __name__ == "__main__":
    client = UnoClient()
    client.run()
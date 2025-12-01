#Aqui usamos pygame. Ele desenha o menu inicial para escolher o modo (se você for o Jogador 0)
#e desenha a mesa de jogo.

import pygame
import socket
import pickle
from protocolo import EstadoJogo

# Configuração de Rede
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 5555))
meu_id = pickle.loads(client.recv(4096))

# Configuração Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(f"UNO - Jogador {meu_id}")
FONT = pygame.font.SysFont("comicsans", 40)
FONT_PEQUENA = pygame.font.SysFont("comicsans", 20)

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
CORES_RGB = {
    'VERMELHO': (255, 0, 0), 'VERDE': (0, 255, 0),
    'AZUL': (0, 0, 255), 'AMARELO': (255, 255, 0),
    'PRETO': (50, 50, 50)
}

estado_local = None

def enviar_acao(acao):
    try:
        client.send(pickle.dumps(acao))
    except:
        print("Erro ao enviar")

def receber_dados():
    global estado_local
    while True:
        try:
            data = client.recv(4096 * 4) # Buffer maior para o estado completo
            if not data: break
            estado_local = pickle.loads(data)
        except:
            break

import threading
thread_rede = threading.Thread(target=receber_dados)
thread_rede.start()

def desenhar_carta(x, y, carta, hover=False):
    cor_fundo = CORES_RGB.get(carta.cor, BLACK)
    rect = pygame.Rect(x, y, 60, 90)
    pygame.draw.rect(win, WHITE, (x-2, y-2, 64, 94)) # Borda
    pygame.draw.rect(win, cor_fundo, rect)
    
    if hover:
        pygame.draw.rect(win, (255, 255, 255), rect, 3) # Realce

    texto = FONT_PEQUENA.render(carta.valor, 1, WHITE)
    win.blit(texto, (x + 30 - texto.get_width()//2, y + 45 - texto.get_height()//2))
    return rect

def tela_menu():
    win.fill(GRAY)
    titulo = FONT.render("UNO MULTIPLAYER", 1, BLACK)
    win.blit(titulo, (WIDTH//2 - titulo.get_width()//2, 50))
    
    if meu_id == 0:
        instrucao = FONT_PEQUENA.render("Escolha o modo de jogo:", 1, BLACK)
        win.blit(instrucao, (WIDTH//2 - instrucao.get_width()//2, 150))
        
        btn_2p = pygame.Rect(300, 200, 200, 50)
        btn_4p = pygame.Rect(300, 270, 200, 50)
        btn_dupla = pygame.Rect(300, 340, 200, 50)
        
        pygame.draw.rect(win, BLACK, btn_2p)
        pygame.draw.rect(win, BLACK, btn_4p)
        pygame.draw.rect(win, BLACK, btn_dupla)
        
        win.blit(FONT_PEQUENA.render("2 JOGADORES", 1, WHITE), (330, 215))
        win.blit(FONT_PEQUENA.render("4 JOGADORES", 1, WHITE), (330, 285))
        win.blit(FONT_PEQUENA.render("2 DUPLAS", 1, WHITE), (350, 355))
        
        return [btn_2p, btn_4p, btn_dupla]
    else:
        texto = FONT.render("Aguardando o anfitrião configurar...", 1, BLACK)
        win.blit(texto, (WIDTH//2 - texto.get_width()//2, 300))
        return []

def tela_jogo():
    win.fill((34, 139, 34)) # Verde mesa
    
    if not estado_local: return []

    # Informações
    txt_modo = FONT_PEQUENA.render(f"Modo: {estado_local.modo_jogo}", 1, WHITE)
    win.blit(txt_modo, (10, 10))
    
    txt_vez = FONT.render(f"Vez do Jogador: {estado_local.jogadores_conectados[estado_local.jogador_atual]}", 1, WHITE)
    win.blit(txt_vez, (WIDTH//2 - txt_vez.get_width()//2, 20))

    if estado_local.modo_jogo == 'DUPLAS':
        parceiro = (meu_id + 2) % 4
        txt_dupla = FONT_PEQUENA.render(f"Seu parceiro: Jogador {parceiro}", 1, WHITE)
        win.blit(txt_dupla, (10, 40))

    # Pilha de Descarte
    if estado_local.descarte:
        desenhar_carta(WIDTH//2 - 30, HEIGHT//2 - 45, estado_local.descarte[-1])

    # Botão Comprar
    btn_comprar = pygame.Rect(WIDTH - 150, HEIGHT//2 - 25, 100, 50)
    pygame.draw.rect(win, (200, 50, 50), btn_comprar)
    win.blit(FONT_PEQUENA.render("COMPRAR", 1, WHITE), (WIDTH - 140, HEIGHT//2 - 10))

    # Minha Mão
    minha_mao = estado_local.maos.get(meu_id, [])
    areas_cartas = []
    
    inicio_x = WIDTH//2 - (len(minha_mao) * 40)//2
    for i, carta in enumerate(minha_mao):
        pos_x = inicio_x + i * 40
        pos_y = HEIGHT - 110
        # Check hover
        mouse_pos = pygame.mouse.get_pos()
        rect_carta = pygame.Rect(pos_x, pos_y, 60, 90)
        is_hover = rect_carta.collidepoint(mouse_pos)
        
        # Desenha a carta um pouco mais para cima se estiver com o mouse em cima
        final_y = pos_y - 20 if is_hover else pos_y
        
        rect = desenhar_carta(pos_x, final_y, carta, is_hover)
        areas_cartas.append((rect, i))

    return areas_cartas, btn_comprar

# Loop Principal
run = True
clock = pygame.time.Clock()

while run:
    clock.tick(30)
    
    # Lógica de Telas
    btns_menu = []
    areas_jogo = []
    btn_comprar_rect = None

    if not estado_local or not estado_local.jogo_iniciado:
        btns_menu = tela_menu()
    else:
        areas_jogo, btn_comprar_rect = tela_jogo()

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
            client.close()
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = event.pos
            
            # Interação no Menu
            if not estado_local or not estado_local.jogo_iniciado:
                if meu_id == 0 and btns_menu:
                    modo = None
                    if btns_menu[0].collidepoint(mouse_pos): modo = '2P'
                    elif btns_menu[1].collidepoint(mouse_pos): modo = '4P'
                    elif btns_menu[2].collidepoint(mouse_pos): modo = 'DUPLAS'
                    
                    if modo:
                        enviar_acao({'tipo': 'CONFIG_MODO', 'modo': modo})

            # Interação no Jogo
            elif estado_local.jogadores_conectados[estado_local.jogador_atual] == meu_id:
                # Tentar Jogar Carta
                jogou = False
                # Iterar de trás para frente para pegar a carta que está desenhada "por cima"
                for rect, indice in reversed(areas_jogo):
                    if rect.collidepoint(mouse_pos):
                        enviar_acao({'tipo': 'JOGAR', 'indice': indice})
                        jogou = True
                        break
                
                # Botão Comprar
                if not jogou and btn_comprar_rect and btn_comprar_rect.collidepoint(mouse_pos):
                    enviar_acao({'tipo': 'COMPRAR'})

pygame.quit()

"""
ARQUIVO: cliente.py
FUNÇÃO: Interface Gráfica (GUI) e comunicação com o servidor.
TECNOLOGIAS: Pygame (visual) e Sockets (rede).
"""

import pygame
import socket
import pickle
import threading
import math
import time
import sys
from protocolo import EstadoJogo, MSG_CRIAR_SALA, MSG_ENTRAR_SALA, MSG_LISTAR_SALAS, MSG_INICIAR_JOGO, MSG_GRITAR_UNO, MSG_SAIR_SALA, MSG_ERRO

# --- CONFIGURAÇÃO DE REDE ---
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print("=== Configuração de Conexão ===")
server_ip = input("Digite o IP do servidor (pressione Enter para localhost): ").strip()
if not server_ip:
    server_ip = 'localhost'

try:
    client.connect((server_ip, 5555))
except Exception as e:
    print(f"Não foi possível conectar ao servidor em {server_ip}:5555")
    print(f"Erro: {e}")
    exit()

# --- CONFIGURAÇÃO PYGAME ---
pygame.display.init()
pygame.font.init()

LARGURA_TELA = 1000
ALTURA_TELA = 700
win = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption("UNO Multiplayer - Lobby")

# --- CORES E ESTILOS ---
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
CINZA_FUNDO = (30, 30, 30)
VERDE_MESA = (34, 139, 34)
VERMELHO = (235, 50, 50)
VERDE = (50, 200, 50)
AZUL = (50, 50, 235)
AMARELO = (245, 215, 20)
CINZA_CARTA = (50, 50, 50)

MAPA_CORES = {
    'VERMELHO': VERMELHO, 'VERDE': VERDE, 'AZUL': AZUL, 'AMARELO': AMARELO, 'PRETO': PRETO
}

FONT_INFO = pygame.font.SysFont('Arial', 24, bold=True)
FONT_AVISO = pygame.font.SysFont('Arial', 36, bold=True)
FONT_CARTA = pygame.font.SysFont('Arial', 40, bold=True)
FONT_CARTA_PQ = pygame.font.SysFont('Arial', 14, bold=True)

# --- ESTADO DO CLIENTE ---
estado_local = None
meu_id = None
em_sala = False
lista_salas = []
mensagem_erro = ""
escolhendo_cor = False
carta_preta_pendente = None # Índice da carta preta que foi clicada

# --- CLASSES AUXILIARES ---
class Botao:
    def __init__(self, x, y, w, h, texto, cor, acao):
        self.rect = pygame.Rect(x, y, w, h)
        self.texto = texto
        self.cor = cor
        self.acao = acao
        self.hover = False

    def desenhar(self, tela):
        cor_atual = tuple(min(c + 30, 255) for c in self.cor) if self.hover else self.cor
        pygame.draw.rect(tela, cor_atual, self.rect, border_radius=12)
        pygame.draw.rect(tela, BRANCO, self.rect, width=2, border_radius=12)
        
        fonte = pygame.font.SysFont('Arial', 20, bold=True)
        txt = fonte.render(self.texto, True, BRANCO)
        txt_rect = txt.get_rect(center=self.rect.center)
        tela.blit(txt, txt_rect)

    def checar_click(self, pos):
        if self.rect.collidepoint(pos):
            return self.acao
        return None

class InputBox:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = CINZA_CARTA
        self.text = text
        self.txt_surface = FONT_INFO.render(text, True, BRANCO)
        self.active = False

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = AZUL if self.active else CINZA_CARTA
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return self.text
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                self.txt_surface = FONT_INFO.render(self.text, True, BRANCO)
        return None

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect, 2)
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))

# --- FUNÇÕES DE REDE ---
def enviar_acao(acao):
    try:
        client.send(pickle.dumps(acao))
    except:
        print("Erro ao enviar")

def receber_dados():
    global estado_local, meu_id, em_sala, lista_salas, mensagem_erro
    while True:
        try:
            data = client.recv(4096 * 8)
            if not data: break
            
            msg = pickle.loads(data)
            
            if isinstance(msg, dict):
                if msg.get('tipo') == MSG_LISTAR_SALAS:
                    lista_salas = msg['salas']
                elif msg.get('tipo') == MSG_ERRO:
                    mensagem_erro = msg['msg']
                    print(f"Erro do servidor: {mensagem_erro}")
                elif msg.get('tipo') == 'SUCESSO_CRIAR':
                    # Sala criada, agora entra nela automaticamente
                    # (O nome da sala precisa ser persistido ou reenviado, simplificando aqui)
                    pass 
                elif msg.get('tipo') == 'ENTROU':
                    meu_id = msg['id']
                    em_sala = True
                    pygame.display.set_caption(f"UNO - Jogador {meu_id}")
            
            elif isinstance(msg, EstadoJogo):
                estado_local = msg
                
        except Exception as e:
            print(f"Erro na thread de rede: {e}")
            break

thread_rede = threading.Thread(target=receber_dados, daemon=True)
thread_rede.start()

# --- FUNÇÕES DE DESENHO (JOGO) ---
def get_simbolo_visual(valor):
    if valor == 'PULAR': return "Ø"
    if valor == 'INVERTER': return "R"
    if valor == 'CORINGA': return "C"
    return valor

def desenhar_carta_estilizada(x, y, carta, hover=False, oculto=False):
    largura = 80
    altura = 120
    if hover and not oculto: y -= 20
    rect = pygame.Rect(x, y, largura, altura)
    
    # Sombra
    pygame.draw.rect(win, (0,0,0, 100), (x+3, y+3, largura, altura), border_radius=10)

    if oculto:
        pygame.draw.rect(win, PRETO, rect, border_radius=10)
        pygame.draw.rect(win, VERMELHO, rect, width=3, border_radius=10)
        pygame.draw.circle(win, AMARELO, (x + largura//2, y + altura//2), 25)
        txt = FONT_CARTA_PQ.render("UNO", True, VERMELHO)
        win.blit(txt, txt.get_rect(center=rect.center))
    else:
        cor_fundo = MAPA_CORES.get(carta.cor, CINZA_CARTA)
        pygame.draw.rect(win, cor_fundo, rect, border_radius=10)
        pygame.draw.rect(win, BRANCO, rect, width=3, border_radius=10)
        pygame.draw.ellipse(win, BRANCO, (x+10, y+20, largura-20, altura-40))
        
        simbolo = get_simbolo_visual(carta.valor)
        cor_texto = cor_fundo if carta.cor != 'PRETO' else PRETO
        txt_centro = FONT_CARTA.render(simbolo, True, cor_texto)
        if len(simbolo) > 1: 
            txt_centro = pygame.font.SysFont('Arial', 30, bold=True).render(simbolo, True, cor_texto)
        win.blit(txt_centro, txt_centro.get_rect(center=rect.center))
        
        txt_pq = FONT_CARTA_PQ.render(simbolo, True, BRANCO)
        win.blit(txt_pq, (x+5, y+5))
        win.blit(txt_pq, (x+largura-20, y+altura-20))
    return rect

def desenhar_setas_direcao(centro_x, centro_y, sentido_horario):
    raio = 130
    cor_dir = AMARELO if sentido_horario else AZUL
    direcao = 1 if sentido_horario else -1
    for i in range(3):
        angulo_base = i * 120
        angulo_inicio = math.radians(angulo_base + 20)
        angulo_fim = math.radians(angulo_base + 100)
        rect_arc = pygame.Rect(centro_x - raio, centro_y - raio, raio*2, raio*2)
        pygame.draw.arc(win, cor_dir, rect_arc, angulo_inicio, angulo_fim, 5)
        
        # Seta (simplificada)
        ponta_angle = angulo_inicio if direcao == 1 else angulo_fim
        ponta_x = centro_x + raio * math.cos(ponta_angle)
        ponta_y = centro_y - raio * math.sin(ponta_angle)
        pygame.draw.circle(win, cor_dir, (int(ponta_x), int(ponta_y)), 10)

# --- TELAS ---
input_sala = InputBox(350, 150, 300, 40, '')

def tela_lobby():
    win.fill(CINZA_FUNDO)
    titulo = FONT_AVISO.render("LOBBY UNO", True, BRANCO)
    win.blit(titulo, titulo.get_rect(center=(LARGURA_TELA//2, 50)))

    # Criar Sala
    txt_criar = FONT_INFO.render("Nome da Nova Sala:", True, BRANCO)
    win.blit(txt_criar, (350, 120))
    input_sala.draw(win)
    btn_criar = Botao(660, 150, 100, 40, "CRIAR", VERDE, 'CRIAR')
    btn_criar.desenhar(win)

    # Lista de Salas
    txt_lista = FONT_INFO.render("Salas Disponíveis:", True, BRANCO)
    win.blit(txt_lista, (100, 250))
    
    botoes_salas = []
    y_offset = 300
    
    if not lista_salas:
        win.blit(FONT_INFO.render("Nenhuma sala encontrada...", True, CINZA_CARTA), (100, 300))
    
    for sala in lista_salas:
        texto = f"{sala['nome']} ({sala['jogadores']}/4) - {sala['status']}"
        btn = Botao(100, y_offset, 600, 50, texto, AZUL, {'tipo': 'ENTRAR', 'nome': sala['nome']})
        btn.desenhar(win)
        botoes_salas.append(btn)
        y_offset += 60
        
    # Mensagem de Erro
    if mensagem_erro:
        erro = FONT_INFO.render(mensagem_erro, True, VERMELHO)
        win.blit(erro, (LARGURA_TELA//2 - erro.get_width()//2, 600))

    return [btn_criar] + botoes_salas

def tela_config_sala():
    win.fill(CINZA_FUNDO)
    titulo = FONT_AVISO.render("SALA DE ESPERA", True, BRANCO)
    win.blit(titulo, titulo.get_rect(center=(LARGURA_TELA//2, 50)))
    
    if not estado_local:
        return []

    # Lista de Jogadores
    y_offset = 150
    txt_jogadores = FONT_INFO.render("Jogadores Conectados:", True, BRANCO)
    win.blit(txt_jogadores, (100, 100))
    
    if estado_local:
        for pid in estado_local.jogadores_conectados:
            nome_display = f"Jogador {pid[0]}:{pid[1]}"
            if pid == estado_local.host_id: nome_display += " (Anfitrião)"
            if pid == meu_id: nome_display += " (Você)"
            
            txt = FONT_INFO.render(nome_display, True, BRANCO)
            win.blit(txt, (100, y_offset))
            y_offset += 40

    botoes = []
    if meu_id == estado_local.host_id:
        # Botão Iniciar
        pode_iniciar = len(estado_local.jogadores_conectados) >= 2
        cor_btn = VERDE if pode_iniciar else CINZA_CARTA
        
        btn_iniciar = Botao(LARGURA_TELA//2 - 100, 500, 200, 60, "INICIAR JOGO", cor_btn, 'INICIAR')
        btn_iniciar.desenhar(win)
        botoes.append(btn_iniciar)
        
        if not pode_iniciar:
             aviso = FONT_CARTA_PQ.render("Mínimo 2 jogadores para iniciar", True, VERMELHO)
             win.blit(aviso, aviso.get_rect(center=(LARGURA_TELA//2, 570)))
    else:
        txt = FONT_AVISO.render("Aguardando o anfitrião iniciar...", True, BRANCO)
        win.blit(txt, txt.get_rect(center=(LARGURA_TELA//2, 500)))
        
    return botoes

def desenhar_mao_oponente(posicao, qtd_cartas, nome, ativo):
    centro_x, centro_y = LARGURA_TELA // 2, ALTURA_TELA // 2
    
    if posicao == 'TOPO':
        largura = 80
        altura = 120
        espacamento = 50
        total_largura = (qtd_cartas - 1) * espacamento + largura
        inicio_x = centro_x - total_largura // 2
        pos_y = 50 
        
        for i in range(qtd_cartas):
            pos_x = inicio_x + i * espacamento
            rect = pygame.Rect(pos_x, pos_y, largura, altura)
            
            # Desenho da carta (verso)
            pygame.draw.rect(win, PRETO, rect, border_radius=10)
            pygame.draw.rect(win, VERMELHO, rect, width=3, border_radius=10)
            pygame.draw.circle(win, AMARELO, rect.center, 25)
            txt = FONT_CARTA_PQ.render("UNO", True, VERMELHO)
            win.blit(txt, txt.get_rect(center=rect.center))
            
            if ativo:
                pygame.draw.rect(win, AMARELO, rect, width=3, border_radius=10)

    elif posicao == 'ESQUERDA':
        largura = 120 # Deitado
        altura = 80
        espacamento = 40
        total_altura = (qtd_cartas - 1) * espacamento + altura
        inicio_y = centro_y - total_altura // 2
        pos_x = 50
        
        for i in range(qtd_cartas):
            pos_y = inicio_y + i * espacamento
            rect = pygame.Rect(pos_x, pos_y, largura, altura)
            
            pygame.draw.rect(win, PRETO, rect, border_radius=10)
            pygame.draw.rect(win, VERMELHO, rect, width=3, border_radius=10)
            pygame.draw.circle(win, AMARELO, rect.center, 25)
            
            txt = FONT_CARTA_PQ.render("UNO", True, VERMELHO)
            txt = pygame.transform.rotate(txt, -90)
            win.blit(txt, txt.get_rect(center=rect.center))
            
            if ativo:
                pygame.draw.rect(win, AMARELO, rect, width=3, border_radius=10)
        
    elif posicao == 'DIREITA':
        largura = 120 # Deitado
        altura = 80
        espacamento = 40
        total_altura = (qtd_cartas - 1) * espacamento + altura
        inicio_y = centro_y - total_altura // 2
        pos_x = LARGURA_TELA - 50 - largura
        
        for i in range(qtd_cartas):
            pos_y = inicio_y + i * espacamento
            rect = pygame.Rect(pos_x, pos_y, largura, altura)
            
            pygame.draw.rect(win, PRETO, rect, border_radius=10)
            pygame.draw.rect(win, VERMELHO, rect, width=3, border_radius=10)
            pygame.draw.circle(win, AMARELO, rect.center, 25)
            
            txt = FONT_CARTA_PQ.render("UNO", True, VERMELHO)
            txt = pygame.transform.rotate(txt, 90)
            win.blit(txt, txt.get_rect(center=rect.center))
            
            if ativo:
                pygame.draw.rect(win, AMARELO, rect, width=3, border_radius=10)

def tela_jogo():
    win.fill(VERDE_MESA)
    if not estado_local: return [], None, []

    centro_x, centro_y = LARGURA_TELA // 2, ALTURA_TELA // 2

    # Vez
    jogador_vez_id = estado_local.jogadores_conectados[estado_local.jogador_atual]
    
    # Se for minha vez, avisa grande embaixo
    if jogador_vez_id == meu_id:
        txt_obj = FONT_AVISO.render("SUA VEZ!", True, AMARELO)
        win.blit(txt_obj, txt_obj.get_rect(center=(centro_x, ALTURA_TELA - 180)))

    desenhar_setas_direcao(centro_x, centro_y, estado_local.sentido_horario)
    
    # --- DESENHAR OPONENTES ---
    jogadores = estado_local.jogadores_conectados
    num_jogadores = len(jogadores)
    if meu_id in jogadores:
        meu_idx = jogadores.index(meu_id)
        
        posicoes = []
        if num_jogadores == 2:
            posicoes = [(1, 'TOPO')]
        elif num_jogadores == 3:
            posicoes = [(1, 'ESQUERDA'), (2, 'DIREITA')]
        elif num_jogadores >= 4:
            posicoes = [(1, 'ESQUERDA'), (2, 'TOPO'), (3, 'DIREITA')]
            
        for offset, pos_nome in posicoes:
            op_idx = (meu_idx + offset) % num_jogadores
            op_id = jogadores[op_idx]
            qtd = len(estado_local.maos.get(op_id, []))
            ativo = (op_id == jogador_vez_id)
            desenhar_mao_oponente(pos_nome, qtd, f"P:{op_id[1]}", ativo)

    # Monte
    rect_monte = pygame.Rect(centro_x - 100, centro_y - 60, 80, 120)
    pygame.draw.rect(win, PRETO, rect_monte, border_radius=10)
    pygame.draw.rect(win, BRANCO, rect_monte, width=2, border_radius=10)
    win.blit(FONT_CARTA_PQ.render("Monte", True, BRANCO), (centro_x - 90, centro_y - 15))
    btn_comprar = rect_monte

    # Descarte
    if estado_local.descarte:
        topo = estado_local.descarte[-1]
        
        # Se a carta for preta, desenha o fundo com a cor atual do jogo
        cor_fundo_topo = CINZA_CARTA
        if topo.cor == 'PRETO' and estado_local.cor_atual:
             cor_fundo_topo = MAPA_CORES.get(estado_local.cor_atual, CINZA_CARTA)
             pygame.draw.rect(win, cor_fundo_topo, (centro_x + 10, centro_y - 70, 100, 140), border_radius=15)
        
        desenhar_carta_estilizada(centro_x + 20, centro_y - 60, topo)

    # Mão
    minha_mao = estado_local.maos.get(meu_id, [])
    areas_cartas = []
    largura_carta = 80
    espacamento = 50
    total_largura = (len(minha_mao) - 1) * espacamento + largura_carta
    inicio_x = centro_x - total_largura // 2
    mouse_pos = pygame.mouse.get_pos()

    for i, carta in enumerate(minha_mao):
        pos_x = inicio_x + i * espacamento
        pos_y = ALTURA_TELA - 140
        rect_temp = pygame.Rect(pos_x, pos_y, largura_carta, 120)
        is_hover = rect_temp.collidepoint(mouse_pos)
        if i < len(minha_mao) - 1 and not is_hover: rect_temp.width = espacamento
        rect_final = desenhar_carta_estilizada(pos_x, pos_y, carta, hover=is_hover)
        areas_cartas.append((rect_final, i))
    
    # Seletor de Cor (Overlay)
    botoes_cor = []
    if escolhendo_cor:
        s = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
        s.fill((0,0,0, 180))
        win.blit(s, (0,0))
        
        txt = FONT_AVISO.render("ESCOLHA UMA COR", True, BRANCO)
        win.blit(txt, txt.get_rect(center=(LARGURA_TELA//2, 250)))
        
        cx, cy = LARGURA_TELA//2, ALTURA_TELA//2
        botoes_cor = [
            Botao(cx - 110, cy - 60, 100, 100, "", VERMELHO, 'VERMELHO'),
            Botao(cx + 10, cy - 60, 100, 100, "", AZUL, 'AZUL'),
            Botao(cx - 110, cy + 50, 100, 100, "", VERDE, 'VERDE'),
            Botao(cx + 10, cy + 50, 100, 100, "", AMARELO, 'AMARELO')
        ]
        for btn in botoes_cor: btn.desenhar(win)

    # Botão GRITAR UNO
    btn_uno = None
    alguem_vulneravel = False
    for pid in estado_local.jogadores_conectados:
        if len(estado_local.maos.get(pid, [])) == 1:
            # Só mostra o botão se alguém com 1 carta NÃO estiver safe
            if pid not in estado_local.uno_safe:
                alguem_vulneravel = True
                break
    
    if alguem_vulneravel:
        # Desenha botão piscante ou destacado
        cor_btn = VERMELHO
        if int(time.time() * 2) % 2 == 0: # Pisca
            cor_btn = (255, 100, 100)
            
        btn_uno = Botao(LARGURA_TELA - 140, ALTURA_TELA - 220, 120, 60, "UNO!", cor_btn, MSG_GRITAR_UNO)
        btn_uno.desenhar(win)

    return areas_cartas, btn_comprar, botoes_cor, btn_uno

# --- LOOP PRINCIPAL ---
run = True
clock = pygame.time.Clock()
enviar_acao({'tipo': MSG_LISTAR_SALAS}) # Pede lista inicial
ultimo_update = time.time()

while run:
    clock.tick(60)
    mouse_pos = pygame.mouse.get_pos()
    
    # Atualização automática do lobby
    if not em_sala and time.time() - ultimo_update > 1.0:
        enviar_acao({'tipo': MSG_LISTAR_SALAS})
        ultimo_update = time.time()
    
    btns_ativos = []
    areas_jogo = []
    btn_comprar_rect = None
    btns_cor = []

    if not em_sala:
        btns_ativos = tela_lobby()
    elif not estado_local or not estado_local.jogo_iniciado:
        btns_ativos = tela_config_sala()
    else:
        # VERIFICA VITORIA
        if estado_local.vencedor is not None:
            tela_jogo()
            s = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
            s.fill((0,0,0, 200))
            win.blit(s, (0,0))
            
            msg = f"JOGADOR {estado_local.vencedor} VENCEU!"
            if estado_local.vencedor == meu_id:
                msg = "VOCÊ VENCEU!"
                cor = VERDE
            else:
                cor = AMARELO
                
            txt = FONT_AVISO.render(msg, True, cor)
            win.blit(txt, txt.get_rect(center=(LARGURA_TELA//2, ALTURA_TELA//2)))
            
            txt_sub = FONT_INFO.render("Voltando ao lobby em 5 segundos...", True, BRANCO)
            win.blit(txt_sub, txt_sub.get_rect(center=(LARGURA_TELA//2, ALTURA_TELA//2 + 50)))
            
            pygame.display.update()
            time.sleep(5)
            
            enviar_acao({'tipo': MSG_SAIR_SALA})
            em_sala = False
            estado_local = None
            meu_id = None
            continue

        areas_jogo, btn_comprar_rect, btns_cor, btn_uno = tela_jogo()
        if escolhendo_cor:
            btns_ativos = btns_cor # Apenas botões de cor ativos
        if btn_uno:
            btns_ativos.append(btn_uno)

    # Hover nos botões
    for btn in btns_ativos:
        btn.hover = btn.rect.collidepoint(mouse_pos)

    pygame.display.update()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if em_sala:
                enviar_acao({'tipo': MSG_SAIR_SALA})
            run = False
            client.close()
            pygame.quit()
            sys.exit()
        
        # Input Box
        if not em_sala:
            input_sala.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            # LOBBY
            if not em_sala:
                for btn in btns_ativos:
                    acao = btn.checar_click(event.pos)
                    if acao == 'CRIAR':
                        nome = input_sala.text.strip()
                        if nome:
                            enviar_acao({'tipo': MSG_CRIAR_SALA, 'nome': nome})
                            # Tenta entrar logo em seguida (pequeno delay para servidor processar)
                            time.sleep(0.1)
                            enviar_acao({'tipo': MSG_ENTRAR_SALA, 'nome': nome})
                    elif isinstance(acao, dict) and acao['tipo'] == 'ENTRAR':
                        enviar_acao({'tipo': MSG_ENTRAR_SALA, 'nome': acao['nome']})
            
            # CONFIG SALA
            elif not estado_local.jogo_iniciado:
                if meu_id == estado_local.host_id:
                    for btn in btns_ativos:
                        acao = btn.checar_click(event.pos)
                        if acao == 'INICIAR':
                            # Só envia se tiver gente suficiente (validação visual já feita, mas bom garantir)
                            if len(estado_local.jogadores_conectados) >= 2:
                                enviar_acao({'tipo': MSG_INICIAR_JOGO})
            
            # JOGO
            elif estado_local.jogo_iniciado:
                
                # Ações Globais (UNO)
                if btn_uno and btn_uno.checar_click(event.pos):
                    enviar_acao({'tipo': MSG_GRITAR_UNO})

                # Ações de Turno
                elif estado_local.jogadores_conectados[estado_local.jogador_atual] == meu_id:
                
                    # Se estiver escolhendo cor
                    if escolhendo_cor:
                        for btn in btns_ativos: # btns_ativos são os de cor aqui
                            cor_escolhida = btn.checar_click(event.pos)
                            if cor_escolhida:
                                enviar_acao({'tipo': 'JOGAR', 'indice': carta_preta_pendente, 'cor_escolhida': cor_escolhida})
                                escolhendo_cor = False
                                carta_preta_pendente = None
                    
                    else:
                        jogou = False
                        for rect, indice in reversed(areas_jogo):
                            if rect.collidepoint(event.pos):
                                # Verifica se é carta preta antes de enviar
                                mao = estado_local.maos[meu_id]
                                if indice < len(mao):
                                    carta = mao[indice]
                                    if carta.cor == 'PRETO':
                                        escolhendo_cor = True
                                        carta_preta_pendente = indice
                                    else:
                                        enviar_acao({'tipo': 'JOGAR', 'indice': indice})
                                jogou = True
                                break
                        if not jogou and btn_comprar_rect and btn_comprar_rect.collidepoint(event.pos):
                            enviar_acao({'tipo': 'COMPRAR'})

pygame.quit()

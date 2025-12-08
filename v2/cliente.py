"""
ARQUIVO: cliente.py
FUNÇÃO: Interface Gráfica (GUI) e comunicação com o servidor.
TECNOLOGIAS: Pygame (visual) e Sockets (rede).
DESCRIÇÃO: Este arquivo contém toda a lógica do cliente, desde a conexão com o servidor,
renderização das telas (Lobby, Sala de Espera, Jogo), tratamento de eventos (cliques, teclado)
e sincronização de estado via rede.
"""

import pygame    # Biblioteca para criação de jogos (gráficos, eventos, som)
import socket    # Biblioteca para comunicação de rede (TCP/IP)
import pickle    # Biblioteca para serialização de objetos (enviar dados complexos pela rede)
import threading # Biblioteca para rodar processos em paralelo (escutar o servidor sem travar o jogo)
import math      # Funções matemáticas (usado para desenhar setas e cálculos geométricos)
import time      # Funções de tempo (delay, controle de FPS)
import sys       # Funções do sistema (encerrar o programa)
# Importa as constantes e classes compartilhadas do protocolo
from protocolo import EstadoJogo, MSG_CRIAR_SALA, MSG_ENTRAR_SALA, MSG_LISTAR_SALAS, MSG_INICIAR_JOGO, MSG_GRITAR_UNO, MSG_SAIR_SALA, MSG_ERRO

# --- CONFIGURAÇÃO DE REDE ---
# Cria o socket do cliente usando IPv4 (AF_INET) e TCP (SOCK_STREAM)
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

print("=== Configuração de Conexão ===")
# Solicita o IP do servidor ao usuário. Se vazio, usa localhost.
server_ip = input("Digite o IP do servidor (pressione Enter para localhost): ").strip()
if not server_ip:
    server_ip = 'localhost'

try:
    # Tenta conectar ao servidor na porta 5555
    client.connect((server_ip, 5555))
except Exception as e:
    print(f"Não foi possível conectar ao servidor em {server_ip}:5555")
    print(f"Erro: {e}")
    exit() # Encerra o programa se não conseguir conectar

# --- CONFIGURAÇÃO PYGAME ---
pygame.display.init() # Inicializa o módulo de display do Pygame
pygame.font.init()    # Inicializa o módulo de fontes do Pygame

# Definição das dimensões da janela
LARGURA_TELA = 1000
ALTURA_TELA = 700
# Cria a janela do jogo
win = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
pygame.display.set_caption("UNO Multiplayer - Lobby") # Define o título da janela

# --- CORES E ESTILOS ---
# Definição de cores em formato RGB (Red, Green, Blue)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
CINZA_FUNDO = (30, 30, 30)   # Cor de fundo do Lobby
VERDE_MESA = (34, 139, 34)   # Cor de fundo da mesa de jogo (verde feltro)
VERMELHO = (235, 50, 50)     # Cores das cartas UNO
VERDE = (50, 200, 50)
AZUL = (50, 50, 235)
AMARELO = (245, 215, 20)
CINZA_CARTA = (50, 50, 50)   # Cor para cartas ocultas ou fundo neutro

# Mapa para converter strings de cor (do protocolo) para tuplas RGB
MAPA_CORES = {
    'VERMELHO': VERMELHO, 'VERDE': VERDE, 'AZUL': AZUL, 'AMARELO': AMARELO, 'PRETO': PRETO
}

# Definição das fontes usadas no jogo
FONT_INFO = pygame.font.SysFont('Arial', 24, bold=True)      # Texto geral
FONT_AVISO = pygame.font.SysFont('Arial', 36, bold=True)     # Títulos e avisos grandes
FONT_CARTA = pygame.font.SysFont('Arial', 40, bold=True)     # Símbolo central da carta
FONT_CARTA_PQ = pygame.font.SysFont('Arial', 14, bold=True)  # Símbolo pequeno nos cantos

# --- ESTADO DO CLIENTE ---
# Variáveis globais que armazenam o estado atual do jogo no cliente
estado_local = None         # Cópia do objeto EstadoJogo recebido do servidor
meu_id = None               # ID deste cliente (atribuído pelo servidor)
em_sala = False             # Flag indicando se o cliente está em uma sala ou no lobby
lista_salas = []            # Lista de salas disponíveis (para o lobby)
mensagem_erro = ""          # Mensagem de erro para exibir na tela (ex: "Sala cheia")
escolhendo_cor = False      # Flag para abrir o menu de escolha de cor (Coringa/+4)
carta_preta_pendente = None # Índice da carta preta que foi clicada (aguardando escolha de cor)

# --- CLASSES AUXILIARES ---
class Botao:
    """
    Classe para criar botões interativos na interface.
    """
    def __init__(self, x, y, w, h, texto, cor, acao):
        self.rect = pygame.Rect(x, y, w, h) # Retângulo de colisão do botão
        self.texto = texto                  # Texto exibido no botão
        self.cor = cor                      # Cor de fundo do botão
        self.acao = acao                    # Ação associada (string ou dict) retornada ao clicar
        self.hover = False                  # Estado de hover (mouse em cima)

    def desenhar(self, tela):
        """Desenha o botão na tela, mudando a cor se o mouse estiver em cima."""
        # Clareia a cor se estiver em hover
        cor_atual = tuple(min(c + 30, 255) for c in self.cor) if self.hover else self.cor
        pygame.draw.rect(tela, cor_atual, self.rect, border_radius=12)
        pygame.draw.rect(tela, BRANCO, self.rect, width=2, border_radius=12) # Borda branca
        
        # Renderiza o texto centralizado
        fonte = pygame.font.SysFont('Arial', 20, bold=True)
        txt = fonte.render(self.texto, True, BRANCO)
        txt_rect = txt.get_rect(center=self.rect.center)
        tela.blit(txt, txt_rect)

    def checar_click(self, pos):
        """Verifica se o clique (pos) foi dentro do botão e retorna a ação."""
        if self.rect.collidepoint(pos):
            return self.acao
        return None

class InputBox:
    """
    Classe para criar caixas de entrada de texto (para digitar nome da sala).
    """
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = CINZA_CARTA
        self.text = text
        self.txt_surface = FONT_INFO.render(text, True, BRANCO)
        self.active = False # Indica se a caixa está focada para digitação

    def handle_event(self, event):
        """Trata eventos de mouse e teclado para a caixa de texto."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Ativa se clicar dentro, desativa se clicar fora
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = AZUL if self.active else CINZA_CARTA # Muda cor quando ativo
        
        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    return self.text # Retorna o texto ao dar Enter
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1] # Apaga caractere
                else:
                    self.text += event.unicode # Adiciona caractere digitado
                # Atualiza a superfície de texto
                self.txt_surface = FONT_INFO.render(self.text, True, BRANCO)
        return None

    def draw(self, screen):
        """Desenha a caixa de texto na tela."""
        pygame.draw.rect(screen, self.color, self.rect, 2) # Borda
        screen.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5)) # Texto

# --- FUNÇÕES DE REDE ---
def enviar_acao(acao):
    """Envia um objeto (dicionário) para o servidor via pickle."""
    try:
        client.send(pickle.dumps(acao))
    except:
        print("Erro ao enviar dados para o servidor.")

def receber_dados():
    """
    Função executada em uma thread separada.
    Fica num loop infinito escutando mensagens do servidor e atualizando o estado global.
    """
    global estado_local, meu_id, em_sala, lista_salas, mensagem_erro
    while True:
        try:
            # Recebe dados do servidor (buffer grande para garantir recebimento do estado completo)
            data = client.recv(4096 * 8)
            if not data: break
            
            msg = pickle.loads(data) # Deserializa a mensagem
            
            # Se for um dicionário, é uma mensagem de controle ou atualização simples
            if isinstance(msg, dict):
                if msg.get('tipo') == MSG_LISTAR_SALAS:
                    lista_salas = msg['salas']
                elif msg.get('tipo') == MSG_ERRO:
                    mensagem_erro = msg['msg']
                    print(f"Erro do servidor: {mensagem_erro}")
                elif msg.get('tipo') == 'SUCESSO_CRIAR':
                    # Sala criada com sucesso
                    pass 
                elif msg.get('tipo') == 'ENTROU':
                    # Confirmação de entrada na sala
                    meu_id = msg['id']
                    em_sala = True
                    # A atualização do caption será feita no loop principal para evitar crash
            
            # Se for uma instância de EstadoJogo, é a atualização completa do jogo
            elif isinstance(msg, EstadoJogo):
                estado_local = msg
                
        except Exception as e:
            print(f"Erro na thread de rede: {e}")
            break

# Inicia a thread de rede em modo daemon (fecha quando o programa principal fechar)
thread_rede = threading.Thread(target=receber_dados, daemon=True)
thread_rede.start()

# --- FUNÇÕES DE DESENHO (JOGO) ---
def get_simbolo_visual(valor):
    """Converte valores especiais para símbolos visuais curtos."""
    if valor == 'PULAR': return "Ø"      # Símbolo de proibido
    if valor == 'INVERTER': return "R"   # Reverse
    if valor == 'CORINGA': return "C"    # Coringa
    return valor

def desenhar_carta_estilizada(x, y, carta, hover=False, oculto=False):
    """
    Desenha uma carta de UNO na tela.
    Args:
        x, y: Posição top-left.
        carta: Objeto Carta.
        hover: Se True, desenha a carta um pouco mais para cima (efeito visual).
        oculto: Se True, desenha o verso da carta (UNO).
    Returns:
        pygame.Rect: O retângulo da carta desenhada (para detecção de clique).
    """
    largura = 80
    altura = 120
    if hover and not oculto: y -= 20 # Efeito de "levantar" a carta
    rect = pygame.Rect(x, y, largura, altura)
    
    # Sombra da carta
    pygame.draw.rect(win, (0,0,0, 100), (x+3, y+3, largura, altura), border_radius=10)

    if oculto:
        # Desenha o verso da carta (Preto com borda vermelha e logo UNO)
        pygame.draw.rect(win, PRETO, rect, border_radius=10)
        pygame.draw.rect(win, VERMELHO, rect, width=3, border_radius=10)
        pygame.draw.circle(win, AMARELO, (x + largura//2, y + altura//2), 25)
        txt = FONT_CARTA_PQ.render("UNO", True, VERMELHO)
        win.blit(txt, txt.get_rect(center=rect.center))
    else:
        # Desenha a frente da carta
        cor_fundo = MAPA_CORES.get(carta.cor, CINZA_CARTA)
        pygame.draw.rect(win, cor_fundo, rect, border_radius=10)
        pygame.draw.rect(win, BRANCO, rect, width=3, border_radius=10)
        # Elipse branca no centro (design clássico do UNO)
        pygame.draw.ellipse(win, BRANCO, (x+10, y+20, largura-20, altura-40))
        
        # Símbolo central
        simbolo = get_simbolo_visual(carta.valor)
        cor_texto = cor_fundo if carta.cor != 'PRETO' else PRETO
        txt_centro = FONT_CARTA.render(simbolo, True, cor_texto)
        if len(simbolo) > 1: 
            # Ajusta fonte para símbolos largos (+2, +4)
            txt_centro = pygame.font.SysFont('Arial', 30, bold=True).render(simbolo, True, cor_texto)
        win.blit(txt_centro, txt_centro.get_rect(center=rect.center))
        
        # Símbolos pequenos nos cantos
        txt_pq = FONT_CARTA_PQ.render(simbolo, True, BRANCO)
        win.blit(txt_pq, (x+5, y+5))
        win.blit(txt_pq, (x+largura-20, y+altura-20))
    return rect

def desenhar_setas_direcao(centro_x, centro_y, sentido_horario):
    """Desenha setas indicando o sentido do jogo (horário ou anti-horário)."""
    raio = 130
    cor_dir = AMARELO if sentido_horario else AZUL
    direcao = 1 if sentido_horario else -1
    
    # Desenha 3 arcos ao redor do centro
    for i in range(3):
        angulo_base = i * 120
        angulo_inicio = math.radians(angulo_base + 20)
        angulo_fim = math.radians(angulo_base + 100)
        rect_arc = pygame.Rect(centro_x - raio, centro_y - raio, raio*2, raio*2)
        pygame.draw.arc(win, cor_dir, rect_arc, angulo_inicio, angulo_fim, 5)
        
        # Desenha a ponta da seta (círculo simples para indicar direção)
        ponta_angle = angulo_inicio if direcao == 1 else angulo_fim
        ponta_x = centro_x + raio * math.cos(ponta_angle)
        ponta_y = centro_y - raio * math.sin(ponta_angle)
        pygame.draw.circle(win, cor_dir, (int(ponta_x), int(ponta_y)), 10)

# --- TELAS ---
input_sala = InputBox(350, 150, 300, 40, '') # Instância global da caixa de input

def tela_lobby():
    """Renderiza a tela inicial (Lobby) onde se cria ou escolhe salas."""
    win.fill(CINZA_FUNDO)
    titulo = FONT_AVISO.render("LOBBY UNO", True, BRANCO)
    win.blit(titulo, titulo.get_rect(center=(LARGURA_TELA//2, 50)))

    # Seção de Criar Sala
    txt_criar = FONT_INFO.render("Nome da Nova Sala:", True, BRANCO)
    win.blit(txt_criar, (350, 120))
    input_sala.draw(win)
    btn_criar = Botao(660, 150, 100, 40, "CRIAR", VERDE, 'CRIAR')
    btn_criar.desenhar(win)

    # Seção de Lista de Salas
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
        
    # Exibe mensagem de erro se houver
    if mensagem_erro:
        erro = FONT_INFO.render(mensagem_erro, True, VERMELHO)
        win.blit(erro, (LARGURA_TELA//2 - erro.get_width()//2, 600))

    return [btn_criar] + botoes_salas # Retorna botões ativos para checagem de clique

def tela_config_sala():
    """Renderiza a sala de espera antes do jogo começar."""
    win.fill(CINZA_FUNDO)
    titulo = FONT_AVISO.render("SALA DE ESPERA", True, BRANCO)
    win.blit(titulo, titulo.get_rect(center=(LARGURA_TELA//2, 50)))
    
    if not estado_local:
        return []

    # Lista de Jogadores Conectados
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
    # Se for o anfitrião, mostra botão de iniciar
    if meu_id == estado_local.host_id:
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
    """
    Desenha as cartas (verso) dos oponentes em posições relativas (Topo, Esquerda, Direita).
    """
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
            
            if ativo: # Destaca se for a vez deste jogador
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
            txt = pygame.transform.rotate(txt, -90) # Rotaciona texto
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
            txt = pygame.transform.rotate(txt, 90) # Rotaciona texto
            win.blit(txt, txt.get_rect(center=rect.center))
            
            if ativo:
                pygame.draw.rect(win, AMARELO, rect, width=3, border_radius=10)

def tela_jogo():
    """Renderiza a tela principal do jogo."""
    win.fill(VERDE_MESA)
    if not estado_local: return [], None, []

    centro_x, centro_y = LARGURA_TELA // 2, ALTURA_TELA // 2

    # Identifica de quem é a vez
    jogador_vez_id = estado_local.jogadores_conectados[estado_local.jogador_atual]
    
    # Se for minha vez, avisa grande embaixo
    if jogador_vez_id == meu_id:
        txt_obj = FONT_AVISO.render("SUA VEZ!", True, AMARELO)
        win.blit(txt_obj, txt_obj.get_rect(center=(centro_x, ALTURA_TELA - 180)))

    # Desenha setas de direção
    desenhar_setas_direcao(centro_x, centro_y, estado_local.sentido_horario)
    
    # --- DESENHAR OPONENTES ---
    # Lógica para posicionar os oponentes na mesa dependendo do número de jogadores
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

    # --- MONTE DE COMPRA ---
    rect_monte = pygame.Rect(centro_x - 100, centro_y - 60, 80, 120)
    pygame.draw.rect(win, PRETO, rect_monte, border_radius=10)
    pygame.draw.rect(win, BRANCO, rect_monte, width=2, border_radius=10)
    win.blit(FONT_CARTA_PQ.render("Monte", True, BRANCO), (centro_x - 90, centro_y - 15))
    btn_comprar = rect_monte

    # --- PILHA DE DESCARTE ---
    if estado_local.descarte:
        topo = estado_local.descarte[-1]
        
        # Se a carta for preta, desenha o fundo com a cor atual do jogo (para indicar qual cor foi escolhida)
        cor_fundo_topo = CINZA_CARTA
        if topo.cor == 'PRETO' and estado_local.cor_atual:
             cor_fundo_topo = MAPA_CORES.get(estado_local.cor_atual, CINZA_CARTA)
             pygame.draw.rect(win, cor_fundo_topo, (centro_x + 10, centro_y - 70, 100, 140), border_radius=15)
        
        desenhar_carta_estilizada(centro_x + 20, centro_y - 60, topo)

    # --- MINHA MÃO ---
    minha_mao = estado_local.maos.get(meu_id, [])
    areas_cartas = []
    largura_carta = 80
    espacamento = 50
    # Calcula largura total para centralizar
    total_largura = (len(minha_mao) - 1) * espacamento + largura_carta
    inicio_x = centro_x - total_largura // 2
    mouse_pos = pygame.mouse.get_pos()

    for i, carta in enumerate(minha_mao):
        pos_x = inicio_x + i * espacamento
        pos_y = ALTURA_TELA - 140
        rect_temp = pygame.Rect(pos_x, pos_y, largura_carta, 120)
        
        # Efeito de hover: se mouse em cima, mostra a carta inteira (não sobreposta)
        is_hover = rect_temp.collidepoint(mouse_pos)
        if i < len(minha_mao) - 1 and not is_hover: rect_temp.width = espacamento
        
        rect_final = desenhar_carta_estilizada(pos_x, pos_y, carta, hover=is_hover)
        areas_cartas.append((rect_final, i))
    
    # --- SELETOR DE COR (OVERLAY) ---
    botoes_cor = []
    if escolhendo_cor:
        # Escurece o fundo
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

    # --- BOTÃO GRITAR UNO ---
    btn_uno = None
    alguem_vulneravel = False
    # Verifica se alguém tem 1 carta e não gritou UNO (não está safe)
    for pid in estado_local.jogadores_conectados:
        if len(estado_local.maos.get(pid, [])) == 1:
            if pid not in estado_local.uno_safe:
                alguem_vulneravel = True
                break
    
    if alguem_vulneravel:
        # Desenha botão piscante ou destacado
        cor_btn = VERMELHO
        if int(time.time() * 2) % 2 == 0: # Pisca a cada 0.5s
            cor_btn = (255, 100, 100)
            
        btn_uno = Botao(LARGURA_TELA - 140, ALTURA_TELA - 220, 120, 60, "UNO!", cor_btn, MSG_GRITAR_UNO)
        btn_uno.desenhar(win)

    return areas_cartas, btn_comprar, botoes_cor, btn_uno

# --- LOOP PRINCIPAL ---
run = True
clock = pygame.time.Clock()
enviar_acao({'tipo': MSG_LISTAR_SALAS}) # Pede lista inicial de salas ao conectar
ultimo_update = time.time()
ultimo_estado_sala = False

while run:
    clock.tick(60) # Limita a 60 FPS
    
    # Atualiza caption se mudou de sala/lobby
    if em_sala != ultimo_estado_sala:
        if em_sala and meu_id is not None:
             pygame.display.set_caption(f"UNO - Jogador {meu_id}")
        else:
             pygame.display.set_caption("UNO Multiplayer - Lobby")
        ultimo_estado_sala = em_sala

    mouse_pos = pygame.mouse.get_pos()
    
    # Atualização automática da lista de salas no lobby (polling a cada 1s)
    if not em_sala and time.time() - ultimo_update > 1.0:
        enviar_acao({'tipo': MSG_LISTAR_SALAS})
        ultimo_update = time.time()
    
    # Listas de elementos interativos
    btns_ativos = []
    areas_jogo = []
    btn_comprar_rect = None
    btns_cor = []

    # --- RENDERIZAÇÃO DAS TELAS ---
    if not em_sala:
        btns_ativos = tela_lobby()
    elif not estado_local or not estado_local.jogo_iniciado:
        btns_ativos = tela_config_sala()
    else:
        # VERIFICA VITORIA
        if estado_local.vencedor is not None:
            tela_jogo() # Desenha o fundo do jogo
            # Overlay de vitória
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
            
            # Reseta estado local e volta ao lobby
            enviar_acao({'tipo': MSG_SAIR_SALA})
            em_sala = False
            estado_local = None
            meu_id = None
            continue

        # Renderiza jogo normal
        areas_jogo, btn_comprar_rect, btns_cor, btn_uno = tela_jogo()
        if escolhendo_cor:
            btns_ativos = btns_cor # Apenas botões de cor ativos se estiver escolhendo
        if btn_uno:
            btns_ativos.append(btn_uno)

    # Atualiza estado de hover nos botões
    for btn in btns_ativos:
        btn.hover = btn.rect.collidepoint(mouse_pos)

    pygame.display.update()

    # --- TRATAMENTO DE EVENTOS ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if em_sala:
                enviar_acao({'tipo': MSG_SAIR_SALA})
            run = False
            client.close()
            pygame.quit()
            sys.exit()
        
        # Input Box (apenas no lobby)
        if not em_sala:
            input_sala.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            # LÓGICA DO LOBBY
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
            
            # LÓGICA DA SALA DE ESPERA
            elif not estado_local.jogo_iniciado:
                if meu_id == estado_local.host_id:
                    for btn in btns_ativos:
                        acao = btn.checar_click(event.pos)
                        if acao == 'INICIAR':
                            # Só envia se tiver gente suficiente (validação visual já feita, mas bom garantir)
                            if len(estado_local.jogadores_conectados) >= 2:
                                enviar_acao({'tipo': MSG_INICIAR_JOGO})
            
            # LÓGICA DO JOGO
            elif estado_local.jogo_iniciado:
                
                # Ações Globais (UNO) - Pode ser clicado a qualquer momento se disponível
                if btn_uno and btn_uno.checar_click(event.pos):
                    enviar_acao({'tipo': MSG_GRITAR_UNO})

                # Ações de Turno (Só se for minha vez)
                elif estado_local.jogadores_conectados[estado_local.jogador_atual] == meu_id:
                
                    # Se estiver escolhendo cor (após jogar +4 ou Coringa)
                    if escolhendo_cor:
                        for btn in btns_ativos: # btns_ativos são os de cor aqui
                            cor_escolhida = btn.checar_click(event.pos)
                            if cor_escolhida:
                                enviar_acao({'tipo': 'JOGAR', 'indice': carta_preta_pendente, 'cor_escolhida': cor_escolhida})
                                escolhendo_cor = False
                                carta_preta_pendente = None
                    
                    else:
                        # Tenta jogar uma carta da mão
                        jogou = False
                        for rect, indice in reversed(areas_jogo): # Reversed para checar as de cima primeiro (se sobrepostas)
                            if rect.collidepoint(event.pos):
                                # Verifica se é carta preta antes de enviar
                                mao = estado_local.maos[meu_id]
                                if indice < len(mao):
                                    carta = mao[indice]
                                    if carta.cor == 'PRETO':
                                        # Se for preta, abre menu de cor e não envia ainda
                                        escolhendo_cor = True
                                        carta_preta_pendente = indice
                                    else:
                                        # Se for normal, envia jogada
                                        enviar_acao({'tipo': 'JOGAR', 'indice': indice})
                                jogou = True
                                break
                        
                        # Se não clicou em carta, verifica se clicou no monte de comprar
                        if not jogou and btn_comprar_rect and btn_comprar_rect.collidepoint(event.pos):
                            enviar_acao({'tipo': 'COMPRAR'})

pygame.quit()

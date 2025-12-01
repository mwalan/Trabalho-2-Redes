import pygame
import random
import sys
import time
import math

# --- CONFIGURAÇÕES DO JOGO ---
LARGURA_TELA = 1000
ALTURA_TELA = 700
FPS = 60

# Cores (R, G, B)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
CINZA_FUNDO = (30, 30, 30)
VERDE_MESA = (34, 139, 34)
VERMELHO = (235, 50, 50)
VERDE = (50, 200, 50)
AZUL = (50, 50, 235)
AMARELO = (245, 215, 20)
CINZA_CARTA = (50, 50, 50)

# Mapeamento de cores
CORES_UNO = {
    'red': VERMELHO,
    'green': VERDE,
    'blue': AZUL,
    'yellow': AMARELO,
    'black': PRETO
}

class Carta:
    def __init__(self, cor, tipo, valor=None):
        self.cor = cor      # 'red', 'blue', 'green', 'yellow', 'black'
        self.tipo = tipo    # 'number', 'skip', 'reverse', 'draw2', 'wild', 'wild4'
        self.valor = valor  # 0-9 se for numero, None se acao
        self.rect = None    # Definido ao desenhar
        self.x = 0
        self.y = 0

    def get_nome_display(self):
        if self.tipo == 'number':
            return str(self.valor)
        if self.tipo == 'skip':
            return "Ø"
        if self.tipo == 'reverse':
            return "R"
        if self.tipo == 'draw2':
            return "+2"
        if self.tipo == 'wild':
            return "C" # Coringa
        if self.tipo == 'wild4':
            return "+4"
        return "?"

    def desenhar(self, superficie, x, y, oculto=False, hover=False):
        self.x = x
        self.y = y
        largura = 80
        altura = 120
        
        # Efeito de hover (sobe um pouco)
        if hover and not oculto:
            y -= 20

        self.rect = pygame.Rect(x, y, largura, altura)

        # Sombra
        sombra = pygame.Rect(x + 3, y + 3, largura, altura)
        pygame.draw.rect(superficie, (0,0,0, 100), sombra, border_radius=10)

        if oculto:
            pygame.draw.rect(superficie, PRETO, self.rect, border_radius=10)
            pygame.draw.rect(superficie, VERMELHO, self.rect, width=3, border_radius=10)
            # Decoracao verso
            pygame.draw.circle(superficie, AMARELO, (x + largura//2, y + altura//2), 25)
            fonte = pygame.font.SysFont('Arial', 20, bold=True)
            texto = fonte.render("UNO", True, VERMELHO)
            texto_rect = texto.get_rect(center=(x + largura//2, y + altura//2))
            superficie.blit(texto, texto_rect)
        else:
            cor_fundo = CORES_UNO.get(self.cor, CINZA_CARTA)
            pygame.draw.rect(superficie, cor_fundo, self.rect, border_radius=10)
            pygame.draw.rect(superficie, BRANCO, self.rect, width=3, border_radius=10)

            # Oval central branca
            oval_rect = pygame.Rect(x + 10, y + 20, largura - 20, altura - 40)
            pygame.draw.ellipse(superficie, BRANCO, oval_rect)

            # Texto central
            simbolo = self.get_nome_display()
            cor_texto = cor_fundo if self.cor != 'black' else (50, 50, 50)
            
            # Ajuste de fonte para simbolos
            tamanho_fonte = 40
            if len(simbolo) > 1: tamanho_fonte = 30
            
            fonte = pygame.font.SysFont('Arial', tamanho_fonte, bold=True)
            texto = fonte.render(simbolo, True, cor_texto)
            texto_rect = texto.get_rect(center=(x + largura//2, y + altura//2))
            superficie.blit(texto, texto_rect)

            # Texto cantos
            fonte_pq = pygame.font.SysFont('Arial', 14, bold=True)
            txt_pq = fonte_pq.render(simbolo, True, BRANCO)
            superficie.blit(txt_pq, (x + 5, y + 5))
            superficie.blit(txt_pq, (x + largura - 20, y + altura - 20))

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
        
        fonte = pygame.font.SysFont('Arial', 24, bold=True)
        txt = fonte.render(self.texto, True, BRANCO)
        txt_rect = txt.get_rect(center=self.rect.center)
        tela.blit(txt, txt_rect)

    def checar_click(self, pos):
        if self.rect.collidepoint(pos):
            return self.acao
        return None

def gerar_baralho():
    baralho = []
    cores = ['red', 'blue', 'green', 'yellow']
    
    for cor in cores:
        # 0
        baralho.append(Carta(cor, 'number', 0))
        # 1-9 (dois de cada)
        for i in range(1, 10):
            baralho.append(Carta(cor, 'number', i))
            baralho.append(Carta(cor, 'number', i))
        # Acoes (dois de cada)
        for tipo in ['skip', 'reverse', 'draw2']:
            baralho.append(Carta(cor, tipo))
            baralho.append(Carta(cor, tipo))
    
    # Wilds (4 de cada)
    for _ in range(4):
        baralho.append(Carta('black', 'wild'))
        baralho.append(Carta('black', 'wild4'))
    
    random.shuffle(baralho)
    return baralho

class Jogo:
    def __init__(self):
        pygame.init()
        self.tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
        pygame.display.set_caption("Uno Pygame - Multiplayer Local")
        self.relogio = pygame.time.Clock()
        self.fonte_info = pygame.font.SysFont('Arial', 24, bold=True)
        self.fonte_aviso = pygame.font.SysFont('Arial', 36, bold=True)

        self.estado = 'MENU' # MENU, JOGANDO, COR_PICKER, GAMEOVER
        self.modo_jogo = '' # '2P', '4P', '2V2'
        
        self.baralho = []
        self.pilha_descarte = []
        self.jogadores = [] # Lista de dics: {'id': 0, 'mao': [], 'bot': F, 'nome': '', 'time': 1}
        self.turno_idx = 0
        self.direcao = 1
        self.cor_atual = ''
        
        self.mensagem = ""
        self.vencedor = None
        self.comprou_no_turno = False
        
        # UI Buttons
        self.botoes_menu = [
            Botao(350, 300, 300, 60, "1 vs 1 (Local)", AZUL, '2P'),
            Botao(350, 380, 300, 60, "4 Jogadores (Local)", VERMELHO, '4P'),
            Botao(350, 460, 300, 60, "2 vs 2 (Local)", VERDE, '2V2')
        ]
        
        self.botoes_cor = [
            Botao(300, 300, 100, 100, "", VERMELHO, 'red'),
            Botao(410, 300, 100, 100, "", AZUL, 'blue'),
            Botao(300, 410, 100, 100, "", VERDE, 'green'),
            Botao(410, 410, 100, 100, "", AMARELO, 'yellow')
        ]
        
        self.botao_reiniciar = Botao(350, 500, 300, 60, "Voltar ao Menu", CINZA_CARTA, 'MENU')

    def iniciar_partida(self, modo):
        self.modo_jogo = modo
        self.baralho = gerar_baralho()
        self.jogadores = []
        self.direcao = 1
        self.turno_idx = 0
        self.comprou_no_turno = False
        self.mensagem = "Vez do Jogador 1!"

        if modo == '2P':
            self.jogadores.append({'id': 0, 'mao': [], 'bot': False, 'nome': 'Jogador 1', 'time': 1})
            self.jogadores.append({'id': 1, 'mao': [], 'bot': False, 'nome': 'Jogador 2', 'time': 2})
        elif modo == '4P':
            nomes = ['Jogador 1', 'Jogador 2', 'Jogador 3', 'Jogador 4']
            for i in range(4):
                self.jogadores.append({'id': i, 'mao': [], 'bot': False, 'nome': nomes[i], 'time': i})
        elif modo == '2V2':
            # Time 1: 0 e 2. Time 2: 1 e 3
            self.jogadores.append({'id': 0, 'mao': [], 'bot': False, 'nome': 'J1 (Time 1)', 'time': 1})
            self.jogadores.append({'id': 1, 'mao': [], 'bot': False, 'nome': 'J2 (Time 2)', 'time': 2})
            self.jogadores.append({'id': 2, 'mao': [], 'bot': False, 'nome': 'J3 (Time 1)', 'time': 1})
            self.jogadores.append({'id': 3, 'mao': [], 'bot': False, 'nome': 'J4 (Time 2)', 'time': 2})

        # Distribuir cartas
        for _ in range(7):
            for p in self.jogadores:
                if self.baralho:
                    p['mao'].append(self.baralho.pop())

        # Primeira carta
        while True:
            carta = self.baralho.pop()
            if carta.tipo != 'wild4':
                self.pilha_descarte = [carta]
                self.cor_atual = carta.cor if carta.cor != 'black' else 'red'
                break
            else:
                self.baralho.insert(0, carta)

        self.estado = 'JOGANDO'

    def desenhar_mesa(self):
        self.tela.fill(VERDE_MESA)
        
        # Info Topo
        txt_status = self.fonte_info.render(f"Cor Atual: {self.cor_atual.upper()} | {self.mensagem}", True, BRANCO)
        self.tela.blit(txt_status, (20, 20))
        
        # Centro e Coordenadas
        centro_x, centro_y = LARGURA_TELA // 2, ALTURA_TELA // 2
        
        # --- Indicador de Direcao (Setas Circulares) ---
        raio = 130
        espessura = 5
        cor_dir = AMARELO if self.direcao == 1 else AZUL
        
        # Desenhar 3 arcos
        for i in range(3):
            # Defasagem de 120 graus
            angulo_base = i * 120
            # Arcos de ~80 graus
            angulo_inicio = math.radians(angulo_base + 20)
            angulo_fim = math.radians(angulo_base + 100)
            
            rect_arc = pygame.Rect(centro_x - raio, centro_y - raio, raio*2, raio*2)
            pygame.draw.arc(self.tela, cor_dir, rect_arc, angulo_inicio, angulo_fim, espessura)
            
            # Desenhar triangulo (seta)
            delta = 0.15 # tamanho angular da seta
            
            if self.direcao == 1: # Horario
                # Seta no inicio do arco (menor angulo)
                ponta_angle = angulo_inicio
                base_angle = angulo_inicio + delta
            else: # Anti-Horario
                # Seta no fim do arco (maior angulo)
                ponta_angle = angulo_fim
                base_angle = angulo_fim - delta
                
            ponta_x = centro_x + raio * math.cos(ponta_angle)
            ponta_y = centro_y - raio * math.sin(ponta_angle)
            
            base_x_in = centro_x + (raio - 12) * math.cos(base_angle)
            base_y_in = centro_y - (raio - 12) * math.sin(base_angle)
            
            base_x_out = centro_x + (raio + 12) * math.cos(base_angle)
            base_y_out = centro_y - (raio + 12) * math.sin(base_angle)
            
            pygame.draw.polygon(self.tela, cor_dir, [(ponta_x, ponta_y), (base_x_in, base_y_in), (base_x_out, base_y_out)])

        # --- Monte e Descarte ---
        pygame.draw.rect(self.tela, PRETO, (centro_x - 100, centro_y - 60, 80, 120), border_radius=10)
        pygame.draw.rect(self.tela, BRANCO, (centro_x - 100, centro_y - 60, 80, 120), width=2, border_radius=10)
        txt_monte = self.fonte_info.render("Monte", True, BRANCO)
        self.tela.blit(txt_monte, (centro_x - 90, centro_y - 15))
        
        # Descarte
        if self.pilha_descarte:
            topo = self.pilha_descarte[-1]
            if topo.cor == 'black':
                pygame.draw.rect(self.tela, CORES_UNO[self.cor_atual], (centro_x + 10, centro_y - 70, 100, 140), border_radius=15)
            
            topo.desenhar(self.tela, centro_x + 20, centro_y - 60)

        # --- Desenhar Jogadores e Cartas ---
        mouse_pos = pygame.mouse.get_pos()

        for p in self.jogadores:
            mao_size = len(p['mao'])
            eh_sua_vez = (p['id'] == self.turno_idx)
            
            # Definir posicao das cartas baseada no ID do jogador
            # ID 0: Baixo, ID 1: Esquerda, ID 2: Cima, ID 3: Direita (Se 4P/2v2)
            # Se 2P: ID 1: Cima

            # --- MODO 2 JOGADORES (Topo e Baixo) ---
            if len(self.jogadores) == 2 or p['id'] == 0 or (len(self.jogadores) > 2 and p['id'] == 2):
                # Layout HORIZONTAL
                offset_x = 40 if mao_size > 10 else 50
                largura_total = (max(0, mao_size - 1)) * offset_x + 80 # 80 = largura carta
                inicio_x = (LARGURA_TELA // 2) - (largura_total // 2)
                
                if p['id'] == 0: # Baixo (Sempre J1)
                    start_y = ALTURA_TELA - 140
                    nome_pos = (LARGURA_TELA//2 - 50, ALTURA_TELA - 170)
                else: # Topo (J2 no modo 2P, J3 no modo 4P)
                    start_y = 50
                    nome_pos = (LARGURA_TELA//2 - 50, 180) # Abaixo das cartas
                    if len(self.jogadores) == 2: nome_pos = (LARGURA_TELA//2 - 50, 180) 
                
                # Nome
                cor_nome = AMARELO if eh_sua_vez else BRANCO
                if eh_sua_vez: cor_nome = (255, 255, 0)
                txt_nome = self.fonte_info.render(f"{p['nome']} ({mao_size})", True, cor_nome)
                # Ajuste centralizado do nome
                rect_nome = txt_nome.get_rect(center=nome_pos)
                if p['id'] != 0 and len(self.jogadores) > 2: # J3
                     rect_nome.y = 180
                elif p['id'] != 0: # J2 (2P)
                     rect_nome.y = 180
                self.tela.blit(txt_nome, rect_nome)

                # Cartas
                for i, carta in enumerate(p['mao']):
                    cx = inicio_x + i * offset_x
                    cy = start_y
                    
                    hover = False
                    if eh_sua_vez and self.estado == 'JOGANDO':
                        rect_col = pygame.Rect(cx, cy, 80, 120)
                        if rect_col.collidepoint(mouse_pos): hover = True
                    
                    carta.desenhar(self.tela, cx, cy, oculto=False, hover=hover)
            
            # --- JOGADORES LATERAIS (Esquerda e Direita) ---
            else:
                # Layout VERTICAL (Para nao invadir o centro)
                offset_y = 30 if mao_size > 10 else 40
                altura_total = (max(0, mao_size - 1)) * offset_y + 120
                start_y = (ALTURA_TELA // 2) - (altura_total // 2)
                
                # Clamp start_y para nao sair da tela se tiver muitas cartas
                start_y = max(50, min(start_y, ALTURA_TELA - altura_total - 50))

                if p['id'] == 1: # Esquerda (J2 em 4P/2v2)
                    fixed_x = 40
                    nome_pos_center = (80, start_y - 25)
                else: # Direita (J4 em 4P/2v2)
                    fixed_x = LARGURA_TELA - 120
                    nome_pos_center = (LARGURA_TELA - 80, start_y - 25)
                
                # Nome
                cor_nome = AMARELO if eh_sua_vez else BRANCO
                if eh_sua_vez: cor_nome = (255, 255, 0)
                txt_nome = self.fonte_info.render(f"{p['nome']} ({mao_size})", True, cor_nome)
                rect_nome = txt_nome.get_rect(center=nome_pos_center)
                self.tela.blit(txt_nome, rect_nome)

                # Cartas Verticais
                for i, carta in enumerate(p['mao']):
                    cx = fixed_x
                    cy = start_y + i * offset_y
                    
                    hover = False
                    if eh_sua_vez and self.estado == 'JOGANDO':
                         if pygame.Rect(cx, cy, 80, 120).collidepoint(mouse_pos): hover = True
                    
                    carta.desenhar(self.tela, cx, cy, oculto=False, hover=hover)

        # Botao Passar (se comprou e nao jogou)
        if self.comprou_no_turno and self.estado == 'JOGANDO':
            btn_passar = Botao(LARGURA_TELA - 200, ALTURA_TELA - 100, 150, 50, "Passar Vez", VERMELHO, 'PASSAR')
            btn_passar.hover = btn_passar.rect.collidepoint(mouse_pos)
            btn_passar.desenhar(self.tela)
            
            if pygame.mouse.get_pressed()[0] and btn_passar.hover:
                self.proximo_turno()
                time.sleep(0.2)

    def checar_jogada_valida(self, carta):
        topo = self.pilha_descarte[-1]
        if carta.cor == 'black': return True
        if carta.cor == self.cor_atual: return True
        if carta.tipo == topo.tipo:
            if carta.tipo == 'number': return carta.valor == topo.valor
            return True
        return False

    def executar_jogada(self, jogador_idx, carta_idx, cor_wild=None):
        jogador = self.jogadores[jogador_idx]
        carta = jogador['mao'].pop(carta_idx)
        
        self.pilha_descarte.append(carta)
        self.comprou_no_turno = False
        
        nova_cor = carta.cor
        if carta.cor == 'black': nova_cor = cor_wild
        self.cor_atual = nova_cor

        # Vitoria
        if not jogador['mao']:
            self.vencedor = jogador
            self.estado = 'GAMEOVER'
            self.mensagem = f"FIM DE JOGO! {jogador['nome']} venceu!"
            return

        pular = False
        if carta.tipo == 'reverse':
            if len(self.jogadores) == 2: pular = True
            else: self.direcao *= -1
        elif carta.tipo == 'skip':
            pular = True
        elif carta.tipo == 'draw2':
            pular = True
            prox = self.get_prox_idx()
            self.comprar_cartas(prox, 2)
        elif carta.tipo == 'wild4':
            pular = True
            prox = self.get_prox_idx()
            self.comprar_cartas(prox, 4)

        self.mensagem = f"{jogador['nome']} jogou {carta.get_nome_display()}"
        self.proximo_turno(pular)

    def comprar_cartas(self, jogador_idx, qtd):
        for _ in range(qtd):
            if not self.baralho:
                if len(self.pilha_descarte) > 1:
                    topo = self.pilha_descarte.pop()
                    self.baralho = self.pilha_descarte[:]
                    self.pilha_descarte = [topo]
                    random.shuffle(self.baralho)
                else: break
            if self.baralho:
                self.jogadores[jogador_idx]['mao'].append(self.baralho.pop())

    def get_prox_idx(self, pular=False):
        passos = 2 if pular else 1
        return (self.turno_idx + (self.direcao * passos)) % len(self.jogadores)

    def proximo_turno(self, pular=False):
        self.turno_idx = self.get_prox_idx(pular)
        self.comprou_no_turno = False
        self.mensagem = f"Vez do {self.jogadores[self.turno_idx]['nome']}"

    def loop_principal(self):
        rodando = True
        while rodando:
            mouse_pos = pygame.mouse.get_pos()
            
            for evento in pygame.event.get():
                if evento.type == pygame.QUIT:
                    rodando = False
                    
                if evento.type == pygame.MOUSEBUTTONDOWN:
                    if self.estado == 'MENU':
                        for btn in self.botoes_menu:
                            acao = btn.checar_click(mouse_pos)
                            if acao: self.iniciar_partida(acao)
                            
                    elif self.estado == 'GAMEOVER':
                         acao = self.botao_reiniciar.checar_click(mouse_pos)
                         if acao: self.estado = 'MENU'

                    elif self.estado == 'COR_PICKER':
                        for btn in self.botoes_cor:
                            cor = btn.checar_click(mouse_pos)
                            if cor:
                                self.executar_jogada(self.turno_idx, self.carta_pendente_idx, cor)
                                self.estado = 'JOGANDO'
                                self.carta_pendente_idx = None

                    elif self.estado == 'JOGANDO':
                        jogador_atual = self.jogadores[self.turno_idx]
                        
                        # Clique no monte (comprar)
                        centro_x, centro_y = LARGURA_TELA // 2, ALTURA_TELA // 2
                        rect_monte = pygame.Rect(centro_x - 100, centro_y - 60, 80, 120)
                        
                        if rect_monte.collidepoint(mouse_pos) and not self.comprou_no_turno:
                            self.comprar_cartas(self.turno_idx, 1)
                            self.comprou_no_turno = True
                            self.mensagem = f"{jogador_atual['nome']} comprou. Jogue ou passe."
                            continue # Evita clique duplo instantaneo
                        
                        # Clique nas cartas do jogador atual
                        # Precisamos re-calcular a posicao exata das cartas para saber qual foi clicada
                        # Mas como 'Carta' guarda self.rect do ultimo draw, podemos usar isso!
                        # Porem, apenas se desenhar_mesa foi chamado.
                        
                        jogou = False
                        # Iterar de tras pra frente (z-index visual)
                        for i in range(len(jogador_atual['mao']) - 1, -1, -1):
                            carta = jogador_atual['mao'][i]
                            if carta.rect and carta.rect.collidepoint(mouse_pos):
                                if self.checar_jogada_valida(carta):
                                    if carta.cor == 'black':
                                        self.estado = 'COR_PICKER'
                                        self.carta_pendente_idx = i
                                    else:
                                        self.executar_jogada(self.turno_idx, i)
                                    jogou = True
                                else:
                                    self.mensagem = "Jogada Invalida!"
                                break 
            
            self.tela.fill(CINZA_FUNDO)
            
            if self.estado == 'MENU':
                titulo = self.fonte_aviso.render("UNO LOCAL MULTIPLAYER", True, AMARELO)
                self.tela.blit(titulo, (LARGURA_TELA//2 - 180, 150))
                for btn in self.botoes_menu:
                    btn.hover = btn.rect.collidepoint(mouse_pos)
                    btn.desenhar(self.tela)
                    
            elif self.estado == 'JOGANDO':
                self.desenhar_mesa()
                
            elif self.estado == 'COR_PICKER':
                self.desenhar_mesa()
                sombra = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
                sombra.fill((0,0,0,180))
                self.tela.blit(sombra, (0,0))
                txt = self.fonte_aviso.render("Escolha uma Cor", True, BRANCO)
                self.tela.blit(txt, (LARGURA_TELA//2 - 120, 200))
                for btn in self.botoes_cor:
                    btn.hover = btn.rect.collidepoint(mouse_pos)
                    btn.desenhar(self.tela)

            elif self.estado == 'GAMEOVER':
                self.desenhar_mesa()
                sombra = pygame.Surface((LARGURA_TELA, ALTURA_TELA), pygame.SRCALPHA)
                sombra.fill((0,0,0,200))
                self.tela.blit(sombra, (0,0))
                txt = self.fonte_aviso.render(self.mensagem, True, AMARELO)
                rect_txt = txt.get_rect(center=(LARGURA_TELA//2, ALTURA_TELA//2 - 50))
                self.tela.blit(txt, rect_txt)
                self.botao_reiniciar.hover = self.botao_reiniciar.rect.collidepoint(mouse_pos)
                self.botao_reiniciar.desenhar(self.tela)

            pygame.display.flip()
            self.relogio.tick(FPS)

        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    jogo = Jogo()
    jogo.loop_principal()

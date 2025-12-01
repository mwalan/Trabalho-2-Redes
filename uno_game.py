import pygame
import random
import sys
import time

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
        self.alvo_x = 0     # Para animação (simplificada)
        self.alvo_y = 0
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
        pygame.display.set_caption("Uno Pygame - 2 Jogadores, 4 Jogadores e Duplas")
        self.relogio = pygame.time.Clock()
        self.fonte_info = pygame.font.SysFont('Arial', 24, bold=True)
        self.fonte_aviso = pygame.font.SysFont('Arial', 36, bold=True)

        self.estado = 'MENU' # MENU, JOGANDO, COR_PICKER, GAMEOVER
        self.modo_jogo = '' # '2P', '4P', '2V2'
        
        self.baralho = []
        self.pilha_descarte = []
        self.jogadores = [] # Lista de dics: {'id': 0, 'mao': [], 'bot': T/F, 'nome': '', 'time': 1}
        self.turno_idx = 0
        self.direcao = 1 # 1 horario, -1 anti-horario
        self.cor_atual = '' # Importante para wild cards
        
        self.mensagem = ""
        self.vencedor = None
        self.comprou_no_turno = False
        
        # UI
        self.botoes_menu = [
            Botao(350, 300, 300, 60, "1 vs 1 (Bot)", AZUL, '2P'),
            Botao(350, 380, 300, 60, "4 Jogadores (Bots)", VERMELHO, '4P'),
            Botao(350, 460, 300, 60, "2 vs 2 (Duplas)", VERDE, '2V2')
        ]
        
        self.botoes_cor = [
            Botao(300, 300, 100, 100, "", VERMELHO, 'red'),
            Botao(410, 300, 100, 100, "", AZUL, 'blue'),
            Botao(300, 410, 100, 100, "", VERDE, 'green'),
            Botao(410, 410, 100, 100, "", AMARELO, 'yellow')
        ]
        
        self.botao_reiniciar = Botao(350, 500, 300, 60, "Voltar ao Menu", CINZA_CARTA, 'MENU')

        # Controle de tempo do bot
        self.tempo_bot = 0
        self.delay_bot = 1500 # ms

    def iniciar_partida(self, modo):
        self.modo_jogo = modo
        self.baralho = gerar_baralho()
        self.jogadores = []
        self.direcao = 1
        self.turno_idx = 0
        self.comprou_no_turno = False
        self.mensagem = "Sua vez!"

        if modo == '2P':
            self.jogadores.append({'id': 0, 'mao': [], 'bot': False, 'nome': 'Voce', 'time': 1})
            self.jogadores.append({'id': 1, 'mao': [], 'bot': True, 'nome': 'Bot', 'time': 2})
        elif modo == '4P':
            nomes = ['Voce', 'Bot Norte', 'Bot Leste', 'Bot Oeste']
            for i in range(4):
                self.jogadores.append({'id': i, 'mao': [], 'bot': i != 0, 'nome': nomes[i], 'time': i})
        elif modo == '2V2':
            # Time 1: 0 e 2. Time 2: 1 e 3
            self.jogadores.append({'id': 0, 'mao': [], 'bot': False, 'nome': 'Voce (T1)', 'time': 1})
            self.jogadores.append({'id': 1, 'mao': [], 'bot': True, 'nome': 'Rival (T2)', 'time': 2})
            self.jogadores.append({'id': 2, 'mao': [], 'bot': True, 'nome': 'Aliado (T1)', 'time': 1})
            self.jogadores.append({'id': 3, 'mao': [], 'bot': True, 'nome': 'Rival (T2)', 'time': 2})

        # Distribuir cartas
        for _ in range(7):
            for p in self.jogadores:
                if self.baralho:
                    p['mao'].append(self.baralho.pop())

        # Primeira carta
        while True:
            carta = self.baralho.pop()
            if carta.tipo != 'wild4': # Evita +4 na saida
                self.pilha_descarte = [carta]
                self.cor_atual = carta.cor if carta.cor != 'black' else 'red' # Default se for wild normal
                break
            else:
                self.baralho.insert(0, carta)

        self.estado = 'JOGANDO'

    def desenhar_mesa(self):
        self.tela.fill(VERDE_MESA)
        
        # Info Topo
        txt_status = self.fonte_info.render(f"Cor Atual: {self.cor_atual.upper()} | {self.mensagem}", True, BRANCO)
        self.tela.blit(txt_status, (20, 20))
        
        # Descarte e Monte
        centro_x, centro_y = LARGURA_TELA // 2, ALTURA_TELA // 2
        
        # Monte
        pygame.draw.rect(self.tela, PRETO, (centro_x - 100, centro_y - 60, 80, 120), border_radius=10)
        pygame.draw.rect(self.tela, BRANCO, (centro_x - 100, centro_y - 60, 80, 120), width=2, border_radius=10)
        txt_monte = self.fonte_info.render("Monte", True, BRANCO)
        self.tela.blit(txt_monte, (centro_x - 90, centro_y - 15))
        
        # Descarte
        if self.pilha_descarte:
            topo = self.pilha_descarte[-1]
            # Se for wild, mostramos a cor escolhida desenhando um retangulo de fundo
            if topo.cor == 'black':
                pygame.draw.rect(self.tela, CORES_UNO[self.cor_atual], (centro_x + 10, centro_y - 70, 100, 140), border_radius=15)
            
            topo.desenhar(self.tela, centro_x + 20, centro_y - 60)

        # Indicador de Direcao
        txt_dir = ">>>" if self.direcao == 1 else "<<<"
        cor_dir = AMARELO if self.direcao == 1 else AZUL
        render_dir = self.fonte_aviso.render(txt_dir, True, cor_dir)
        self.tela.blit(render_dir, (centro_x - 20, centro_y + 80))

        # Jogadores e Cartas
        posicoes = {}
        if len(self.jogadores) == 2:
            posicoes[0] = (LARGURA_TELA//2, ALTURA_TELA - 100) # Voce
            posicoes[1] = (LARGURA_TELA//2, 80) # Bot
        else:
            posicoes[0] = (LARGURA_TELA//2, ALTURA_TELA - 80) # Sul (Voce)
            posicoes[1] = (80, ALTURA_TELA//2) # Oeste
            posicoes[2] = (LARGURA_TELA//2, 80) # Norte
            posicoes[3] = (LARGURA_TELA - 80, ALTURA_TELA//2) # Leste

        mouse_pos = pygame.mouse.get_pos()
        jogador_atual = self.jogadores[self.turno_idx]

        for p in self.jogadores:
            px, py = posicoes[p['id']]
            # Desenha Avatar/Nome
            cor_nome = AMARELO if self.turno_idx == p['id'] else BRANCO
            txt_nome = self.fonte_info.render(f"{p['nome']} ({len(p['mao'])})", True, cor_nome)
            self.tela.blit(txt_nome, (px - 50, py - 60 if py > ALTURA_TELA//2 else py + 130))

            # Desenha Mao
            mao_size = len(p['mao'])
            offset = 50 # espaco entre cartas
            largura_total = mao_size * offset
            inicio_x = px - largura_total // 2
            
            # Se for voce, interacao
            eh_voce = (p['id'] == 0)
            
            for i, carta in enumerate(p['mao']):
                cx = inicio_x + i * offset
                cy = py
                
                # Para bots laterais, logica simplificada de desenho (apenas contagem visual)
                if len(self.jogadores) > 2 and (p['id'] == 1 or p['id'] == 3):
                    # Desenhar apenas um monte representativo ou cartas viradas 90 graus seria ideal
                    # Simplificando: desenhar pequeno retangulo
                    rect_mini = pygame.Rect(px - 40, py - 40 + i*10, 80, 120) if p['id'] == 1 else pygame.Rect(px - 40, py - 40 + i*10, 80, 120)
                    pygame.draw.rect(self.tela, PRETO, rect_mini, border_radius=5)
                    pygame.draw.rect(self.tela, BRANCO, rect_mini, width=1, border_radius=5)
                    continue

                hover = False
                if eh_voce and self.estado == 'JOGANDO' and self.turno_idx == 0:
                    rect_virtual = pygame.Rect(cx, cy, 80, 120)
                    if rect_virtual.collidepoint(mouse_pos):
                        hover = True
                
                oculto = p['bot']
                carta.desenhar(self.tela, cx, cy, oculto=oculto, hover=hover)

        # Botao Passar (se comprou e nao jogou)
        if self.turno_idx == 0 and self.comprou_no_turno and self.estado == 'JOGANDO':
            btn_passar = Botao(LARGURA_TELA - 200, ALTURA_TELA - 100, 150, 50, "Passar Vez", VERMELHO, 'PASSAR')
            btn_passar.hover = btn_passar.rect.collidepoint(mouse_pos)
            btn_passar.desenhar(self.tela)
            
            # Checar clique no loop principal, mas desenhamos aqui
            if pygame.mouse.get_pressed()[0] and btn_passar.hover:
                self.proximo_turno()
                time.sleep(0.2) # Debounce basico

    def checar_jogada_valida(self, carta):
        topo = self.pilha_descarte[-1]
        
        # Coringa sempre pode
        if carta.cor == 'black':
            return True
        
        # Mesma cor (considerando cor escolhida no wild)
        if carta.cor == self.cor_atual:
            return True
            
        # Mesmo valor/simbolo
        if carta.tipo == topo.tipo:
            if carta.tipo == 'number':
                return carta.valor == topo.valor
            return True # Simbolos iguais
            
        return False

    def executar_jogada(self, jogador_idx, carta_idx, cor_wild=None):
        jogador = self.jogadores[jogador_idx]
        carta = jogador['mao'].pop(carta_idx)
        
        self.pilha_descarte.append(carta)
        self.comprou_no_turno = False
        
        # Efeitos
        pular = False
        nova_cor = carta.cor
        
        if carta.cor == 'black':
            nova_cor = cor_wild
        
        self.cor_atual = nova_cor

        # Verificar vitoria
        if not jogador['mao']:
            self.vencedor = jogador
            self.estado = 'GAMEOVER'
            if self.modo_jogo == '2V2':
                self.mensagem = f"FIM DE JOGO! Time {jogador['time']} venceu!"
            else:
                self.mensagem = f"FIM DE JOGO! {jogador['nome']} venceu!"
            return

        if carta.tipo == 'reverse':
            if len(self.jogadores) == 2:
                pular = True
            else:
                self.direcao *= -1
        
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
                # Recicla descarte
                if len(self.pilha_descarte) > 1:
                    topo = self.pilha_descarte.pop()
                    self.baralho = self.pilha_descarte[:]
                    self.pilha_descarte = [topo]
                    random.shuffle(self.baralho)
                else:
                    break
            if self.baralho:
                self.jogadores[jogador_idx]['mao'].append(self.baralho.pop())

    def get_prox_idx(self, pular=False):
        passos = 2 if pular else 1
        idx = (self.turno_idx + (self.direcao * passos)) % len(self.jogadores)
        return idx

    def proximo_turno(self, pular=False):
        self.turno_idx = self.get_prox_idx(pular)
        self.comprou_no_turno = False
        self.tempo_bot = pygame.time.get_ticks() # Reset timer bot

    def logica_bot(self):
        # Atraso para "pensar"
        if pygame.time.get_ticks() - self.tempo_bot < self.delay_bot:
            return

        bot = self.jogadores[self.turno_idx]
        jogadas_validas = [i for i, c in enumerate(bot['mao']) if self.checar_jogada_valida(c)]

        if jogadas_validas:
            # Estrategia simples: Prioriza acao, depois cor, guarda wild
            melhor_idx = jogadas_validas[0]
            
            # Tenta nao usar wild de cara
            for idx in jogadas_validas:
                c = bot['mao'][idx]
                if c.cor != 'black':
                    melhor_idx = idx
                    break
            
            carta = bot['mao'][melhor_idx]
            cor_escolhida = 'red'
            if carta.cor == 'black':
                # Escolhe cor que mais tem na mao
                cores = {'red':0, 'blue':0, 'green':0, 'yellow':0}
                for c in bot['mao']:
                    if c.cor != 'black': cores[c.cor] += 1
                cor_escolhida = max(cores, key=cores.get)

            self.executar_jogada(self.turno_idx, melhor_idx, cor_escolhida)
        else:
            if not self.comprou_no_turno:
                self.comprar_cartas(self.turno_idx, 1)
                self.comprou_no_turno = True
                self.mensagem = f"{bot['nome']} comprou uma carta"
                self.tempo_bot = pygame.time.get_ticks() # Espera mais um pouco para ver se joga
            else:
                self.mensagem = f"{bot['nome']} passou a vez"
                self.proximo_turno()

    def loop_principal(self):
        rodando = True
        while rodando:
            mouse_pos = pygame.mouse.get_pos()
            
            # --- EVENTOS ---
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
                                self.executar_jogada(0, self.carta_pendente_idx, cor)
                                self.estado = 'JOGANDO'
                                self.carta_pendente_idx = None

                    elif self.estado == 'JOGANDO':
                        # Clique no monte (comprar)
                        centro_x, centro_y = LARGURA_TELA // 2, ALTURA_TELA // 2
                        rect_monte = pygame.Rect(centro_x - 100, centro_y - 60, 80, 120)
                        
                        if self.turno_idx == 0: # Sua vez
                            if rect_monte.collidepoint(mouse_pos) and not self.comprou_no_turno:
                                self.comprar_cartas(0, 1)
                                self.comprou_no_turno = True
                                self.mensagem = "Voce comprou. Jogue ou passe."
                            
                            # Clique nas cartas
                            jogador = self.jogadores[0]
                            offset = 50
                            inicio_x = (LARGURA_TELA // 2) - ((len(jogador['mao']) * offset) // 2)
                            
                            for i in range(len(jogador['mao']) - 1, -1, -1): # Check de tras pra frente (z-index)
                                cx = inicio_x + i * offset
                                cy = ALTURA_TELA - 100
                                if pygame.Rect(cx, cy, 80, 120).collidepoint(mouse_pos):
                                    carta = jogador['mao'][i]
                                    if self.checar_jogada_valida(carta):
                                        if carta.cor == 'black':
                                            self.estado = 'COR_PICKER'
                                            self.carta_pendente_idx = i
                                        else:
                                            self.executar_jogada(0, i)
                                    else:
                                        self.mensagem = "Jogada Invalida!"
                                    break # Clicou em uma, para

            # --- UPDATE ---
            if self.estado == 'JOGANDO':
                if self.jogadores[self.turno_idx]['bot']:
                    self.logica_bot()

            # --- DRAW ---
            self.tela.fill(CINZA_FUNDO)
            
            if self.estado == 'MENU':
                titulo = self.fonte_aviso.render("UNO PYGAME", True, AMARELO)
                self.tela.blit(titulo, (LARGURA_TELA//2 - 100, 150))
                for btn in self.botoes_menu:
                    btn.hover = btn.rect.collidepoint(mouse_pos)
                    btn.desenhar(self.tela)
                    
            elif self.estado == 'JOGANDO':
                self.desenhar_mesa()
                
            elif self.estado == 'COR_PICKER':
                self.desenhar_mesa() # Fundo
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

"""
ARQUIVO: protocolo.py
FUNÇÃO: Definir as regras, estruturas de dados e o estado compartilhado do jogo.
IMPORTÂNCIA: Este arquivo é a "verdade absoluta" do jogo. Tanto o servidor quanto o cliente
precisam ter exatamente a mesma versão deste arquivo para que a serialização (pickle) funcione.
DESCRIÇÃO: Contém a classe Carta, a classe EstadoJogo (que encapsula toda a lógica do UNO)
e as constantes de mensagens de rede.
"""

import random   # Usado para embaralhar o baralho

# --- CONSTANTES DO JOGO ---
# Definem as propriedades básicas das cartas
CORES = ['VERMELHO', 'VERDE', 'AZUL', 'AMARELO']
VALORES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'PULAR', 'INVERTER', '+2']
ESPECIAIS = ['CORINGA', '+4']

# --- TIPOS DE MENSAGEM (REDE) ---
# Constantes usadas para identificar o tipo de ação enviada pela rede
MSG_ENTRAR_SALA = 'ENTRAR_SALA'
MSG_CRIAR_SALA = 'CRIAR_SALA'
MSG_LISTAR_SALAS = 'LISTAR_SALAS'
MSG_ATUALIZAR_SALA = 'ATUALIZAR_SALA' # Servidor -> Cliente (dentro da sala)
MSG_INICIAR_JOGO = 'INICIAR_JOGO'
MSG_GRITAR_UNO = 'GRITAR_UNO'
MSG_SAIR_SALA = 'SAIR_SALA'
MSG_ERRO = 'ERRO'

class Carta:
    """
    Representa uma única carta do jogo.
    Atributos:
        cor (str): A cor da carta (ex: 'VERMELHO') ou 'PRETO' para especiais.
        valor (str): O número ou ação da carta (ex: '7', 'PULAR', '+4').
    """
    def __init__(self, cor, valor):
        self.cor = cor
        self.valor = valor
    
    def __repr__(self):
        # Método mágico para representação em string (útil para debug)
        return f"{self.valor} {self.cor}"

class EstadoJogo:
    """
    Classe principal que armazena todo o estado do jogo num determinado momento.
    O servidor mantém uma instância desta classe e envia cópias dela para os clientes.
    """
    def __init__(self, modo_jogo):
        self.modo_jogo = modo_jogo # Modos: '2P' (2 Jogadores), '4P' (4 Jogadores), 'DUPLAS'
        self.baralho = self.criar_baralho() # Lista de cartas disponíveis para compra
        self.descarte = [] # Pilha de cartas jogadas na mesa
        self.maos = {} # Dicionário mapeando ID do jogador -> Lista de Cartas
        self.jogador_atual = 0 # Índice do jogador que deve jogar agora
        self.sentido_horario = True # Controla a direção do jogo (pode ser invertido)
        self.jogadores_conectados = [] # Lista de IDs dos jogadores conectados
        self.jogo_iniciado = False # Flag para saber se estamos no lobby ou no jogo
        self.vencedor = None # Armazena o ID do vencedor quando alguém ganha
        self.cor_atual = None # Cor ativa na mesa (importante para coringas)
        self.uno_safe = [] # Lista de IDs de jogadores que gritaram UNO e estão seguros
        self.host_id = None # ID do anfitrião da sala
        
        # Inicialização do jogo: embaralha e vira a primeira carta
        self.embaralhar()
        topo = self.baralho.pop()
        self.descarte.append(topo)
        # Se a primeira carta for preta, define vermelho como padrão, senão usa a cor da carta
        self.cor_atual = topo.cor if topo.cor != 'PRETO' else 'VERMELHO'

    def criar_baralho(self):
        """Gera todas as cartas do baralho padrão do UNO."""
        baralho = []
        for cor in CORES:
            for valor in VALORES:
                baralho.append(Carta(cor, valor))
                if valor != '0': # No UNO, existe apenas um '0' por cor, mas duas de cada outra
                    baralho.append(Carta(cor, valor))
        
        # Adiciona as cartas pretas (Coringas e +4)
        for _ in range(4):
            baralho.append(Carta('PRETO', 'CORINGA'))
            baralho.append(Carta('PRETO', '+4'))
        return baralho

    def embaralhar(self):
        """Mistura as cartas do baralho."""
        random.shuffle(self.baralho)

    def comprar_carta(self, id_jogador):
        """
        Retira uma carta do baralho e adiciona à mão do jogador.
        Se o baralho acabar, recicla as cartas do descarte.
        """
        if not self.baralho:
            # Se o baralho acabou, pega o descarte (menos a carta do topo), embaralha e usa como novo baralho
            self.baralho = self.descarte[:-1]
            self.descarte = [self.descarte[-1]]
            random.shuffle(self.baralho)
        
        if self.baralho:
            carta = self.baralho.pop()
            self.maos[id_jogador].append(carta)
            
            # Se comprou e ficou com mais de 1 carta, perde o status de UNO (se tivesse)
            # Isso evita que alguém grite UNO, compre carta e continue "safe" com 2 cartas
            if len(self.maos[id_jogador]) != 1 and id_jogador in self.uno_safe:
                self.uno_safe.remove(id_jogador)
                
            return True
        return False

    def jogar_carta(self, id_jogador, indice_carta, cor_escolhida=None):
        """
        Tenta jogar uma carta da mão do jogador para o descarte.
        Retorna True se a jogada for válida, False caso contrário.
        """
        mao = self.maos[id_jogador]
        
        # Verifica se o índice é válido
        if 0 <= indice_carta < len(mao):
            carta = mao[indice_carta]
            topo = self.descarte[-1] # A carta que está atualmente no topo da mesa

            # --- REGRAS DE VALIDAÇÃO ---
            # 1. Mesma cor (da carta ou da cor ativa na mesa)
            # 2. Mesmo valor/símbolo (ex: 7 no 7, Pular no Pular)
            # 3. Carta do jogador é preta (Coringa/+4) - sempre pode jogar
            match_cor = carta.cor == self.cor_atual or carta.cor == 'PRETO'
            match_valor = carta.valor == topo.valor
            
            if match_cor or match_valor:
                # Se for carta preta, PRECISA ter escolhido uma cor
                if carta.cor == 'PRETO':
                    if not cor_escolhida or cor_escolhida not in CORES:
                        return False # Jogada inválida sem escolha de cor
                    self.cor_atual = cor_escolhida
                else:
                    self.cor_atual = carta.cor

                # Remove da mão e coloca no descarte
                self.descarte.append(mao.pop(indice_carta))
                
                # VERIFICA VITORIA
                if len(mao) == 0:
                    self.vencedor = id_jogador
                    return True

                # Se ficou com 1 carta, precisa gritar UNO (reseta status safe)
                # O jogador deve clicar no botão UNO imediatamente
                if len(mao) == 1 and id_jogador in self.uno_safe:
                    self.uno_safe.remove(id_jogador)
                
                # --- EFEITOS ESPECIAIS ---
                pular_vez = False
                
                if carta.valor == 'PULAR':
                    pular_vez = True
                
                elif carta.valor == 'INVERTER':
                    if len(self.jogadores_conectados) == 2:
                        # Em 2 jogadores, Inverter funciona como Pular
                        pular_vez = True
                    else:
                        self.sentido_horario = not self.sentido_horario
                
                elif carta.valor == '+2':
                    # Identifica o próximo jogador (vítima)
                    total = len(self.jogadores_conectados)
                    passo = 1 if self.sentido_horario else -1
                    proximo_idx = (self.jogador_atual + passo) % total
                    id_proximo = self.jogadores_conectados[proximo_idx]
                    
                    # Vítima compra 2 cartas e perde a vez
                    self.comprar_carta(id_proximo)
                    self.comprar_carta(id_proximo)
                    pular_vez = True
                
                elif carta.valor == '+4':
                    # Identifica o próximo jogador (vítima)
                    total = len(self.jogadores_conectados)
                    passo = 1 if self.sentido_horario else -1
                    proximo_idx = (self.jogador_atual + passo) % total
                    id_proximo = self.jogadores_conectados[proximo_idx]
                    
                    # Vítima compra 4 cartas e perde a vez
                    for _ in range(4):
                        self.comprar_carta(id_proximo)
                    pular_vez = True
                
                if pular_vez:
                    self.avancar_turno()
                
                # Passa a vez para o próximo jogador
                self.avancar_turno()
                return True
        return False

    def avancar_turno(self):
        """Calcula quem é o próximo jogador baseado no sentido do jogo."""
        total = len(self.jogadores_conectados)
        passo = 1 if self.sentido_horario else -1
        # Aritmética modular para garantir que o índice dê a volta (ex: jogador 3 -> jogador 0)
        self.jogador_atual = (self.jogador_atual + passo) % total

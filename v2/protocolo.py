#Este arquivo define o que é uma carta, o baralho e o estado do jogo. O servidor e o cliente usam isso para "falar a mesma língua".


import random
import pickle

# Cores e Constantes
CORES = ['VERMELHO', 'VERDE', 'AZUL', 'AMARELO']
VALORES = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'PULAR', 'INVERTER', '+2']
ESPECIAIS = ['CORINGA', '+4']

class Carta:
    def __init__(self, cor, valor):
        self.cor = cor
        self.valor = valor
    
    def __repr__(self):
        return f"{self.valor} {self.cor}"

class EstadoJogo:
    def __init__(self, modo_jogo):
        self.modo_jogo = modo_jogo # '2P', '4P', 'DUPLAS'
        self.baralho = self.criar_baralho()
        self.descarte = []
        self.maos = {} # Dicionario {id_jogador: [Cartas]}
        self.jogador_atual = 0
        self.sentido_horario = True
        self.jogadores_conectados = []
        self.jogo_iniciado = False
        self.vencedor = None
        
        # Inicializa o jogo
        self.embaralhar()
        self.descarte.append(self.baralho.pop())

    def criar_baralho(self):
        baralho = []
        for cor in CORES:
            for valor in VALORES:
                baralho.append(Carta(cor, valor))
                if valor != '0': # Duas cartas de 1-9 e especiais por cor
                    baralho.append(Carta(cor, valor))
        for _ in range(4):
            baralho.append(Carta('PRETO', 'CORINGA'))
            baralho.append(Carta('PRETO', '+4'))
        return baralho

    def embaralhar(self):
        random.shuffle(self.baralho)

    def comprar_carta(self, id_jogador):
        if not self.baralho:
            # Recicla descarte se baralho acabar (simplificado)
            self.baralho = self.descarte[:-1]
            self.descarte = [self.descarte[-1]]
            random.shuffle(self.baralho)
        
        if self.baralho:
            carta = self.baralho.pop()
            self.maos[id_jogador].append(carta)
            return True
        return False

    def jogar_carta(self, id_jogador, indice_carta):
        mao = self.maos[id_jogador]
        if 0 <= indice_carta < len(mao):
            carta = mao[indice_carta]
            topo = self.descarte[-1]

            # Validação simples de regras do UNO
            match_cor = carta.cor == topo.cor or carta.cor == 'PRETO' or topo.cor == 'PRETO'
            match_valor = carta.valor == topo.valor
            
            if match_cor or match_valor:
                self.descarte.append(mao.pop(indice_carta))
                
                # Lógica simplificada de efeitos (Pular/Inverter apenas avança turno extra aqui)
                # Para um TCC completo, expandir a lógica de efeitos especiais aqui
                
                self.avancar_turno()
                return True
        return False

    def avancar_turno(self):
        total = len(self.jogadores_conectados)
        passo = 1 if self.sentido_horario else -1
        self.jogador_atual = (self.jogador_atual + passo) % total
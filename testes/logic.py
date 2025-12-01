import random

class Card:
    def __init__(self, color, tipo, value=None):
        self.color = color
        self.tipo = tipo
        self.value = value
    
    def to_dict(self):
        """Serializa a carta para enviar via JSON"""
        sym = str(self.value) if self.tipo == 'number' else self.tipo
        if self.tipo == 'draw2': sym = '+2'
        if self.tipo == 'wild4': sym = '+4'
        return {'color': self.color, 'type': self.tipo, 'value': self.value, 'symbol': sym}

class UnoGame:
    def __init__(self):
        self.deck = []
        self.discard = []
        self.players = [] # Lista de nomes
        self.hands = []   # Lista de listas de Cards
        self.turn_index = 0
        self.direction = 1
        self.current_color = ''
        
    def generate_deck(self):
        colors = ['red', 'blue', 'green', 'yellow']
        self.deck = []
        for c in colors:
            self.deck.append(Card(c, 'number', 0))
            for i in range(1, 10):
                self.deck.extend([Card(c, 'number', i)] * 2)
            for t in ['skip', 'reverse', 'draw2']:
                self.deck.extend([Card(c, t)] * 2)
        for _ in range(4):
            self.deck.extend([Card('black', 'wild'), Card('black', 'wild4')])
        random.shuffle(self.deck)

    def add_player(self, name):
        self.players.append(name)
        self.hands.append([])

    def start_game(self):
        self.generate_deck()
        # Distribui 7 cartas
        for i in range(len(self.players)):
            for _ in range(7):
                self.hands[i].append(self.deck.pop())
        
        # Carta inicial
        top = self.deck.pop()
        self.discard = [top]
        self.current_color = top.color if top.color != 'black' else 'red'

    def play_card(self, player_index, card_idx, wild_color=None):
        """Tenta jogar uma carta. Retorna (Sucesso, MsgErro)"""
        if player_index != self.turn_index:
            return False, "Não é sua vez!"
            
        hand = self.hands[player_index]
        if card_idx >= len(hand): return False, "Carta inválida"
        
        card = hand[card_idx]
        top = self.discard[-1]
        
        # Validação Básica
        valid = False
        if card.color == 'black': valid = True
        elif card.color == self.current_color: valid = True
        elif card.tipo == top.tipo and card.tipo != 'number': valid = True
        elif card.tipo == 'number' and card.value == top.value: valid = True
        
        if not valid: return False, "Jogada inválida"
        
        # Executa Jogada
        played = hand.pop(card_idx)
        self.discard.append(played)
        
        # Efeitos
        self.current_color = wild_color if card.color == 'black' else card.color
        
        skip = False
        if card.tipo == 'skip': skip = True
        if card.tipo == 'reverse': self.direction *= -1
        if card.tipo == 'draw2': 
            next_p = (self.turn_index + self.direction) % len(self.players)
            self.draw_n(next_p, 2)
            skip = True
            
        # Avança turno
        steps = 2 if skip else 1
        self.turn_index = (self.turn_index + steps * self.direction) % len(self.players)
        return True, "OK"

    def draw_card(self, player_index):
        if self.deck:
            self.hands[player_index].append(self.deck.pop())
            # Se não jogar, passa a vez (simplificação)
            self.turn_index = (self.turn_index + self.direction) % len(self.players)

    def draw_n(self, p_idx, n):
        for _ in range(n):
            if self.deck: self.hands[p_idx].append(self.deck.pop())

    def get_state_dict(self):
        """Retorna o estado serializável para o cliente"""
        return {
            "current_player_idx": self.turn_index,
            "current_player_name": self.players[self.turn_index],
            "current_color": self.current_color,
            "discard_top": self.discard[-1].to_dict() if self.discard else None,
            "hands": [[c.to_dict() for c in h] for h in self.hands] # Na prática, deveria ocultar mãos alheias
        }

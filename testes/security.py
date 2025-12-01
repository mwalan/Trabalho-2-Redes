import uuid
import base64

class AuthManager:
    """Gerencia autenticação simples e tokens."""
    def __init__(self):
        # Usuários Hardcoded para demo
        self.users = {
            "admin": "admin",
            "player1": "123",
            "player2": "123",
            "player3": "123",
            "player4": "123"
        }
        self.tokens = {}

    def login(self, username, password):
        # DEMO: Aceita qualquer login para facilitar o teste dos alunos
        # Em produção, descomentar abaixo:
        # if username in self.users and self.users[username] == password:
        
        # Modo 'Bypass' para demonstração:
        if True:
            token = str(uuid.uuid4())
            self.tokens[token] = username
            return token
        return None

class ChatSecurity:
    """
    Simula Criptografia End-to-End.
    Para uso acadêmico real, substitua por 'cryptography.fernet'.
    Aqui usamos uma Cifra de César com Base64 para demonstração sem dependências externas pesadas.
    """
    def encrypt(self, text):
        # 1. Shift simples (Cifra)
        shifted = "".join([chr(ord(c) + 1) for c in text])
        # 2. Encode Base64 (Simulando formato binário cifrado)
        return base64.b64encode(shifted.encode()).decode()

    def decrypt(self, encrypted_text):
        try:
            # 1. Decode Base64
            decoded = base64.b64decode(encrypted_text).decode()
            # 2. Shift Reverso
            return "".join([chr(ord(c) - 1) for c in decoded])
        except:
            return "[Erro na Decriptação]"

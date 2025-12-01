import json
import struct

def send_json(socket, data):
    """Envia um dicionário como JSON precedido pelo tamanho (Protocolo Length-Prefix)."""
    json_bytes = json.dumps(data).encode('utf-8')
    # Empacota o tamanho da mensagem em 4 bytes (big-endian)
    socket.sendall(struct.pack('>I', len(json_bytes)) + json_bytes)

def recv_json(socket):
    """Recebe uma mensagem JSON."""
    try:
        # Lê os primeiros 4 bytes para saber o tamanho
        raw_len = socket.recv(4)
        if not raw_len: return None
        msg_len = struct.unpack('>I', raw_len)[0]
        
        # Lê o corpo da mensagem
        data = b""
        while len(data) < msg_len:
            packet = socket.recv(msg_len - len(data))
            if not packet: return None
            data += packet
            
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        print(f"Erro rede: {e}")
        return None

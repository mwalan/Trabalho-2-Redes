#O servidor usa socket e threading. Ele espera os jogadores se conectarem, distribui as 
#cartas iniciais e fica num loop recebendo jogadas e enviando o novo estado para todos.

import socket
import threading
import pickle
from protocolo import EstadoJogo

HOST = 'localhost'
PORT = 5555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()
print(f"Servidor UNO rodando em {HOST}:{PORT}")

clientes = []
# Por padrão iniciamos esperando 2 jogadores, mas o primeiro cliente pode mudar isso
estado_jogo = EstadoJogo('2P') 

def broadcast(estado):
    data = pickle.dumps(estado)
    for c in clientes:
        try:
            c.send(data)
        except:
            clientes.remove(c)

def handle_client(conn, player_id):
    global estado_jogo
    conn.send(pickle.dumps(player_id)) # Envia o ID do jogador ao conectar

    while True:
        try:
            data = conn.recv(4096)
            if not data: break
            
            acao = pickle.loads(data)
            # acao é um dicionário: {'tipo': 'JOGAR', 'indice': 0} ou {'tipo': 'COMPRAR'}
            
            if estado_jogo.jogo_iniciado and estado_jogo.jogadores_conectados[estado_jogo.jogador_atual] == player_id:
                alterou = False
                if acao['tipo'] == 'JOGAR':
                    alterou = estado_jogo.jogar_carta(player_id, acao['indice'])
                elif acao['tipo'] == 'COMPRAR':
                    estado_jogo.comprar_carta(player_id)
                    estado_jogo.avancar_turno() # Passa a vez ao comprar
                    alterou = True
                
                if alterou:
                    broadcast(estado_jogo)
            
            # Configuração do Menu (O jogador 0 decide o modo)
            elif not estado_jogo.jogo_iniciado and player_id == 0 and acao['tipo'] == 'CONFIG_MODO':
                estado_jogo.modo_jogo = acao['modo']
                print(f"Modo de jogo alterado para: {estado_jogo.modo_jogo}")
                broadcast(estado_jogo)

        except Exception as e:
            print(f"Erro: {e}")
            break

    print(f"Jogador {player_id} desconectado")
    clientes.remove(conn)
    conn.close()

def start():
    player_id = 0
    while True:
        conn, addr = server.accept()
        print(f"Novo jogador conectado: {addr}")
        clientes.append(conn)
        estado_jogo.jogadores_conectados.append(player_id)
        estado_jogo.maos[player_id] = []
        
        # Distribui 7 cartas iniciais
        for _ in range(7):
            estado_jogo.comprar_carta(player_id)

        thread = threading.Thread(target=handle_client, args=(conn, player_id))
        thread.start()
        
        # Verifica se pode começar
        num_necessario = 2
        if estado_jogo.modo_jogo == '4P' or estado_jogo.modo_jogo == 'DUPLAS':
            num_necessario = 4
            
        if len(clientes) == num_necessario:
            estado_jogo.jogo_iniciado = True
            print("Jogo Iniciado!")
            broadcast(estado_jogo)
            
        player_id += 1

start()
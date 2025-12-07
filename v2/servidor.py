"""
ARQUIVO: servidor.py
FUNÇÃO: Gerenciar conexões, salas e jogos.
ARQUITETURA: Cliente-Servidor com Múltiplas Salas.
"""

import socket
import threading
import pickle
from protocolo import EstadoJogo, MSG_CRIAR_SALA, MSG_ENTRAR_SALA, MSG_LISTAR_SALAS, MSG_ATUALIZAR_SALA, MSG_INICIAR_JOGO, MSG_GRITAR_UNO, MSG_SAIR_SALA, MSG_ERRO

HOST = '0.0.0.0'
PORT = 5555

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen()
print(f"Servidor UNO rodando em {HOST}:{PORT}")

# Estrutura de Salas: { 'nome_sala': {'estado': EstadoJogo, 'clientes': [conn1, conn2]} }
salas = {} 

def broadcast_sala(nome_sala, mensagem):
    """Envia uma mensagem para todos os jogadores de uma sala específica."""
    if nome_sala not in salas: return
    
    sala = salas[nome_sala]
    # Serializa apenas uma vez para eficiência
    data = pickle.dumps(mensagem)
    
    for cliente in sala['clientes']:
        try:
            cliente.send(data)
        except:
            # Cliente caiu, será removido no loop principal
            pass

def handle_client(conn, addr):
    print(f"Nova conexão: {addr}")
    sala_atual = None
    player_id = None

    try:
        while True:
            # Loop do Lobby (antes de entrar numa sala)
            if not sala_atual:
                data = conn.recv(4096)
                if not data: break
                req = pickle.loads(data)
                
                if req['tipo'] == MSG_LISTAR_SALAS:
                    # Retorna lista de salas: [{'nome': 'Sala 1', 'jogadores': 2/4, 'status': 'Aguardando'}]
                    lista = []
                    for nome, info in salas.items():
                        estado = info['estado']
                        lista.append({
                            'nome': nome,
                            'jogadores': len(info['clientes']),
                            'status': 'Jogando' if estado.jogo_iniciado else 'Aguardando'
                        })
                    conn.send(pickle.dumps({'tipo': MSG_LISTAR_SALAS, 'salas': lista}))

                elif req['tipo'] == MSG_CRIAR_SALA:
                    nome = req['nome']
                    if nome in salas:
                        conn.send(pickle.dumps({'tipo': MSG_ERRO, 'msg': 'Sala já existe!'}))
                    else:
                        # Cria nova sala
                        salas[nome] = {
                            'estado': EstadoJogo('PADRAO'), 
                            'clientes': []
                        }
                        conn.send(pickle.dumps({'tipo': 'SUCESSO_CRIAR'}))
                        # Cliente deve enviar ENTRAR_SALA em seguida

                elif req['tipo'] == MSG_ENTRAR_SALA:
                    nome = req['nome']
                    if nome in salas:
                        sala = salas[nome]
                        estado = sala['estado']
                        
                        if len(sala['clientes']) >= 4:
                            conn.send(pickle.dumps({'tipo': MSG_ERRO, 'msg': 'Sala cheia!'}))
                            continue
                            
                        if estado.jogo_iniciado:
                            conn.send(pickle.dumps({'tipo': MSG_ERRO, 'msg': 'Jogo já começou!'}))
                            continue

                        # Entra na sala
                        sala_atual = nome
                        player_id = addr
                        sala['clientes'].append(conn)
                        
                        estado.jogadores_conectados.append(player_id)
                        estado.maos[player_id] = []
                        
                        if estado.host_id is None:
                            estado.host_id = player_id
                        
                        # Distribui cartas iniciais
                        for _ in range(7):
                            estado.comprar_carta(player_id)
                        
                        # Envia ID e Estado Inicial
                        conn.send(pickle.dumps({'tipo': 'ENTROU', 'id': player_id}))
                        broadcast_sala(sala_atual, estado)
                        
                        # Início automático removido. O anfitrião deve iniciar manualmente.

                    else:
                        conn.send(pickle.dumps({'tipo': MSG_ERRO, 'msg': 'Sala não encontrada!'}))

            # Loop do Jogo (dentro de uma sala)
            else:
                data = conn.recv(4096)
                if not data: break
                acao = pickle.loads(data)
                
                sala = salas[sala_atual]
                estado = sala['estado']
                
                if acao['tipo'] == MSG_SAIR_SALA:
                    # Remove jogador da sala e do estado
                    if conn in sala['clientes']:
                        sala['clientes'].remove(conn)
                    
                    if player_id in estado.jogadores_conectados:
                        estado.jogadores_conectados.remove(player_id)
                        if player_id in estado.maos:
                            del estado.maos[player_id]
                        
                        # Migração de Anfitrião
                        if estado.host_id == player_id and estado.jogadores_conectados:
                            estado.host_id = estado.jogadores_conectados[0]
                    
                    # Se a sala ficar vazia, ela será removida no finally ou aqui mesmo?
                    # O finally trata desconexão. Aqui é saída voluntária.
                    if not sala['clientes']:
                        del salas[sala_atual]
                    else:
                        broadcast_sala(sala_atual, estado)
                        
                    sala_atual = None
                    player_id = None
                    # Não envia resposta, apenas volta pro loop do lobby
                    continue

                # Processa Ações de Jogo
                if estado.jogo_iniciado:
                    alterou = False
                    
                    # Ações do Jogador da Vez
                    if estado.jogadores_conectados[estado.jogador_atual] == player_id:
                        if acao['tipo'] == 'JOGAR':
                            cor = acao.get('cor_escolhida')
                            alterou = estado.jogar_carta(player_id, acao['indice'], cor)
                        elif acao['tipo'] == 'COMPRAR':
                            estado.comprar_carta(player_id)
                            estado.avancar_turno()
                            alterou = True
                    
                    # Ações Globais (Qualquer um pode fazer a qualquer momento)
                    if acao['tipo'] == MSG_GRITAR_UNO:
                        # 1. Se quem gritou tem 1 carta, fica safe
                        if len(estado.maos[player_id]) == 1:
                            if player_id not in estado.uno_safe:
                                estado.uno_safe.append(player_id)
                                alterou = True
                        
                        # 2. Verifica se pegou alguém no flagra (outros jogadores com 1 carta não safe)
                        for pid in estado.jogadores_conectados:
                            if pid != player_id:
                                if len(estado.maos[pid]) == 1 and pid not in estado.uno_safe:
                                    # Penalidade: Compra 2 cartas
                                    estado.comprar_carta(pid)
                                    estado.comprar_carta(pid)
                                    alterou = True

                    if alterou:
                        broadcast_sala(sala_atual, estado)
                
                # Configuração da Sala (Anfitrião)
                elif not estado.jogo_iniciado and player_id == estado.host_id:
                    if acao['tipo'] == MSG_INICIAR_JOGO:
                        # Verifica se tem jogadores suficientes (minimo 2)
                        num_jogadores = len(sala['clientes'])
                        
                        if num_jogadores >= 2:
                            estado.jogo_iniciado = True
                            broadcast_sala(sala_atual, estado)
                        else:
                            # Opcional: Enviar erro para o anfitrião avisando que precisa de mais gente
                            # Por enquanto, apenas ignora ou printa no server
                            print(f"Tentativa de iniciar com {num_jogadores} jogadores. Mínimo: 2")

    except Exception as e:
        print(f"Erro com cliente {addr}: {e}")
    
    finally:
        # Limpeza ao desconectar
        if sala_atual and sala_atual in salas:
            sala = salas[sala_atual]
            estado = sala['estado']
            
            if conn in sala['clientes']:
                sala['clientes'].remove(conn)
            
            # Remove do estado se ainda estiver lá (caso de crash/desconexão abrupta)
            if player_id is not None and player_id in estado.jogadores_conectados:
                estado.jogadores_conectados.remove(player_id)
                if player_id in estado.maos:
                    del estado.maos[player_id]
                
                # Migração de Anfitrião
                if estado.host_id == player_id and estado.jogadores_conectados:
                    estado.host_id = estado.jogadores_conectados[0]
                
                broadcast_sala(sala_atual, estado)
            
            # Se a sala ficar vazia, apaga
            if not sala['clientes']:
                del salas[sala_atual]
                print(f"Sala {sala_atual} removida (vazia).")
        
        conn.close()
        print(f"Conexão fechada: {addr}")

def start():
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

start()
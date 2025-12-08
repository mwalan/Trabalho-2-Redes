"""
ARQUIVO: servidor.py
FUNÇÃO: Gerenciar conexões, salas e jogos.
ARQUITETURA: Cliente-Servidor com Múltiplas Salas.
DESCRIÇÃO: Este arquivo implementa o servidor central do jogo UNO. Ele aceita conexões TCP,
gerencia múltiplas salas de jogo simultâneas, processa as mensagens dos clientes e mantém
o estado oficial de cada jogo (usando a classe EstadoJogo).
"""

import socket   # Biblioteca para comunicação de rede (TCP/IP)
import threading # Biblioteca para lidar com múltiplos clientes simultaneamente (Threads)
import pickle   # Biblioteca para serialização de objetos (enviar dados complexos pela rede)
# Importa as constantes e classes compartilhadas do protocolo
from protocolo import EstadoJogo, MSG_CRIAR_SALA, MSG_ENTRAR_SALA, MSG_LISTAR_SALAS, MSG_INICIAR_JOGO, MSG_GRITAR_UNO, MSG_SAIR_SALA, MSG_ERRO

# --- CONFIGURAÇÃO DO SERVIDOR ---
HOST = '0.0.0.0' # Escuta em todas as interfaces de rede disponíveis
PORT = 5555      # Porta onde o servidor vai rodar

# Cria o socket do servidor (AF_INET = IPv4, SOCK_STREAM = TCP)
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Permite reutilizar o endereço/porta imediatamente após fechar (evita erro "Address already in use")
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Vincula o socket ao endereço e porta
server.bind((HOST, PORT))
# Começa a escutar conexões
server.listen()
print(f"Servidor UNO rodando em {HOST}:{PORT}")

# --- ESTRUTURA DE DADOS GLOBAL ---
# Dicionário que armazena todas as salas ativas.
# Chave: Nome da sala (str)
# Valor: Dicionário {'estado': Objeto EstadoJogo, 'clientes': Lista de sockets conectados}
salas = {} 

def broadcast_sala(nome_sala, estado):
    """
    Envia uma mensagem para todos os jogadores conectados em uma sala específica.
    Útil para atualizar o estado do jogo para todos ao mesmo tempo.
    """
    if nome_sala not in salas: return
    
    sala = salas[nome_sala]
    # Serializa a mensagem apenas uma vez para eficiência (pickle é custoso)
    data = pickle.dumps(estado)
    
    for cliente in sala['clientes']:
        try:
            cliente.send(data)
        except:
            # Se falhar ao enviar (cliente caiu), ignora. 
            # A remoção do cliente será tratada no loop principal dele (handle_client).
            pass

def handle_client(conn, addr):
    """
    Função executada em uma thread separada para cada cliente conectado.
    Gerencia todo o ciclo de vida da conexão desse cliente.
    """
    print(f"Nova conexão: {addr}")
    sala_atual = None # Nome da sala onde o cliente está (None se estiver no lobby)
    player_id = None  # ID único do jogador (usamos o endereço IP:Porta como ID)

    try:
        while True:
            # --- LOOP DO LOBBY (Antes de entrar numa sala) ---
            if not sala_atual:
                data = conn.recv(4096)
                if not data: break # Conexão fechada pelo cliente
                req = pickle.loads(data)
                
                # 1. Listar Salas
                if req['tipo'] == MSG_LISTAR_SALAS:
                    # Monta uma lista com informações básicas de todas as salas
                    lista = []
                    for nome, info in salas.items():
                        estado = info['estado']
                        lista.append({
                            'nome': nome,
                            'jogadores': len(info['clientes']),
                            'status': 'Jogando' if estado.jogo_iniciado else 'Aguardando'
                        })
                    conn.send(pickle.dumps({'tipo': MSG_LISTAR_SALAS, 'salas': lista}))

                # 2. Criar Sala
                elif req['tipo'] == MSG_CRIAR_SALA:
                    nome = req['nome']
                    if nome in salas:
                        conn.send(pickle.dumps({'tipo': MSG_ERRO, 'msg': 'Sala já existe!'}))
                    else:
                        # Cria nova sala com estado inicial padrão
                        salas[nome] = {
                            'estado': EstadoJogo(), 
                            'clientes': []
                        }
                        conn.send(pickle.dumps({'tipo': 'SUCESSO_CRIAR'}))
                        # O cliente deve enviar ENTRAR_SALA em seguida automaticamente

                # 3. Entrar em Sala
                elif req['tipo'] == MSG_ENTRAR_SALA:
                    nome = req['nome']
                    if nome in salas:
                        sala = salas[nome]
                        estado = sala['estado']
                        
                        # Validações
                        if len(sala['clientes']) >= 4:
                            conn.send(pickle.dumps({'tipo': MSG_ERRO, 'msg': 'Sala cheia!'}))
                            continue
                            
                        if estado.jogo_iniciado:
                            conn.send(pickle.dumps({'tipo': MSG_ERRO, 'msg': 'Jogo já começou!'}))
                            continue

                        # Sucesso: Adiciona cliente à sala
                        sala_atual = nome
                        player_id = addr
                        sala['clientes'].append(conn)
                        
                        # Atualiza o estado do jogo
                        estado.jogadores_conectados.append(player_id)
                        estado.maos[player_id] = [] # Inicializa mão vazia
                        
                        # Define o primeiro jogador como anfitrião (Host)
                        if estado.host_id is None:
                            estado.host_id = player_id
                        
                        # Distribui as 7 cartas iniciais para este jogador
                        for _ in range(7):
                            estado.comprar_carta(player_id)
                        
                        # Envia confirmação para o cliente com seu ID
                        conn.send(pickle.dumps({'tipo': 'ENTROU', 'id': player_id}))
                        # Envia o estado atualizado para TODOS na sala (para verem o novo jogador)
                        broadcast_sala(sala_atual, estado)

                    else:
                        conn.send(pickle.dumps({'tipo': MSG_ERRO, 'msg': 'Sala não encontrada!'}))

            # --- LOOP DO JOGO (Dentro de uma sala) ---
            else:
                data = conn.recv(4096)
                if not data: break
                acao = pickle.loads(data)
                
                sala = salas[sala_atual]
                estado = sala['estado']
                
                # 4. Sair da Sala (Voltar ao Lobby)
                if acao['tipo'] == MSG_SAIR_SALA:
                    # Remove jogador da lista de clientes da sala
                    if conn in sala['clientes']:
                        sala['clientes'].remove(conn)
                    
                    # Remove jogador do estado do jogo
                    if player_id in estado.jogadores_conectados:
                        estado.jogadores_conectados.remove(player_id)
                        if player_id in estado.maos:
                            del estado.maos[player_id]
                        
                        # Se o anfitrião saiu, passa a liderança para o próximo
                        if estado.host_id == player_id and estado.jogadores_conectados:
                            estado.host_id = estado.jogadores_conectados[0]
                    
                    # Se a sala ficar vazia, ela é destruída
                    if not sala['clientes']:
                        del salas[sala_atual]
                    else:
                        # Avisa os outros que alguém saiu
                        broadcast_sala(sala_atual, estado)
                        
                    # Reseta variáveis locais para voltar ao loop do lobby
                    sala_atual = None
                    player_id = None
                    continue

                # 5. Processamento de Ações de Jogo
                if estado.jogo_iniciado:
                    alterou = False # Flag para saber se precisamos reenviar o estado
                    
                    # Ações do Jogador da Vez (Jogar ou Comprar)
                    if estado.jogadores_conectados[estado.jogador_atual] == player_id:
                        if acao['tipo'] == 'JOGAR':
                            cor = acao.get('cor_escolhida')
                            # Tenta jogar a carta (validação feita dentro de jogar_carta)
                            alterou = estado.jogar_carta(player_id, acao['indice'], cor)
                        elif acao['tipo'] == 'COMPRAR':
                            estado.comprar_carta(player_id)
                            estado.avancar_turno() # Passa a vez após comprar
                            alterou = True
                    
                    # Ações Globais (Qualquer um pode fazer a qualquer momento)
                    if acao['tipo'] == MSG_GRITAR_UNO:
                        # Caso 1: O próprio jogador grita UNO (para se proteger)
                        if len(estado.maos[player_id]) == 1:
                            if player_id not in estado.uno_safe:
                                estado.uno_safe.append(player_id)
                                alterou = True
                        
                        # Caso 2: Alguém grita UNO para denunciar outro (Counter-UNO)
                        for pid in estado.jogadores_conectados:
                            if pid != player_id:
                                # Se alguém tem 1 carta e NÃO está safe (esqueceu de gritar)
                                if len(estado.maos[pid]) == 1 and pid not in estado.uno_safe:
                                    # Penalidade: Compra 2 cartas
                                    estado.comprar_carta(pid)
                                    estado.comprar_carta(pid)
                                    alterou = True

                    # Se houve mudança no estado, envia para todos
                    if alterou:
                        broadcast_sala(sala_atual, estado)
                
                # 6. Configuração da Sala (Apenas Anfitrião antes do jogo começar)
                elif not estado.jogo_iniciado and player_id == estado.host_id:
                    if acao['tipo'] == MSG_INICIAR_JOGO:
                        # Verifica se tem jogadores suficientes (minimo 2)
                        num_jogadores = len(sala['clientes'])
                        
                        if num_jogadores >= 2:
                            estado.jogo_iniciado = True
                            broadcast_sala(sala_atual, estado)
                        else:
                            print(f"Tentativa de iniciar com {num_jogadores} jogadores. Mínimo: 2")

    except Exception as e:
        print(f"Erro com cliente {addr}: {e}")
    
    finally:
        # --- LIMPEZA AO DESCONECTAR ---
        # Garante que o jogador seja removido corretamente se a conexão cair
        if sala_atual in salas:
            sala = salas[sala_atual]
            estado = sala['estado']
            
            if conn in sala['clientes']:
                sala['clientes'].remove(conn)
            
            if player_id is not None and player_id in estado.jogadores_conectados:
                estado.jogadores_conectados.remove(player_id)
                if player_id in estado.maos:
                    del estado.maos[player_id]
                
                if estado.host_id == player_id and estado.jogadores_conectados:
                    estado.host_id = estado.jogadores_conectados[0]
                
                broadcast_sala(sala_atual, estado)
            
            if not sala['clientes']:
                del salas[sala_atual]
                print(f"Sala {sala_atual} removida (vazia).")
        
        conn.close()
        print(f"Conexão fechada: {addr}")

def start():
    """Função principal que aceita novas conexões."""
    while True:
        conn, addr = server.accept()
        # Cria uma nova thread para cada cliente
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

# Inicia o servidor
start()

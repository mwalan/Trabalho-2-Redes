# Relatório de Implementação de Rede: UNO Multiplayer

Este documento detalha as escolhas arquiteturais, protocolos e estruturas de código utilizadas para viabilizar a comunicação em rede do jogo UNO. O sistema foi projetado para garantir consistência de estado entre múltiplos jogadores simultâneos.

## 1. Arquitetura e Protocolos

### Topologia de Rede
O sistema utiliza uma arquitetura **Cliente-Servidor** (Topologia Estrela).
* **Centralização:** Cada cliente se conecta exclusivamente ao servidor.
* **Isolamento:** Os clientes nunca se comunicam diretamente entre si (sem P2P). O servidor atua como a autoridade central ("Source of Truth"), gerenciando toda a lógica e validação do jogo.

### Protocolo de Transporte: TCP
Foi escolhido o protocolo **TCP (Transmission Control Protocol)** em vez de UDP.
* **Justificativa:** O UNO é um jogo de turnos onde a integridade do estado é crítica. O TCP garante a **entrega** e a **ordem** dos pacotes. A perda de um único pacote (ex: uma carta "+4") quebraria a lógica do jogo, algo que o UDP não preveniria nativamente.

### Serialização de Dados: Pickle
A troca de mensagens utiliza a biblioteca nativa do Python, `pickle`.
* **Motivação:** Diferente de JSON ou XML, o `pickle` permite serializar objetos Python complexos diretamente.
* **Vantagem na Implementação:** O servidor envia a instância completa da classe `EstadoJogo`. O cliente recebe este objeto pronto para uso, eliminando a necessidade de *parsing* manual e reconstrução de estado no lado do cliente.

---

## 2. Implementação do Servidor (`servidor.py`)

O servidor é responsável por aceitar conexões, gerenciar salas e sincronizar o estado do jogo.

### Gerenciamento de Conexões (Socket Mestre)
* O servidor abre um socket mestre na **porta 5555** e entra em modo de escuta (`listen`).
* **Modelo de Concorrência (Threading):** Ao aceitar uma nova conexão, o servidor instancia imediatamente uma nova **Thread** apontando para a função `handle_client`.
    * *Importância:* Isso permite atender a múltiplos clientes simultaneamente. Sem o uso de threads, o servidor ficaria bloqueado atendendo o primeiro jogador, obrigando o segundo a esperar a desconexão do anterior para poder interagir.

### Funções Críticas de Rede

#### `handle_client(conn, addr)`
É a função que representa a "vida" da conexão de um jogador específico.
* **Execução:** Roda em paralelo (uma instância para cada jogador).
* **Lógica:** Opera em um loop infinito (`while True`) aguardando mensagens via `conn.recv`.
* **Máquina de Estados:** Gerencia o contexto do jogador, distinguindo se ele está no **"Lobby"** (criando/escolhendo salas) ou em **"Jogo"** (partida ativa).
* **Processamento:** Recebe ações (ex: `{'tipo': 'JOGAR', 'indice': 0}`), aplica as regras alterando o objeto `EstadoJogo` local e dispara a atualização para a sala.

#### `broadcast_sala(nome_sala, mensagem)`
Responsável pela sincronização em massa (Multicast lógico).
* **Funcionamento:** Itera sobre a lista de sockets conectados àquela sala específica (`sala['clientes']`).
* **Ação:** Executa um `send()` individual para cada cliente.
* **Uso:** É acionada sempre que o estado do jogo muda (ex: carta jogada, compra efetuada). Envia o objeto `EstadoJogo` atualizado para garantir que todos vejam exatamente a mesma mesa.

---

## 3. Implementação do Cliente (`cliente.py`)

O cliente atua como uma interface gráfica "burra", desenhando o estado recebido e capturando inputs.

### Inicialização
* **`client.connect((ip, porta))`**: Inicia o *Handshake* TCP (SYN, SYN-ACK, ACK) para estabelecer o túnel confiável de comunicação com o servidor.

### Funções Críticas de Rede

#### `enviar_acao(acao)`
Responsável pelo fluxo de saída (Output).
* **Processo:** Recebe um dicionário (ex: `{'tipo': 'COMPRAR'}`), serializa-o com `pickle.dumps()` e envia pelo socket (`client.send`).
* **Gatilho:** Chamada sempre que há interação do usuário (clique em botão, carta ou tecla).

#### `receber_dados()`
Responsável pelo fluxo de entrada (Input).
* **Execução:** Roda em uma **Thread paralela** (modo `daemon=True`). Isso é crucial para não travar a interface gráfica (Pygame) enquanto aguarda dados da rede.
* **Buffer:** Utiliza um buffer grande (`4096 * 8`) na leitura (`client.recv`), pois o objeto `EstadoJogo` serializado contém todas as cartas e variáveis, resultando em um pacote grande em bytes.
* **Sincronização:** Ao receber o objeto, atualiza a variável global `estado_local`. Na iteração seguinte do loop principal do Pygame, a tela é redesenhada refletindo o novo estado.

---

## 4. Exemplo Prático de Fluxo de Dados

Para ilustrar a interação entre os componentes, considere o cenário onde um jogador joga uma carta **"+4"**.

1.  **Cliente (Main Thread - Interface):**
    * Detecta o clique na carta "+4".
    * Abre o menu de escolha de cor e o usuário seleciona "Azul".
    * Invoca `enviar_acao({'tipo': 'JOGAR', 'indice': 2, 'cor': 'AZUL'})`.
    * O socket envia os bytes serializados para o servidor.

2.  **Servidor (Thread `handle_client` do usuário):**
    * Recebe os bytes e desserializa o objeto.
    * **Validação:** Verifica se é a vez do jogador, se ele possui a carta e se a regra permite a jogada.
    * **Execução:**
        * Move a carta da mão do jogador para o descarte.
        * Altera a cor atual do jogo para "Azul".
        * Aplica a penalidade (compra de 4 cartas) ao próximo jogador.
        * Avança o turno.
    * Invoca `broadcast_sala(sala, novo_estado_jogo)`.

3.  **Todos os Clientes da Sala (Thread `receber_dados`):**
    * Recebem o objeto `novo_estado_jogo`.
    * Atualizam suas variáveis locais `estado_local`.
    * **Resultado Visual:** O Pygame redesenha a tela: a carta do jogador some, o descarte é atualizado, o oponente recebe 4 cartas e a seta de turno aponta para o próximo jogador.
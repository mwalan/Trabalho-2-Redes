# UNO Multiplayer (Versão 2)

## Descrição

Este projeto é uma implementação multiplayer do clássico jogo de cartas UNO, desenvolvida como parte do Trabalho 2 da disciplina de Redes de Computadores. O objetivo foi criar uma aplicação distribuída robusta utilizando a arquitetura Cliente-Servidor.

O principal desafio abordado foi a sincronização de estado em tempo real entre múltiplos clientes e o servidor, garantindo que todos os jogadores vejam a mesma mesa, mãos e turnos. Além disso, foi implementado um sistema de salas (Lobby) que permite múltiplos jogos simultâneos no mesmo servidor.

## Tecnologias Utilizadas

- **Linguagem de Programação**: Python 3
- **Bibliotecas/Frameworks**:
  - `socket`: Para comunicação de rede via TCP/IP.
  - `pygame`: Para a interface gráfica do usuário (GUI).
  - `threading`: Para gerenciamento de conexões simultâneas e escuta de mensagens sem bloquear a interface.
  - `pickle`: Para serialização de objetos (envio de estruturas de dados complexas pela rede).

## Como Executar

### Requisitos

- Python 3.x instalado.
- Biblioteca `pygame` instalada.

### Instruções de Execução

1.  **Clone o repositório (se ainda não o fez):**

    ```bash
    git clone https://github.com/mwalan/Trabalho-2-Redes.git
    cd Trabalho-2-Redes
    ```

2.  **Instale as dependências:**

    ```bash
    pip install pygame
    ```

3.  **Execute o servidor:**
    O servidor deve ser o primeiro a ser iniciado. Ele ficará escutando na porta 5555.

    ```bash
    python3 v2/servidor.py
    ```

4.  **Execute o cliente:**
    Abra novos terminais para cada jogador que deseja conectar.
    ```bash
    python3 v2/cliente.py
    ```
    - Ao iniciar, o cliente pedirá o IP do servidor. Se estiver rodando localmente, apenas pressione **Enter** para usar `localhost`. Caso contrário coloque o **IPv4** da máquina que está rodando o servidor.

## Como Testar

1.  Inicie o servidor em um terminal.
2.  Abra pelo menos dois terminais adicionais e inicie o cliente em cada um.
3.  **No Cliente 1 (Anfitrião):**
    - No Lobby, digite um nome para a sala na caixa de texto.
    - Clique em **CRIAR**. Você entrará automaticamente na sala de espera.
4.  **No Cliente 2:**
    - A sala criada aparecerá na lista "Salas Disponíveis".
    - Clique no botão da sala para entrar.
5.  **Iniciando o Jogo:**
    - O anfitrião (Cliente 1) verá o botão **INICIAR JOGO** habilitado assim que houver 2 ou mais jogadores.
    - Clique em INICIAR JOGO.
6.  **Jogando:**
    - O jogo segue as regras padrão do UNO.
    - Clique nas cartas da sua mão para jogar (se for sua vez e a jogada for válida).
    - Se não tiver carta, clique no **Monte** para comprar.
    - Se tiver apenas 1 carta, lembre-se de clicar no botão **UNO!** para não sofrer penalidade.

## Funcionalidades Implementadas

- **Arquitetura Cliente-Servidor**: Servidor centralizado que gerencia o estado.
- **Sistema de Salas (Lobby)**: Criação e listagem de salas, permitindo múltiplos jogos isolados.
- **Regras Completas do UNO**:
  - Cartas Numéricas, Pular, Inverter, +2.
  - Cartas Especiais: Coringa (Muda Cor) e +4.
  - Validação de jogadas no servidor (anti-cheat básico).
- **Mecânica de "UNO!"**: Botão para gritar UNO quando tiver 1 carta. Penalidade automática se alguém denunciar (Counter-UNO).
- **Interface Gráfica**: Visualização da mesa, mão do jogador, oponentes (posicionados na mesa) e animações simples de hover.
- **Fim de Jogo**: Detecção de vitória e retorno ao Lobby.

## Possíveis Melhorias Futuras

- **Chat no Lobby/Sala**: Permitir comunicação por texto entre os jogadores.
- **Efeitos Sonoros**: Adicionar sons para compra, jogada e vitória.
- **Animações de Movimento**: Animar as cartas saindo da mão e indo para o descarte.
- **Reconexão**: Permitir que um jogador que caiu volte para a mesma sala e recupere sua mão.
- **Persistência**: Salvar histórico de partidas ou placar em banco de dados.

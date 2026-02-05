# Bot de Sorteio para Discord (Python)

Este projeto cria um bot para gerenciar sorteios com a regra:

- **1 ticket a cada 5.000 FE vendidos**.
- **Sem limite de tickets por pessoa**.
- Sorteio de **1 único vencedor**.
- Prêmio anunciado de **10.000 FE**.

## Requisitos

- Python 3.10+
- Conta de desenvolvedor Discord + bot criado

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuração

Defina as variáveis de ambiente:

- `DISCORD_TOKEN` (obrigatória): token do bot
- `RAFFLE_CHANNEL_ID` (opcional): ID do canal em que os comandos podem ser usados

Exemplo:

```bash
export DISCORD_TOKEN="seu_token_aqui"
export RAFFLE_CHANNEL_ID="123456789012345678"
python bot.py
```

## Permissões e estrutura de canal

Para respeitar seu fluxo (canal de visualização para membros e somente você enviando mensagens):

1. Crie um canal de texto para sorteio.
2. Nas permissões do canal:
   - `@everyone`: **sem** permissão de enviar mensagens.
   - Seu usuário/cargo de admin: com permissão de enviar mensagens.
   - Bot: com permissão de ler e enviar mensagens.
3. Use o ID desse canal na variável `RAFFLE_CHANNEL_ID`.

## Comandos

> Todos os comandos exigem permissão de **administrador**.

- `!add @usuario <fe>`
  - Adiciona FE ao participante.
  - Converte automaticamente em tickets com regra `fe // 5000`.
  - Exemplo: `!add @Joao 15000` -> 3 tickets.

- `!status @usuario`
  - Mostra FE acumulado e tickets do participante.

- `!list`
  - Lista todos os participantes com tickets e FE acumulados.

- `!draw`
  - Realiza o sorteio ponderado por tickets.
  - Anuncia 1 vencedor e prêmio de 10.000 FE.

- `!reset`
  - Limpa todos os participantes e tickets para um novo ciclo.

## Armazenamento

Os dados ficam em `raffle_data.json` no mesmo diretório do projeto.

## Observação

A lógica atual considera **tickets por lote informado** no comando `!add` (regra direta de negócio solicitada).

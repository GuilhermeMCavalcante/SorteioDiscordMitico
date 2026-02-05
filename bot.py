import json
import os
import random
from pathlib import Path
from typing import Dict, Any

import discord
from discord.ext import commands

DATA_FILE = Path("raffle_data.json")


def load_data() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        return {"participants": {}}

    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "participants" not in data:
        data["participants"] = {}

    return data


def save_data(data: Dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def tickets_from_fe(fe_value: int) -> int:
    return fe_value // 5000


def build_pool(participants: Dict[str, Dict[str, int]]) -> list[str]:
    pool: list[str] = []
    for user_id, info in participants.items():
        pool.extend([user_id] * info["tickets"])
    return pool


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
RAFFLE_CHANNEL_ID = os.getenv("RAFFLE_CHANNEL_ID")





async def validate_raffle_channel(ctx: commands.Context) -> bool:
    if not RAFFLE_CHANNEL_ID:
        return True

    return str(ctx.channel.id) == RAFFLE_CHANNEL_ID


@bot.check
async def global_channel_check(ctx: commands.Context) -> bool:
    if await validate_raffle_channel(ctx):
        return True

    await ctx.send("Use os comandos apenas no canal configurado para sorteio.")
    return False

@bot.event
async def on_ready() -> None:
    print(f"Bot online como {bot.user} (ID: {bot.user.id})")


@bot.command(name="add")
@commands.has_permissions(administrator=True)
async def add_participant(ctx: commands.Context, member: discord.Member, fe_value: int) -> None:
    """Adiciona FE para um participante e converte em tickets (1 ticket a cada 5.000 FE)."""
    if fe_value <= 0:
        await ctx.send("O valor de FE precisa ser maior que 0.")
        return

    gained_tickets = tickets_from_fe(fe_value)
    if gained_tickets == 0:
        await ctx.send("Esse valor não gera ticket. É necessário no mínimo 5.000 FE por ticket.")
        return

    data = load_data()
    participants = data["participants"]
    user_id = str(member.id)

    if user_id not in participants:
        participants[user_id] = {
            "name": member.display_name,
            "fe_total": 0,
            "tickets": 0,
        }

    participants[user_id]["name"] = member.display_name
    participants[user_id]["fe_total"] += fe_value
    participants[user_id]["tickets"] += gained_tickets

    save_data(data)

    await ctx.send(
        f"✅ {member.mention} recebeu **{gained_tickets} ticket(s)**. "
        f"Total atual: **{participants[user_id]['tickets']} ticket(s)** "
        f"({participants[user_id]['fe_total']} FE acumulados)."
    )


@bot.command(name="status")
@commands.has_permissions(administrator=True)
async def participant_status(ctx: commands.Context, member: discord.Member) -> None:
    data = load_data()
    participant = data["participants"].get(str(member.id))

    if not participant:
        await ctx.send(f"{member.mention} ainda não possui tickets.")
        return

    await ctx.send(
        f"📌 {member.mention}: {participant['tickets']} ticket(s), "
        f"{participant['fe_total']} FE acumulados."
    )


@bot.command(name="list")
@commands.has_permissions(administrator=True)
async def list_participants(ctx: commands.Context) -> None:
    data = load_data()
    participants = data["participants"]

    if not participants:
        await ctx.send("Nenhum participante cadastrado ainda.")
        return

    lines = ["🎟️ **Participantes do sorteio**"]
    for info in sorted(participants.values(), key=lambda i: i["tickets"], reverse=True):
        lines.append(f"- {info['name']}: {info['tickets']} ticket(s) | {info['fe_total']} FE")

    await ctx.send("\n".join(lines))


@bot.command(name="draw")
@commands.has_permissions(administrator=True)
async def draw_winner(ctx: commands.Context) -> None:
    """Sorteia 1 único vencedor para prêmio de 10.000 FE."""
    data = load_data()
    participants = data["participants"]

    pool = build_pool(participants)
    if not pool:
        await ctx.send("Não há tickets para realizar o sorteio.")
        return

    winner_id = int(random.choice(pool))
    winner = ctx.guild.get_member(winner_id)
    winner_mention = winner.mention if winner else f"<@{winner_id}>"

    await ctx.send(
        "🏆 **RESULTADO DO SORTEIO** 🏆\n"
        f"Vencedor: {winner_mention}\n"
        "Prêmio: **10.000 FE**"
    )


@bot.command(name="reset")
@commands.has_permissions(administrator=True)
async def reset_raffle(ctx: commands.Context) -> None:
    save_data({"participants": {}})
    await ctx.send("♻️ Sorteio resetado. Todos os participantes e tickets foram removidos.")


@add_participant.error
@participant_status.error
@list_participants.error
@draw_winner.error
@reset_raffle.error
async def admin_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Você não tem permissão para usar este comando.")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("Argumento inválido. Confira o comando e tente novamente.")
        return

    raise error


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Defina a variável de ambiente DISCORD_TOKEN com o token do bot.")

    bot.run(token)

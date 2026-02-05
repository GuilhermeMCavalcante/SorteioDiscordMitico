import json
import os
import random
from pathlib import Path
from typing import Any

import discord
from discord import app_commands

DATA_FILE = Path("raffle_data.json")
PRIZE_FE = 10000
TICKET_FE_RATIO = 5000


def load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return {"participants": {}}

    with DATA_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "participants" not in data:
        data["participants"] = {}

    return data


def save_data(data: dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def tickets_from_fe(fe_value: int) -> int:
    return fe_value // TICKET_FE_RATIO


def build_pool(participants: dict[str, dict[str, int]]) -> list[str]:
    pool: list[str] = []
    for user_id, info in participants.items():
        pool.extend([user_id] * info["tickets"])
    return pool


class RaffleBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.raffle_channel_id = os.getenv("RAFFLE_CHANNEL_ID")

    async def setup_hook(self) -> None:
        await self.tree.sync()

    async def on_ready(self) -> None:
        if self.user is not None:
            print(f"Bot online como {self.user} (ID: {self.user.id})")


bot = RaffleBot()


def has_admin(interaction: discord.Interaction) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    return interaction.user.guild_permissions.administrator


async def validate_context(interaction: discord.Interaction) -> tuple[bool, str | None]:
    if not has_admin(interaction):
        return False, "Você não tem permissão para usar este comando."

    if bot.raffle_channel_id and str(interaction.channel_id) != bot.raffle_channel_id:
        return False, "Use os comandos apenas no canal configurado para sorteio."

    if interaction.guild is None:
        return False, "Este comando só pode ser usado dentro de um servidor."

    return True, None


@bot.tree.command(name="add", description="Adiciona FE para um usuário e converte em tickets")
@app_commands.describe(member="Membro que receberá os tickets", fe_value="Valor de FE adicionado")
async def add_participant(interaction: discord.Interaction, member: discord.Member, fe_value: int) -> None:
    valid, error = await validate_context(interaction)
    if not valid:
        await interaction.response.send_message(error, ephemeral=True)
        return

    if fe_value <= 0:
        await interaction.response.send_message("O valor de FE precisa ser maior que 0.", ephemeral=True)
        return

    gained_tickets = tickets_from_fe(fe_value)
    if gained_tickets == 0:
        await interaction.response.send_message(
            "Esse valor não gera ticket. É necessário no mínimo 5.000 FE por ticket.",
            ephemeral=True,
        )
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

    await interaction.response.send_message(
        f"✅ {member.mention} recebeu **{gained_tickets} ticket(s)**. "
        f"Total atual: **{participants[user_id]['tickets']} ticket(s)** "
        f"({participants[user_id]['fe_total']} FE acumulados)."
    )


@bot.tree.command(name="status", description="Mostra status de tickets de um participante")
@app_commands.describe(member="Membro para consultar")
async def participant_status(interaction: discord.Interaction, member: discord.Member) -> None:
    valid, error = await validate_context(interaction)
    if not valid:
        await interaction.response.send_message(error, ephemeral=True)
        return

    data = load_data()
    participant = data["participants"].get(str(member.id))

    if not participant:
        await interaction.response.send_message(f"{member.mention} ainda não possui tickets.")
        return

    await interaction.response.send_message(
        f"📌 {member.mention}: {participant['tickets']} ticket(s), "
        f"{participant['fe_total']} FE acumulados."
    )


@bot.tree.command(name="list", description="Lista participantes e tickets")
async def list_participants(interaction: discord.Interaction) -> None:
    valid, error = await validate_context(interaction)
    if not valid:
        await interaction.response.send_message(error, ephemeral=True)
        return

    data = load_data()
    participants = data["participants"]

    if not participants:
        await interaction.response.send_message("Nenhum participante cadastrado ainda.")
        return

    lines = ["🎟️ **Participantes do sorteio**"]
    for info in sorted(participants.values(), key=lambda i: i["tickets"], reverse=True):
        lines.append(f"- {info['name']}: {info['tickets']} ticket(s) | {info['fe_total']} FE")

    await interaction.response.send_message("\n".join(lines))


@bot.tree.command(name="draw", description="Realiza o sorteio de um único vencedor")
async def draw_winner(interaction: discord.Interaction) -> None:
    valid, error = await validate_context(interaction)
    if not valid:
        await interaction.response.send_message(error, ephemeral=True)
        return

    data = load_data()
    participants = data["participants"]
    pool = build_pool(participants)

    if not pool:
        await interaction.response.send_message("Não há tickets para realizar o sorteio.")
        return

    winner_id = int(random.choice(pool))
    winner = interaction.guild.get_member(winner_id) if interaction.guild else None
    winner_mention = winner.mention if winner else f"<@{winner_id}>"

    await interaction.response.send_message(
        "🏆 **RESULTADO DO SORTEIO** 🏆\n"
        f"Vencedor: {winner_mention}\n"
        f"Prêmio: **{PRIZE_FE:,} FE**".replace(",", ".")
    )


@bot.tree.command(name="reset", description="Reseta todos os participantes e tickets")
async def reset_raffle(interaction: discord.Interaction) -> None:
    valid, error = await validate_context(interaction)
    if not valid:
        await interaction.response.send_message(error, ephemeral=True)
        return

    save_data({"participants": {}})
    await interaction.response.send_message("♻️ Sorteio resetado. Todos os participantes e tickets foram removidos.")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Defina a variável de ambiente DISCORD_TOKEN com o token do bot.")

    bot.run(token)

import math
import os
from dotenv import load_dotenv
import discord
from discord import app_commands
import requests, json
import helpers
import aiohttp
import asyncio

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_GUILD = os.getenv('DISCORD_GUILD')
BASE_URL = os.getenv('BASE_URL')
ITEM_URL = BASE_URL + os.getenv('ITEM_URL')
ITEM_IMAGE_URL = BASE_URL + os.getenv('ITEM_IMAGE_URL')
QUESTS_URL = os.getenv('QUESTS_URL')
PROJECTS_URL = os.getenv('PROJECTS_URL')
WORKSHOP_URL = os.getenv('WORKSHOP_URL')

# Helper function: fetch JSON from a URL
async def fetch_json(session, url):
    async with session.get(url) as resp:
        text= await resp.text()
        return json.loads(text)


@tree.command(
    name="recycle",
    description="Search an item to see where it's used",
    guild=discord.Object(id=DISCORD_GUILD)
)

@app_commands.describe(item="The item you're searching for")
async def recycle(interaction: discord.Interaction,
                  item: str):
    await interaction.response.defer(thinking=True)
    print(f'Searching for {item}')
    item = helpers.sanitise_item(item)
    print(f'Sanitised string: {item}')
    # search the quest list
    # get list of quest files
    required_quests = []
    async with aiohttp.ClientSession() as session:
        async with session.get(QUESTS_URL) as response:
            files = await response.json()

        # launch downloads in parallel
        tasks = [
            fetch_json(session, file["download_url"])
            for file in files if file["name"].endswith(".json")
        ]

        quests = await asyncio.gather(*tasks)
        for quest in quests:
            for granted in quest.get("grantedItemIds", []):
                if granted.get("itemId") == item:
                    required_quests.append(quest["name"]["en"])


    # search the workshop list
    required_workshops = []
    async with aiohttp.ClientSession() as session:
        async with session.get(WORKSHOP_URL) as response:
            files = await response.json()

        tasks = [
            fetch_json(session,file["download_url"])
            for file in files if file["name"].endswith(".json")
        ]

        workshops = await asyncio.gather(*tasks)
        for workshop in workshops:
            for level in workshop.get("levels",[]):
                for req in level.get("requirementItemIds",[]):
                    if req.get("itemId") == item:
                        required_workshops.append(f'{workshop["id"]} Level {level["level"]}')

    # search projects/expeditions
    required_phases=[]
    response = requests.get(PROJECTS_URL)
    if response.status_code == 200:
        projects = response.json()
        # for phase in projects.get("phases",[]):
        #     for req in phase.get("requirementItemIds",[]):
        #         if req.get("itemId") == item:
        #             required_phases.append(phase["phase"])
        for project in projects:  # iterate the list
            for phase in project.get("phases", []):  # now .get works
                for req in phase.get("requirementItemIds", []):
                    if req.get("itemId") == item:
                        required_phases.append(f'Expedition Project {phase["phase"]}')
    else:
        required_phases.append("Couldn't search projects")



    # get the image
    item_to_search = ITEM_URL + item + '.json'
    response = requests.get(item_to_search)
    if response.status_code == 200:
        message_text = response.json()
        embed = discord.Embed(
            title=item,
            description='poo',
        )
        embed.set_image(url=f'{ITEM_IMAGE_URL}{item}.png')
        # add quests
        embed.add_field(name="Quests",value=required_quests)
        embed.add_field(name="Projects",value=required_phases)
        embed.add_field(name="Workshops",value=required_workshops)
        await interaction.followup.send(embed=embed)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await tree.sync(guild=discord.Object(id=DISCORD_GUILD))

client.run(DISCORD_TOKEN)
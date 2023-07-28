import os
import time
import datetime
from brownie import *

# Initialize API keys
ARBISCAN_TOKEN = '371ZEJCDH4M4B5VT1NY8QAEHPK6PB5R7P4'
os.environ["ARBISCAN_TOKEN"] = ARBISCAN_TOKEN

ACCOUNT_NAME = os.getenv('ACCOUNT_NAME')
PASSWORD = os.getenv('ACCOUNT_PW')

user = accounts.load(ACCOUNT_NAME, PASSWORD)
network.connect('arbitrum-main')

# Load the token contracts
print('Loading Contracts:')
weth_contract = Contract.from_explorer('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')
rdpx_contract = Contract.from_explorer('0x32Eb7902D4134bf98A28b963D26de779AF92A212')

# Load the SushiSwapRouter
router = Contract.from_explorer('0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506')

# Create dictionaries for our tokens
rdpx = {
    "address": rdpx_contract.address,
    "symbol": rdpx_contract.symbol(),
    "decimals": rdpx_contract.decimals(),
}
weth = {
    "address": weth_contract.address,
    "symbol": weth_contract.symbol(),
    "decimals": weth_contract.decimals(),
}

# Initialize ratios at 0
rdpx_to_weth_ratio = 0.0
weth_to_rdpx_ratio = 0.0


# 
# THE LOOP
#
print('Starting the loop...')
while True:

    try:
        # get rDPX to WETH ratio
        weth_quantity_out = (
                router.getAmountsOut(
                    1 * (10 ** rdpx["decimals"]),
                    [
                        rdpx["address"],
                        weth["address"],
                    ],
                )[-1] / (10 ** weth["decimals"])
            )

        if weth_quantity_out != rdpx_to_weth_ratio:
            rdpx_to_weth_ratio = weth_quantity_out
            print(
                    f"{datetime.datetime.now().strftime('[%H:%M:%S]')} | {rdpx['symbol']} -> {weth['symbol']} | ({weth_quantity_out:.6f})"
                )


        # Get the currend weth -> rdpx ratio
        rdpx_quantity_out = (
            router.getAmountsOut(
                1 * (10 ** weth["decimals"]),
                [
                    weth["address"],
                    rdpx["address"],
                ],
            )[-1] / (10 ** rdpx["decimals"])
        )

        if rdpx_quantity_out != weth_to_rdpx_ratio:
            weth_to_rdpx_ratio = rdpx_quantity_out
            print(
                    f"{datetime.datetime.now().strftime('[%H:%M:%S]')} | {weth['symbol']} -> {rdpx['symbol']} | ({rdpx_quantity_out:.6f})"
                )
    except Exception as e:
        print(f"Error: {e} \n\nWill wait 30 seconds and try again...")
        time.sleep(30)
        continue
        

    # take a break
    time.sleep(3)
        

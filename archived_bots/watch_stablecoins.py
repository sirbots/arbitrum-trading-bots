import os
import sys
import time
import datetime
from brownie import *

# Initialize API keys
WEB3_INFURA_PROJECT_ID = os.getenv('WEB3_INFURA_PROJECT_ID')
ARBISCAN_TOKEN = '371ZEJCDH4M4B5VT1NY8QAEHPK6PB5R7P4'
os.environ["ARBISCAN_TOKEN"] = ARBISCAN_TOKEN

ACCOUNT_NAME = os.getenv('ACCOUNT_NAME')
PASSWORD = os.getenv('ACCOUNT_PW')

try:
    network.connect('arbitrum-main')        
except:
    sys.exit(
        "Could not connect to Arbitrum! Verify that brownie lists the Arbitrum Mainnet using 'brownie networks list'"
    )
try:
    user = accounts.load(ACCOUNT_NAME, PASSWORD)
except:
    sys.exit(
        "Could not load account! Verify that your account is listed using 'brownie accounts list' and that you are using the correct password. If you have not added an account, run 'brownie accounts new' now."
    )


# Load the token contracts
print('Loading Contracts...\n')

# stablecoin contracts
dai_contract = Contract.from_explorer('0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1')
# dusd_contract = Contract.from_explorer('0xF0B5cEeFc89684889e5F7e0A7775Bd100FcD3709') # liquidity is too low. 
# frax_contract = Contract.from_explorer('0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F') # liquidity is too low
mim_contract = Contract.from_explorer('0xFEa7a6a0B346362BF88A9e4A88416B77a57D6c2A')
usdc_contract = Contract.from_explorer('0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')
usdt_contract = Contract.from_explorer('0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9')
# tusd_contract = Contract.from_explorer('0x4D15a3A2286D883AF0AA1B3f21367843FAc63E07') # has no symbol or decimals methods and very low liquidity


# weth and router contracts
weth_contract = Contract.from_explorer('0x82aF49447D8a07e3bd95BD0d56f35241523fBab1')
router = Contract.from_explorer('0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506')


# Create dictionaries for our tokens
dai = {
    "address": dai_contract.address,
    "symbol": dai_contract.symbol(),
    "decimals": dai_contract.decimals(),
}
# dusd = {
#     "address": dusd_contract.address,
#     "symbol": dusd_contract.symbol(),
#     "decimals": dusd_contract.decimals(),
#}
# frax = {
#     "address": frax_contract.address,
#     "symbol": frax_contract.symbol(),
#     "decimals": frax_contract.decimals(),
# }
mim = {
    "address": mim_contract.address,
    "symbol": mim_contract.symbol(),
    "decimals": mim_contract.decimals(),
}
usdc = {
    "address": usdc_contract.address,
    "symbol": usdc_contract.symbol(),
    "decimals": usdc_contract.decimals(),
}
usdt = {
    "address": usdt_contract.address,
    "symbol": usdt_contract.symbol(),
    "decimals": usdt_contract.decimals(),
}

# A list of tuples with our dictionaries
token_pairs = [
    # (dai, dusd),
    # (dusd, dai),
    # (dai, frax),
    # (frax, dai),
    (dai, mim),
    (mim, dai),
    (dai, usdc),
    (usdc, dai),
    (dai, usdt),
    (usdt, dai),

    # (dusd, frax),
    # (frax, dusd),
    # (dusd, mim),
    # (mim, dusd),
    # (dusd, usdc),
    # (usdc, dusd),
    # (dusd, usdt),
    # (usdt, dusd),
    
    # (frax, mim),
    # (mim, frax),
    # (frax, usdc),
    # (usdc, frax),
    # (frax, usdt),
    # (usdt, frax),
    
    (mim, usdc),
    (usdc, mim),
    (mim, usdt),
    (usdt, mim),

    (usdc, usdt),
    (usdt, usdc),
]


#
# Config Variables
#
THRESHOLD = 1.01
PAIR_SLEEP_TIME = 1
LOOP_SLEEP_TIME = 60

print('Starting the loop...')
while True:
    for pair in token_pairs:
        token_in = pair[0]
        token_out = pair[1]
        quantity_out = (
            router.getAmountsOut(
                1 * (10 ** token_in["decimals"]),
                [
                    token_in["address"],
                    weth_contract.address,
                    token_out["address"],
                ],
            )[-1] / (10 ** token_out["decimals"])
        )   
        if quantity_out >= THRESHOLD:
            print(
                f"{datetime.datetime.now().strftime('[%I:%M:%S %p]')} {token_in['symbol']} -> {token_out['symbol']}: ({quantity_out:.3f})"
            )
        time.sleep(PAIR_SLEEP_TIME)
    time.sleep(LOOP_SLEEP_TIME)
        



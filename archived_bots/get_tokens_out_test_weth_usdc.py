import os
from os.path import exists
import csv
import sys
import time
import datetime
from decimal import Decimal
from brownie import *


# Initialize API keys
WEB3_INFURA_PROJECT_ID = os.getenv('WEB3_INFURA_PROJECT_ID')

# Contract addresses
SUSHI_ROUTER_CONTRACT_ADDRESS = "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
TOKEN_POOL_CONTRACT_ADDRESS = "0x905dfCD5649217c42684f23958568e533C711Aa3" # Sushi WETH-USDC pool

def get_tokens_out_from_tokens_in(
    pool_reserves_token0,
    pool_reserves_token1,
    quantity_token0_in = 0,
    quantity_token1_in = 0,
    fee = 0
):
    # fails if two input tokens are passed, or if both are 0
    # assert will raise an error if the condition does not evaulate to True.
    # Since this function calculates a swap in two different modes (depending whether quantity_token0_in or quantity_token1_in is defined), I want to be sure that the function is not called in an ambiguous way. Thus I assert that both modes are not called at the same time, and that some positive value was passed in if that passes. An assert is not the same as error handling, since it will fail and stop the program immediately.
    assert not (quantity_token0_in and quantity_token1_in)
    assert quantity_token0_in or quantity_token1_in

    if quantity_token0_in:
        return (pool_reserves_token1 * quantity_token0_in * (1 - fee)) // (pool_reserves_token0 + quantity_token0_in * (1 - fee))

    if quantity_token1_in:
        return (pool_reserves_token0 * quantity_token1_in * (1 - fee)) // (pool_reserves_token1 + quantity_token1_in * (1 - fee))


def contract_load(address, alias):
    # Attempts to load the saved contract by alias.
    # If not found, fetch from network explorer and set alias.
    try:
        contract = Contract(alias)
    except ValueError:
        contract = Contract.from_explorer(address)
        contract.set_alias(alias)
    finally:
        print(f"• {alias}")
        return contract

def get_swap_rate(token_in_quantity, token_in_address, token_out_address, contract):
    try:
        return contract.getAmountsOut(
            token_in_quantity, [token_in_address, token_out_address]
        )
    except Exception as e:
        print(f"Exception in get_swap_rate: {e}")
        return False 


try:
    network.connect('arbitrum-main')
except:
    sys.exit(
        "Could not connect to Arbitrum! Verify that brownie lists the Arbitrum Mainnet using 'brownie networks list'"
    )


print("\nContracts loaded:")
lp = contract_load(TOKEN_POOL_CONTRACT_ADDRESS, "Sushi LP: WETH-USDC")
router = contract_load(SUSHI_ROUTER_CONTRACT_ADDRESS, "Sushi: Router")

token0 = Contract.from_explorer(lp.token0.call())
token1 = Contract.from_explorer(lp.token1.call())

print()
print(f"token0 = {token0.symbol.call()}")
print(f"token1 = {token1.symbol.call()}")

print()
print("*** Getting Pool Reserves *** ")
x0, y0 = lp.getReserves.call()[0:2]
print(f"token0: \t\t\t{x0}")
print(f"token1: \t\t\t{y0}")

300000
300_000


print()
print("*** Calculating hypothetical swap: 500,000 WETH to USDC @ 0.3% fee ***")
quote = router.getAmountsOut(500_000 * (10 ** 18), [token1.address, token0.address])[-1]
tokens_out = get_tokens_out_from_tokens_in(
    pool_reserves_token0=x0,
    pool_reserves_token1=y0,
    quantity_token1_in=500_000 * (10 ** 18),
    fee=Decimal("0.003"),
)
print()
print(f"Calculated Tokens Out: \t\t{tokens_out}")
print(f"Router Quoted getAmountsOut: \t{quote}")
print(f"Difference: \t\t\t{quote - tokens_out}")

print()
print("*** Calculating hypothetical swap: 500,000 USDC to WETH @ 0.3% fee ***")
quote = router.getAmountsOut(
    500_000 * (10 ** 18),
    [token0.address, token1.address],
)[-1]
tokens_out = get_tokens_out_from_tokens_in(
    pool_reserves_token0=x0,
    pool_reserves_token1=y0,
    quantity_token0_in=500_000 * (10 ** 18),
    fee=Decimal("0.003"),
)
print()
print(f"Calculated Tokens Out: \t\t{tokens_out}")
print(f"Router Quoted getAmountsOut: \t{quote}")
print(f"Difference: \t\t\t{quote - tokens_out}")


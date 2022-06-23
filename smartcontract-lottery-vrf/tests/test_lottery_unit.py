from scripts.helpful_scripts import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    get_account,
    fund_with_link,
    get_contract,
)
from brownie import Lottery, accounts, config, network, exceptions
from scripts.deploy_lottery import deploy_lottery
from web3 import Web3
import pytest


def test_get_entrance_fee():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    # ARRANGE
    lottery = deploy_lottery()
    # ACT
    # assuming 2000eth/usd
    # 2000/1 == 50/x == 0.025
    expected_entrance_fee = Web3.toWei(0.025, "ether")
    entrance_fee = lottery.getEntranceFee()
    # ASSERT
    assert expected_entrance_fee == entrance_fee


def test_cant_enter_unless_started():
    # ARRANGE
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    # ACT/ASSERT
    with pytest.raises(exceptions.VirtualMachineError):
        tx = lottery.enter({"from": get_account(), "value": lottery.getEntranceFee()})
        tx.wait(1)


def test_can_start_and_enter_lottery():
    # ARRANGE
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    tx = lottery.startLottery({"from": account})
    tx.wait(1)
    # Act
    tx2 = lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    tx2.wait(1)
    # Assert
    assert lottery.players(0) == account


def test_can_end_lottery():
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    tx = lottery.startLottery({"from": account})
    tx.wait(1)
    tx1 = lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    tx1.wait(1)
    fund_with_link(lottery)
    tx2 = lottery.endLottery({"from": account})
    tx2.wait(1)
    assert lottery.lottery_state() == 2


def test_can_pick_winner_correctly():
    # Arrange
    if network.show_active() not in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        pytest.skip()
    lottery = deploy_lottery()
    account = get_account()
    tx = lottery.startLottery({"from": account})
    tx.wait(1)
    tx1 = lottery.enter({"from": account, "value": lottery.getEntranceFee()})
    tx1.wait(1)
    tx2 = lottery.enter(
        {"from": get_account(index=1), "value": lottery.getEntranceFee()}
    )
    tx2.wait(1)
    tx3 = lottery.enter(
        {"from": get_account(index=2), "value": lottery.getEntranceFee()}
    )
    tx3.wait(1)
    fund_with_link(lottery)
    transaction = lottery.endLottery({"from": account})
    requestId = transaction.events["RequestedRandomness"]["requestId"]
    STATIC_RNG = 777
    get_contract("vrf_coordinator").callBackWithRandomness(
        requestId, STATIC_RNG, lottery.address, {"from": account}
    )
    starting_balance_of_account = account.balance()
    balance_of_lottery = lottery.balance()
    # 777%3=0 therefore original account should win
    assert lottery.recentWinner() == account
    assert lottery.balance() == 0
    assert account.balance() == starting_balance_of_account + balance_of_lottery
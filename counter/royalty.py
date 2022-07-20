"""
    ASC for Algorand-facing endpoint for the custom NFT bridge
    Performs following actions:
    1. Wraps an ERC20 token (like USDC) into a fungible ASA
    2. Adjusts HAND token pool reserves to keep the HAND:stablecoin ratio at 1:1
    3. Fixed price Cross-chain Automated Market Maker(AMM) used:
    HAND Token price = (ERC20 Reserve on Ethereum / HAND token reserve on Algorand) = 1 USD
    4. Swaps Platform token ASAs from one platform to another. Must have the platform token ASAs sent to it and held in reserve
"""

from typing import List
from pyteal import *
from pyteal.ast.bytes import Bytes
from pyteal_helpers import program
 
def approval():
    #globals
    global_owner = Bytes("owner")  # byteslice
    global_reservebalance = Bytes("reservebalance")  # uint64


    #Scratch Varibles for looping over Txn arguments
    scratch_counter_algos = ScratchVar(TealType.uint64)
    scratch_counter_assets = ScratchVar(TealType.uint64)

    #Scratch Varible for Storing Trannsaction argument length
    # asa_arg_len = ScratchVar(TealType.uint64)
    # algo_arg_len = ScratchVar(TealType.uint64)

 
    # operations for adjusting reserves
    op_adjustplus = Bytes("adjustplus")
    op_adjustminus = Bytes("adjustminus")
    op_holdassetsoptin = Bytes("holdassetsoptin")
    op_transferassetout = Bytes("transferassetout")
    op_transferassetprogram = Bytes("transferassetprogram")


    #



    #Operation for Royalty
    op_royalty_algos_transfer= Bytes("payout_algos")
    op_royalty_asset_transfer = Bytes("payout_asset")

 
    adjust_reserve_plus = Seq(
        [
            App.globalPut(global_reservebalance, App.globalGet(global_reservebalance) + Btoi(Txn.application_args[1])),
            Approve(),
        ]
    )
 
    adjust_reserve_minus = Seq(
        [
            App.globalPut(global_reservebalance, App.globalGet(global_reservebalance) - Btoi(Txn.application_args[1])),
            Approve(),
        ]
    )
 
    hold_assets_optin = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.AssetTransfer,
            # TxnField.asset_receiver: Txn.sender(),
            TxnField.asset_receiver: Global.current_application_address(),
            TxnField.asset_amount: Int(0), #opt-in to the asset
            TxnField.xfer_asset: Txn.assets[0], # Must be in the assets array sent as part of the application call
        }),
        InnerTxnBuilder.Submit(),
        Approve(),
    )
 
    transfer_asset_out = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.asset_receiver: Txn.sender(),
            TxnField.asset_amount: Btoi(Txn.application_args[1]),  
            TxnField.xfer_asset: Txn.assets[0], # Must be in the assets array sent as part of the application call
        }),
        InnerTxnBuilder.Submit(),
        Approve(),
    )
 
    transfer_asset_programswap = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.asset_receiver: Txn.application_args[1],
            TxnField.asset_amount: Btoi(Txn.application_args[2]), # this amount is already pre-multiplied with the appropriate multiplier value
            TxnField.xfer_asset: Txn.assets[0], # Must be in the assets array sent as part of the application call
        }),
        InnerTxnBuilder.Submit(),
        Approve(),
    )
 
    payout_royalty_algos = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.asset_receiver: Txn.application_args[1],
            TxnField.asset_amount: Btoi(Txn.application_args[2]), # this amount is already pre-multiplied with the appropriate multiplier value
            TxnField.xfer_asset: Txn.assets[0], # Must be in the assets array sent as part of the application call
        }),
        InnerTxnBuilder.Submit(),
        Approve(),
    )  
 
    payout_royalty_asa = Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.ApplicationCall,
            TxnField.asset_receiver: Txn.application_args[1],
            TxnField.asset_amount: Btoi(Txn.application_args[2]), # this amount is already pre-multiplied with the appropriate multiplier value
            TxnField.xfer_asset: Txn.assets[0], # Must be in the assets array sent as part of the application call
        }),
        InnerTxnBuilder.Submit(),
        Approve(),
    )
    
    
    #Paying Royalty with multiple arguments

    payout_algos =Seq(
        #InnerTxnBuilder.Begin(),
        #scratch_counter_algos.store(Int(1)),
        #For(counter_algos.store(1), counter_algos.load()<Btoi(Txn.application_args[0])+1,
        For(scratch_counter_algos.store(Int(1)), scratch_counter_algos.load()<Btoi(Txn.application_args[0]),
        scratch_counter_algos.store(scratch_counter_algos.load()+Int(1))
        ).Do(Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.Payment,
                TxnField.receiver: Txn.application_args[scratch_counter_algos.load()],
                TxnField.amount: Btoi(Txn.application_args[scratch_counter_algos.load()+Btoi(Txn.application_args[0])]),
            }),
            InnerTxnBuilder.Submit(),
        ])
        ),
        Approve(),
    )

    payout_asset =Seq(
        For(scratch_counter_assets.store(Int(1)), scratch_counter_assets.load()<Btoi(Txn.application_args[0])+Int(1),
        scratch_counter_assets.store(scratch_counter_assets.load()+Int(1))
        ).Do(Seq([
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields({
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.asset_receiver: Txn.application_args[scratch_counter_assets.load()],
                TxnField.asset_amount: Btoi(Txn.application_args[scratch_counter_assets.load()+Btoi(Txn.application_args[0])]),
                }),
                 InnerTxnBuilder.Submit(),
            ])
        ),
        Approve(),
    )

    # @Subroutine

    # def SendPayment(Expr:List):

    #     return Seq(
    #         For(scratch_counter_assets.store(Int(1)), scratch_counter_assets.load()<Btoi(Txn.application_args[0])+Int(1),
    #     scratch_counter_assets.store(scratch_counter_assets.load()+Int(1))
    #     ).Do(Seq([
    #         InnerTxnBuilder.Begin(),
    #         InnerTxnBuilder.SetFields({
    #             TxnField.type_enum: TxnType.AssetTransfer,
    #             TxnField.asset_receiver: Txn.application_args[scratch_counter_assets.load()],
    #             TxnField.asset_amount: Btoi(Txn.application_args[scratch_counter_assets.load()+Btoi(Txn.application_args[0])]),
    #             }),
    #              InnerTxnBuilder.Submit(),
    #         ])
    #     ),
    #     Approve(),
    # )

        


 
    return program.event(
        init=Seq(
            [
                App.globalPut(global_owner, Txn.sender()),
                App.globalPut(global_reservebalance, Int(0)),
                Approve(),
            ]
        ),
        no_op=Cond(
            [Txn.application_args[0] == op_adjustplus, adjust_reserve_plus],
            [Txn.application_args[0] == op_adjustminus, adjust_reserve_minus],
            [Txn.application_args[0] == op_holdassetsoptin, hold_assets_optin],
            [Txn.application_args[0] == op_transferassetout, transfer_asset_out],
            [Txn.application_args[0] == op_transferassetprogram, transfer_asset_programswap],

            #
           # [Txn.application_args[0] == op_algos_transfer, ],




            #Operations
            [Txn.application_args[0] == op_royalty_algos_transfer, payout_algos],
            [Txn.application_args[0] == op_royalty_asset_transfer, payout_asset ],
        ),
    )
 
def clear():
    return Int(1)

# M6K33UYTNJDOTH5QPK7N2WOXGR3N7OVQSDPSEVBYNNZGUZLHY2XWSKW3CI
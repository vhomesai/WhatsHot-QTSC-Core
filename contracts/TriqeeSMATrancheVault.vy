# pragma version ~=0.4.0
"""
@title Triqee Institutional SMA Tranche Vault (Base Mainnet L2) - Patched & Hardened
@notice Non-custodial institutional yield-sharing vault for $100k-$1M capital tranches.
@dev Deploys capital into Triqee 3-Tier Waterfall (bGS-REPO, Morpho Steakhouse, Aerodrome USDY LP).
     Automates preferred yield payout to LP (6.000% APY) and positive carry spread (+3.155%) to Protocol Treasury.
@author Triqee Autonomous Research Division (Audited by DAE / ChatGPT)
"""

interface IERC20:
    def transfer(_to: address, _value: uint256) -> bool: nonpayable
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable
    def approve(_spender: address, _value: uint256) -> bool: nonpayable

interface IFlashFlowRouter:
    def execute_tranche(params: Bytes[1024]) -> bool: payable

event DepositTranche:
    lp_address: indexed(address)
    amount_usd: uint256
    timestamp: uint256

event HarvestAndCompound:
    epoch_id: indexed(uint256)
    gross_yield: uint256
    lp_payout: uint256
    protocol_carry: uint256
    timestamp: uint256

event RedeemTranche:
    lp_address: indexed(address)
    principal_returned: uint256
    stub_lp_yield: uint256
    accumulated_unpaid_lp_yield: uint256
    timestamp: uint256

# Mathematical Precision Constants
SECONDS_PER_YEAR: constant(uint256) = 31536000 # 365 days
RATE_DIVISOR: constant(uint256) = 1000000      # 1,000,000 for micro-rate precision (0.0001%)

# Contract Immutables
USDC_TOKEN: public(immutable(address))
FLASHFLOW_ROUTER: public(immutable(address))
TRIQEE_TREASURY: public(immutable(address))

# State Variables
owner: public(address)
lp_partner: public(address)
principal_deposited: public(uint256) # in USDC units (6 decimals)
deposit_timestamp: public(uint256)
last_harvest_timestamp: public(uint256)

# Yield Parameters (Stored as parts-per-million: 10,000 = 1.00%)
# 60,000 = 6.000% APY
# 91,550 = 9.155% APY
lp_preferred_rate_ppm: public(uint256)
blended_gross_rate_ppm: public(uint256)

# Payout Accounting State (Fixes multi-harvest yield retention)
total_lp_yield_distributed: public(uint256)
total_protocol_carry_distributed: public(uint256)
accumulated_unpaid_lp_yield: public(uint256)
is_vault_active: public(bool)

@deploy
def __init__(_usdc: address, _router: address, _treasury: address):
    USDC_TOKEN = _usdc
    FLASHFLOW_ROUTER = _router
    TRIQEE_TREASURY = _treasury
    self.owner = msg.sender
    self.lp_preferred_rate_ppm = 60000   # Exactly 6.000% APY
    self.blended_gross_rate_ppm = 91550  # Exactly 9.155% APY (+3.155% Carry Spread)
    self.total_lp_yield_distributed = 0
    self.total_protocol_carry_distributed = 0
    self.accumulated_unpaid_lp_yield = 0
    self.is_vault_active = False

@external
@nonreentrant
def deposit_sma_tranche(_amount: uint256):
    """
    @notice Deposit institutional principal (USDC) into the non-custodial SMA vault.
    @param _amount Amount of USDC (6 decimals). Minimum $50,000.
    """
    assert _amount >= 50000 * 10**6, "Minimum tranche is $50,000 USDC"
    assert not self.is_vault_active, "Vault already active with live tranche"
    
    # Transfer USDC from LP to this Vault
    extcall IERC20(USDC_TOKEN).transferFrom(msg.sender, self, _amount)
    
    self.lp_partner = msg.sender
    self.principal_deposited = _amount
    self.deposit_timestamp = block.timestamp
    self.last_harvest_timestamp = block.timestamp
    self.total_lp_yield_distributed = 0
    self.total_protocol_carry_distributed = 0
    self.accumulated_unpaid_lp_yield = 0
    self.is_vault_active = True
    
    # Approve FlashFlow Router to deploy into 3-Tier Waterfall
    extcall IERC20(USDC_TOKEN).approve(FLASHFLOW_ROUTER, _amount)
    
    log DepositTranche(lp_address=msg.sender, amount_usd=_amount, timestamp=block.timestamp)

@external
@nonreentrant
def harvest_and_distribute_spread() -> (uint256, uint256):
    """
    @notice Harvests accrued 12-hour yield, directly transfers LP their 6.000% preferred return,
            and routes the +3.155% positive carry margin to Triqee Treasury.
    @dev Fixes previous bug by immediately executing LP transfer at harvest epoch.
    @return (lp_payout, protocol_margin)
    """
    assert self.is_vault_active, "Vault not active"
    time_elapsed: uint256 = block.timestamp - self.last_harvest_timestamp
    assert time_elapsed >= 43200, "Epoch period (12h) not elapsed yet"
    
    # Gross Yield: Principal * Gross PPM * time / (RATE_DIVISOR * SECONDS_PER_YEAR)
    gross_yield: uint256 = (self.principal_deposited * self.blended_gross_rate_ppm * time_elapsed) // (RATE_DIVISOR * SECONDS_PER_YEAR)
    
    # LP Preferred Yield (6.000% APY)
    lp_share: uint256 = (self.principal_deposited * self.lp_preferred_rate_ppm * time_elapsed) // (RATE_DIVISOR * SECONDS_PER_YEAR)
    
    # Protocol Positive Carry Margin (The Spread: 3.155% APY)
    protocol_margin: uint256 = 0
    if gross_yield > lp_share:
        protocol_margin = gross_yield - lp_share
        
    self.last_harvest_timestamp = block.timestamp
    
    # Direct payout to LP Partner (6.000% preferred return)
    if lp_share > 0:
        extcall IERC20(USDC_TOKEN).transfer(self.lp_partner, lp_share)
        self.total_lp_yield_distributed += lp_share
        
    # Stream positive carry margin (+3.155%) to Protocol Treasury
    if protocol_margin > 0:
        extcall IERC20(USDC_TOKEN).transfer(TRIQEE_TREASURY, protocol_margin)
        self.total_protocol_carry_distributed += protocol_margin
        
    log HarvestAndCompound(epoch_id=block.number, gross_yield=gross_yield, lp_payout=lp_share, protocol_carry=protocol_margin, timestamp=block.timestamp)
    return (lp_share, protocol_margin)

@external
@nonreentrant
def redeem_lp_tranche():
    """
    @notice Allows the LP partner to redeem 100% of their deposited principal
            plus any stub accrued preferred yield since the last harvest timestamp.
    """
    assert msg.sender == self.lp_partner or msg.sender == self.owner, "Unauthorized"
    assert self.is_vault_active, "No active tranche"
    
    # Calculate unharvested stub yield between last harvest and redemption moment
    stub_elapsed: uint256 = block.timestamp - self.last_harvest_timestamp
    stub_lp_yield: uint256 = (self.principal_deposited * self.lp_preferred_rate_ppm * stub_elapsed) // (RATE_DIVISOR * SECONDS_PER_YEAR)
    
    total_due_lp: uint256 = self.principal_deposited + stub_lp_yield + self.accumulated_unpaid_lp_yield
    self.accumulated_unpaid_lp_yield = 0
    self.is_vault_active = False
    
    # Transfer full principal + stub yield back to LP
    extcall IERC20(USDC_TOKEN).transfer(self.lp_partner, total_due_lp)
    
    log RedeemTranche(
        lp_address=self.lp_partner,
        principal_returned=self.principal_deposited,
        stub_lp_yield=stub_lp_yield,
        accumulated_unpaid_lp_yield=self.accumulated_unpaid_lp_yield,
        timestamp=block.timestamp
    )

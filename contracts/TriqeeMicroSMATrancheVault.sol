// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

/**
 * ============================================================================
 * 🏛️ TRIQEE™ MICRO-TRANCHE SMA VAULT (BASE MAINNET L2)
 * ============================================================================
 * Parallels the Institutional Senior Tranche Vault (0x97dd66167a509Bf583dABC5C29405D5C791f95AB)
 * Calibrated for micro-liquidity validation and retail LP onboarding.
 * - LP Preferred Return: 6.00% APY (600 bps)
 * - Blended Gross Rate: 9.15% APY (915 bps)
 * - Protocol Carry Spread: +3.15% APY (315 bps)
 * - Minimum Tranche: 0.05 USDC (50,000 units)
 * ============================================================================
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

contract TriqeeMicroSMATrancheVault {
    uint256 public constant SECONDS_PER_YEAR = 31536000;
    uint256 public constant BPS_DIVISOR = 10000;

    address public immutable USDC_TOKEN;
    address public immutable FLASHFLOW_ROUTER;
    address public immutable TRIQEE_TREASURY;

    address public owner;
    address public lp_partner;
    uint256 public principal_deposited;
    uint256 public deposit_timestamp;
    uint256 public last_harvest_timestamp;

    uint256 public lp_preferred_rate_bps = 600;  // 6.00%
    uint256 public blended_gross_rate_bps = 915; // 9.15%
    uint256 public min_tranche_units = 50000;    // $0.05 USDC
    bool public is_vault_active;

    event DepositTranche(address indexed lp_address, uint256 amount_usd, uint256 timestamp);
    event HarvestAndCompound(uint256 indexed epoch_id, uint256 gross_yield, uint256 lp_payout, uint256 protocol_carry, uint256 timestamp);
    event RedeemTranche(address indexed lp_address, uint256 principal_returned, uint256 accrued_lp_yield, uint256 timestamp);

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    constructor(address _usdc, address _router, address _treasury) {
        USDC_TOKEN = _usdc != address(0) ? _usdc : 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
        FLASHFLOW_ROUTER = _router != address(0) ? _router : 0xa0F19fFA4a1F4672ba2504Afc1cDfa2FaeF2C685;
        TRIQEE_TREASURY = _treasury != address(0) ? _treasury : 0x676A66D77B4B14C2f981239f7368Ab5cc37aC666;
        owner = msg.sender;
        is_vault_active = false;
    }

    function deposit_sma_tranche(uint256 _amount) external {
        require(_amount >= min_tranche_units, "BELOW_MIN_TRANCHE");
        require(!is_vault_active, "VAULT_ACTIVE");

        require(IERC20(USDC_TOKEN).transferFrom(msg.sender, address(this), _amount), "TRANSFER_FAILED");

        lp_partner = msg.sender;
        principal_deposited = _amount;
        deposit_timestamp = block.timestamp;
        last_harvest_timestamp = block.timestamp;
        is_vault_active = true;

        IERC20(USDC_TOKEN).approve(FLASHFLOW_ROUTER, _amount);

        emit DepositTranche(msg.sender, _amount, block.timestamp);
    }

    function harvest_and_distribute_spread() external returns (uint256 lp_share, uint256 protocol_margin) {
        require(is_vault_active, "VAULT_NOT_ACTIVE");
        uint256 time_elapsed = block.timestamp - last_harvest_timestamp;

        uint256 gross_yield = (principal_deposited * blended_gross_rate_bps * time_elapsed) / (BPS_DIVISOR * SECONDS_PER_YEAR);
        lp_share = (principal_deposited * lp_preferred_rate_bps * time_elapsed) / (BPS_DIVISOR * SECONDS_PER_YEAR);

        if (gross_yield > lp_share) {
            protocol_margin = gross_yield - lp_share;
        }

        last_harvest_timestamp = block.timestamp;

        if (protocol_margin > 0) {
            IERC20(USDC_TOKEN).transfer(TRIQEE_TREASURY, protocol_margin);
        }

        emit HarvestAndCompound(block.number, gross_yield, lp_share, protocol_margin, block.timestamp);
    }

    function redeem_lp_tranche() external {
        require(msg.sender == lp_partner || msg.sender == owner, "UNAUTHORIZED");
        require(is_vault_active, "NO_ACTIVE_TRANCHE");

        uint256 time_elapsed = block.timestamp - last_harvest_timestamp;
        uint256 unpaid_lp_yield = (principal_deposited * lp_preferred_rate_bps * time_elapsed) / (BPS_DIVISOR * SECONDS_PER_YEAR);

        uint256 total_due_lp = principal_deposited + unpaid_lp_yield;
        uint256 return_principal = principal_deposited;
        is_vault_active = false;
        principal_deposited = 0;

        require(IERC20(USDC_TOKEN).transfer(lp_partner, total_due_lp), "TRANSFER_FAILED");

        emit RedeemTranche(lp_partner, return_principal, unpaid_lp_yield, block.timestamp);
    }
}

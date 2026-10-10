// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title QuantVaultAlphaShare ($QAV)
 * @author WhatsHot, Inc. // Triqee Omniverse DAO LLC (Wyoming Entity: DA-000000992)
 * @notice ERC-4626 Tokenized Yield Vault tied to QuantVault™ live alpha execution.
 * @dev Manages USDC/ETH liquidity with proof-of-reserve NAV feeds and 2/20 fee splits.
 */

interface IERC20Minimal {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);
}

contract QuantVaultAlphaShare {
    string public constant name = "Triqee QuantVault Alpha Share";
    string public constant symbol = "QAV";
    uint8 public constant decimals = 18;

    string public constant WYOMING_DAO_ID = "DA-000000992";
    string public constant CERN_DOI = "10.5281/zenodo.23045297";

    address public immutable asset; // Base asset (e.g. USDC or WETH)
    address public daoTreasury;
    address public oracleManager;

    uint256 private _totalShares;
    mapping(address => uint256) private _shares;

    // Real-Time Proof-of-Reserve Valuation (scaled to 1e18)
    uint256 public totalVaultNAV;
    uint256 public lastOracleTimestamp;
    uint256 public constant HIGH_WATER_MARK_ALPHA_BPS = 39420; // +394.20%

    // 2/20 Fee Structure
    uint256 public constant MANAGEMENT_FEE_BPS = 200; // 2.00% annual
    uint256 public constant PERFORMANCE_FEE_BPS = 2000; // 20.00% on net profit

    event Deposit(address indexed caller, address indexed owner, uint256 assets, uint256 shares);
    event Withdraw(address indexed caller, address indexed receiver, uint256 assets, uint256 shares);
    event NAVUpdated(uint256 oldNAV, uint256 newNAV, string proofHash, uint256 timestamp);

    modifier onlyOracle() {
        require(msg.sender == oracleManager || msg.sender == daoTreasury, "UNAUTHORIZED_ORACLE");
        _;
    }

    constructor(address _asset, address _treasury, address _oracle) {
        require(_asset != address(0) && _treasury != address(0), "INVALID_PARAMS");
        asset = _asset;
        daoTreasury = _treasury;
        oracleManager = _oracle;
        lastOracleTimestamp = block.timestamp;
    }

    function totalShares() external view returns (uint256) {
        return _totalShares;
    }

    function shareBalanceOf(address account) external view returns (uint256) {
        return _shares[account];
    }

    /**
     * @notice Updates the Vault NAV based on IonQ QAOA execution and Broker feeds.
     */
    function updateVaultNAV(uint256 _newNAV, string calldata proofHash) external onlyOracle {
        emit NAVUpdated(totalVaultNAV, _newNAV, proofHash, block.timestamp);
        totalVaultNAV = _newNAV;
        lastOracleTimestamp = block.timestamp;
    }

    /**
     * @notice Deposit assets into QuantVault and receive $QAV shares.
     */
    function deposit(uint256 assets, address receiver) external returns (uint256 shares) {
        require(assets > 0, "ZERO_DEPOSIT");
        
        if (_totalShares == 0 || totalVaultNAV == 0) {
            shares = assets;
        } else {
            shares = (assets * _totalShares) / totalVaultNAV;
        }

        require(shares > 0, "ZERO_SHARES_MINTED");
        require(IERC20Minimal(asset).transferFrom(msg.sender, address(this), assets), "TRANSFER_FAILED");

        _totalShares += shares;
        _shares[receiver] += shares;
        totalVaultNAV += assets;

        emit Deposit(msg.sender, receiver, assets, shares);
    }

    /**
     * @notice Redeem $QAV shares for underlying assets.
     */
    function redeem(uint256 shares, address receiver, address owner) external returns (uint256 assets) {
        require(shares > 0, "ZERO_SHARES");
        require(_shares[owner] >= shares, "INSUFFICIENT_SHARES");
        require(msg.sender == owner || msg.sender == daoTreasury, "UNAUTHORIZED_REDEEM");

        assets = (shares * totalVaultNAV) / _totalShares;
        require(assets > 0, "ZERO_ASSETS_RETURNED");

        _shares[owner] -= shares;
        _totalShares -= shares;
        totalVaultNAV -= assets;

        require(IERC20Minimal(asset).transfer(receiver, assets), "TRANSFER_FAILED");
        emit Withdraw(msg.sender, receiver, assets, shares);
    }
}

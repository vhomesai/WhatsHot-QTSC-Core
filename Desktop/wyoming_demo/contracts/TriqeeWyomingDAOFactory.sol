// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./TriqeeComputeGasToken.sol";
import "./QuantVaultAlphaShare.sol";
import "./TriqeeWyomingBondingCurve.sol";

/**
 * @title TriqeeWyomingDAOFactory
 * @author WhatsHot, Inc. // Triqee Omniverse DAO LLC (Wyoming Entity: DA-000000992)
 * @notice Factory contract for launching Wyoming-compliant utility tokens, bonding curves, and yield vaults on Base L2.
 * @dev Enforces 1.5% protocol origination fees and links all deployments to DA-000000992 metadata.
 */

contract TriqeeWyomingDAOFactory {
    string public constant FACTORY_NAME = "Triqee Wyoming DAO Token Factory & Bonding Launchpad";
    string public constant WYOMING_ENTITY_ID = "DA-000000992";
    string public constant STATUTORY_FRAMEWORK = "Wyoming W.S. 17-31 & W.S. 34-29-106";
    string public constant CERN_ZENODO_DOI = "10.5281/zenodo.23045297";

    address public daoTreasury;
    uint256 public constant PROTOCOL_ORIGINATION_FEE_BPS = 150; // 1.50%

    // Dedicated Bonding Curve Engine
    TriqeeWyomingBondingCurve public bondingCurveEngine;

    // Registry of created contracts
    address[] public deployedTokens;
    address[] public deployedVaults;

    event TokenCreated(
        address indexed tokenAddress,
        string name,
        string symbol,
        uint256 initialSupply,
        address indexed creator,
        uint256 timestamp
    );

    event TokenBondingCurveInitialized(
        address indexed tokenAddress,
        address indexed curveEngine,
        address indexed creator,
        uint256 timestamp
    );

    event VaultCreated(
        address indexed vaultAddress,
        address indexed underlyingAsset,
        address indexed creator,
        uint256 timestamp
    );

    modifier onlyTreasury() {
        require(msg.sender == daoTreasury, "UNAUTHORIZED_TREASURY_CALL");
        _;
    }

    constructor(address _treasury) {
        require(_treasury != address(0), "INVALID_TREASURY");
        daoTreasury = _treasury;
        bondingCurveEngine = new TriqeeWyomingBondingCurve(_treasury);
    }

    /**
     * @notice Deploy a new Wyoming-compliant Compute Gas Utility Token.
     */
    function createComputeGasToken(
        uint256 initialSupply
    ) external returns (address) {
        TriqeeComputeGasToken token = new TriqeeComputeGasToken(daoTreasury, initialSupply);
        deployedTokens.push(address(token));

        emit TokenCreated(
            address(token),
            "Triqee Quantum Compute Gas",
            "TQ",
            initialSupply,
            msg.sender,
            block.timestamp
        );
        return address(token);
    }

    /**
     * @notice Deploy a new utility token paired with an automated bonding curve on Base L2.
     */
    function createBondingCurveToken(
        string memory name,
        string memory symbol
    ) external returns (address tokenAddress, address curveEngineAddress) {
        uint256 initialSupply = 1_000_000_000 * 10**18; // 1 Billion standard supply
        TriqeeComputeGasToken token = new TriqeeComputeGasToken(address(bondingCurveEngine), initialSupply);
        
        tokenAddress = address(token);
        curveEngineAddress = address(bondingCurveEngine);
        deployedTokens.push(tokenAddress);

        bondingCurveEngine.initializeCurve(tokenAddress, msg.sender);

        emit TokenCreated(tokenAddress, name, symbol, initialSupply, msg.sender, block.timestamp);
        emit TokenBondingCurveInitialized(tokenAddress, curveEngineAddress, msg.sender, block.timestamp);

        return (tokenAddress, curveEngineAddress);
    }

    /**
     * @notice Deploy a new QuantVault Alpha ERC-4626 Yield Vault.
     */
    function createQuantVault(
        address underlyingAsset,
        address oracleManager
    ) external returns (address) {
        QuantVaultAlphaShare vault = new QuantVaultAlphaShare(
            underlyingAsset,
            daoTreasury,
            oracleManager
        );
        deployedVaults.push(address(vault));

        emit VaultCreated(address(vault), underlyingAsset, msg.sender, block.timestamp);
        return address(vault);
    }

    function getDeployedTokensCount() external view returns (uint256) {
        return deployedTokens.length;
    }

    function getDeployedVaultsCount() external view returns (uint256) {
        return deployedVaults.length;
    }

    function setTreasury(address _newTreasury) external onlyTreasury {
        require(_newTreasury != address(0), "INVALID_ADDRESS");
        daoTreasury = _newTreasury;
    }
}

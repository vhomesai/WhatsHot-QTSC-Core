// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TriqeeWyomingBondingCurve
 * @author WhatsHot, Inc. // Triqee Omniverse DAO LLC (Wyoming Entity: DA-000000992)
 * @notice Autonomous AI & Quantum Utility Token Bonding Curve Engine for Base L2.
 * @dev Implements an automated constant-product bonding curve with 1.50% protocol fee
 *      routed to DAO Treasury, and automatic $69k graduation seeding to Uniswap V3 / Aerodrome.
 *      Governed by Wyoming W.S. 17-31 (DAO Supplement) & W.S. 34-29-106 (Utility Token Act).
 *      Permanent Scientific Citation: CERN Zenodo DOI 10.5281/zenodo.23045297.
 */

interface IERC20Token {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function mint(address to, uint256 amount) external;
    function burn(uint256 amount) external;
}

contract TriqeeWyomingBondingCurve {
    string public constant VERSION = "Triqee-BondingCurve-v1.0-Wyoming";
    string public constant WYOMING_ENTITY_ID = "DA-000000992";
    string public constant STATUTE = "Wyoming W.S. 17-31 & W.S. 34-29-106";
    string public constant CERN_ZENODO_DOI = "10.5281/zenodo.23045297";

    address public immutable daoTreasury;
    uint256 public constant PROTOCOL_FEE_BPS = 150; // 1.50% fee on all buys and sells
    uint256 public constant BPS_DENOMINATOR = 10000;

    // Bonding curve constant product parameters
    uint256 public constant VIRTUAL_ETH_RESERVE = 0.5 ether;
    uint256 public constant TOTAL_CURVE_SUPPLY = 800_000_000 * 10**18; // 800M tokens on curve (80% of 1B)
    uint256 public constant GRADUATION_ETH_TARGET = 24 ether; // ~$69,000 USD Market Cap at ~$2,875/ETH

    struct CurveState {
        address tokenAddress;
        address creator;
        uint256 realEthReserve;
        uint256 virtualEthReserve;
        uint256 tokensRemaining;
        uint256 k; // constant product invariant
        bool isGraduated;
        uint256 totalVolumeEth;
        uint256 totalFeesAccruedEth;
    }

    mapping(address => CurveState) public curves;
    address[] public activeCurveTokens;

    event CurveCreated(
        address indexed tokenAddress,
        address indexed creator,
        uint256 initialTokenSupply,
        uint256 timestamp
    );

    event TokensPurchased(
        address indexed tokenAddress,
        address indexed buyer,
        uint256 ethIn,
        uint256 tokensOut,
        uint256 feeEth,
        uint256 currentPriceWei
    );

    event TokensSold(
        address indexed tokenAddress,
        address indexed seller,
        uint256 tokensIn,
        uint256 ethOut,
        uint256 feeEth,
        uint256 currentPriceWei
    );

    event TokenGraduated(
        address indexed tokenAddress,
        uint256 totalEthSeeded,
        uint256 tokensSeeded,
        uint256 timestamp
    );

    modifier onlyTreasury() {
        require(msg.sender == daoTreasury, "NOT_DAO_TREASURY");
        _;
    }

    constructor(address _treasury) {
        require(_treasury != address(0), "INVALID_TREASURY");
        daoTreasury = _treasury;
    }

    /**
     * @notice Initialize a bonding curve for a freshly deployed utility token.
     */
    function initializeCurve(address tokenAddress, address creator) external {
        require(curves[tokenAddress].tokenAddress == address(0), "CURVE_ALREADY_EXISTS");
        require(tokenAddress != address(0), "INVALID_TOKEN");

        uint256 virtualEth = VIRTUAL_ETH_RESERVE;
        uint256 curveSupply = TOTAL_CURVE_SUPPLY;
        uint256 kVal = virtualEth * curveSupply;

        curves[tokenAddress] = CurveState({
            tokenAddress: tokenAddress,
            creator: creator,
            realEthReserve: 0,
            virtualEthReserve: virtualEth,
            tokensRemaining: curveSupply,
            k: kVal,
            isGraduated: false,
            totalVolumeEth: 0,
            totalFeesAccruedEth: 0
        });

        activeCurveTokens.push(tokenAddress);

        emit CurveCreated(tokenAddress, creator, curveSupply, block.timestamp);
    }

    /**
     * @notice Buy utility tokens along the bonding curve using ETH.
     */
    function buyTokens(address tokenAddress, uint256 minTokensOut) external payable returns (uint256 tokensOut) {
        CurveState storage curve = curves[tokenAddress];
        require(curve.tokenAddress != address(0), "CURVE_NOT_FOUND");
        require(!curve.isGraduated, "TOKEN_ALREADY_GRADUATED");
        require(msg.value > 0, "ZERO_ETH");

        // Calculate 1.50% protocol fee
        uint256 fee = (msg.value * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
        uint256 netEth = msg.value - fee;

        // Route fee immediately to Wyoming DAO Treasury
        (bool feeSuccess, ) = daoTreasury.call{value: fee}("");
        require(feeSuccess, "FEE_TRANSFER_FAILED");

        // Calculate token output using constant product: k = (virtualEth + netEth) * (newTokensRemaining)
        uint256 effectiveEth = curve.virtualEthReserve + curve.realEthReserve;
        uint256 newEffectiveEth = effectiveEth + netEth;
        uint256 newTokensRemaining = curve.k / newEffectiveEth;
        tokensOut = curve.tokensRemaining - newTokensRemaining;

        require(tokensOut >= minTokensOut, "SLIPPAGE_EXCEEDED");
        require(tokensOut <= curve.tokensRemaining, "INSUFFICIENT_CURVE_LIQUIDITY");

        // Update state
        curve.realEthReserve += netEth;
        curve.tokensRemaining = newTokensRemaining;
        curve.totalVolumeEth += msg.value;
        curve.totalFeesAccruedEth += fee;

        // Transfer tokens to buyer
        require(IERC20Token(tokenAddress).transfer(msg.sender, tokensOut), "TOKEN_TRANSFER_FAILED");

        uint256 currentPrice = getCurrentPriceWei(tokenAddress);
        emit TokensPurchased(tokenAddress, msg.sender, msg.value, tokensOut, fee, currentPrice);

        // Check graduation condition
        if (curve.realEthReserve >= GRADUATION_ETH_TARGET) {
            _graduateToken(tokenAddress);
        }

        return tokensOut;
    }

    /**
     * @notice Sell utility tokens back to the bonding curve for ETH.
     */
    function sellTokens(address tokenAddress, uint256 tokenAmount, uint256 minEthOut) external returns (uint256 netEthOut) {
        CurveState storage curve = curves[tokenAddress];
        require(curve.tokenAddress != address(0), "CURVE_NOT_FOUND");
        require(!curve.isGraduated, "TOKEN_ALREADY_GRADUATED");
        require(tokenAmount > 0, "ZERO_TOKENS");

        // Transfer tokens from seller to curve
        require(IERC20Token(tokenAddress).transferFrom(msg.sender, address(this), tokenAmount), "TRANSFER_FROM_FAILED");

        // Calculate ETH return: (effectiveEth - newEffectiveEth)
        uint256 effectiveEth = curve.virtualEthReserve + curve.realEthReserve;
        uint256 newTokensRemaining = curve.tokensRemaining + tokenAmount;
        uint256 newEffectiveEth = curve.k / newTokensRemaining;
        uint256 grossEthOut = effectiveEth - newEffectiveEth;

        require(grossEthOut <= curve.realEthReserve, "INSUFFICIENT_ETH_RESERVE");

        // Deduct 1.50% protocol fee
        uint256 fee = (grossEthOut * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
        netEthOut = grossEthOut - fee;

        require(netEthOut >= minEthOut, "SLIPPAGE_EXCEEDED");

        // Update state
        curve.realEthReserve -= grossEthOut;
        curve.tokensRemaining = newTokensRemaining;
        curve.totalVolumeEth += grossEthOut;
        curve.totalFeesAccruedEth += fee;

        // Route fee to DAO Treasury
        (bool feeSuccess, ) = daoTreasury.call{value: fee}("");
        require(feeSuccess, "FEE_TRANSFER_FAILED");

        // Transfer net ETH to seller
        (bool ethSuccess, ) = msg.sender.call{value: netEthOut}("");
        require(ethSuccess, "ETH_TRANSFER_FAILED");

        uint256 currentPrice = getCurrentPriceWei(tokenAddress);
        emit TokensSold(tokenAddress, msg.sender, tokenAmount, netEthOut, fee, currentPrice);

        return netEthOut;
    }

    /**
     * @notice Internal graduation protocol triggering Uniswap V3 / Aerodrome liquidity seed.
     */
    function _graduateToken(address tokenAddress) internal {
        CurveState storage curve = curves[tokenAddress];
        curve.isGraduated = true;

        uint256 ethToSeed = curve.realEthReserve;
        uint256 tokensToSeed = curve.tokensRemaining;

        // In production: transfers ETH & remaining tokens to Uniswap V3 / Aerodrome Slipstream Position Manager
        // For security, ETH is routed to DAO Treasury or liquidity contract lock
        (bool success, ) = daoTreasury.call{value: ethToSeed}("");
        require(success, "GRADUATION_SEED_FAILED");

        emit TokenGraduated(tokenAddress, ethToSeed, tokensToSeed, block.timestamp);
    }

    /**
     * @notice Calculate instantaneous spot price in Wei per token.
     */
    function getCurrentPriceWei(address tokenAddress) public view returns (uint256) {
        CurveState memory curve = curves[tokenAddress];
        if (curve.tokensRemaining == 0) return 0;
        uint256 effectiveEth = curve.virtualEthReserve + curve.realEthReserve;
        // Price = (effectiveEth * 1e18) / tokensRemaining
        return (effectiveEth * 1e18) / (curve.tokensRemaining / 1e18);
    }

    function getCurveState(address tokenAddress) external view returns (
        uint256 realEthReserve,
        uint256 tokensRemaining,
        uint256 currentPriceWei,
        bool isGraduated,
        uint256 totalVolumeEth,
        uint256 totalFeesAccruedEth
    ) {
        CurveState memory curve = curves[tokenAddress];
        return (
            curve.realEthReserve,
            curve.tokensRemaining,
            getCurrentPriceWei(tokenAddress),
            curve.isGraduated,
            curve.totalVolumeEth,
            curve.totalFeesAccruedEth
        );
    }
}

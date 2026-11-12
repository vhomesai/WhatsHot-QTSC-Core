// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * ============================================================================
 * TRIQEE™ WYOMING DAO TOKEN FACTORY & CONSTANT-PRODUCT BONDING ENGINE
 * ============================================================================
 * Authority: Wyoming Statutory Title WY DA-000000992 | W.S. § 17-31 & W.S. § 34-29-106
 * Beneficiary Multi-Sig: 0x676A66D77B4B14C2f981239f7368Ab5cc37aC666
 * Network: Base L2 Mainnet (Chain ID: 8453)
 * Scientific Anchor: DOI 10.5281/zenodo.23045297
 *
 * Architecture:
 *   1. TriqeeConsumptiveToken: ERC-20 utility token with statutory burnForCompute().
 *   2. TriqeeBondingCurve: Constant-product virtual reserve AMM (k = x * y).
 *      - Virtual ETH Reserve: 0.50 ETH
 *      - Curve Allocation: 800,000,000 tokens (80% of 1B supply)
 *      - Graduation Threshold: 24.00 ETH (~$69,000 USD)
 *      - Protocol Fee: 1.50% hardcoded to Multi-Sig Treasury
 *   3. TriqeeTokenFactory: Permissionless deployment of Wyoming utility tokens.
 * ============================================================================
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

abstract contract ReentrancyGuard {
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status;

    error ReentrancyGuardReentrantCall();

    constructor() {
        _status = _NOT_ENTERED;
    }

    modifier nonReentrant() {
        if (_status == _ENTERED) revert ReentrancyGuardReentrantCall();
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}

/**
 * @title TriqeeConsumptiveToken
 * @dev Compliant Wyoming Utility Token under W.S. 34-29-106 featuring burnForCompute()
 */
contract TriqeeConsumptiveToken is IERC20 {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public override totalSupply;

    address public immutable factory;
    address public immutable bondingCurve;
    address public constant MULTISIG_TREASURY = 0x676A66D77B4B14C2f981239f7368Ab5cc37aC666;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    event ConsumptiveBurn(address indexed burner, uint256 amount, string targetHardware, uint256 timestamp);

    error Unauthorized();
    error InsufficientBalance();
    error InsufficientAllowance();

    constructor(
        string memory _name,
        string memory _symbol,
        uint256 _initialSupply,
        address _bondingCurve
    ) {
        name = _name;
        symbol = _symbol;
        factory = msg.sender;
        bondingCurve = _bondingCurve;
        totalSupply = _initialSupply;

        // 80% to bonding curve, 20% to DAO Multi-Sig Treasury for liquidity & development
        uint256 curveAmount = (_initialSupply * 80) / 100;
        uint256 treasuryAmount = _initialSupply - curveAmount;

        _balances[_bondingCurve] = curveAmount;
        emit Transfer(address(0), _bondingCurve, curveAmount);

        _balances[MULTISIG_TREASURY] = treasuryAmount;
        emit Transfer(address(0), MULTISIG_TREASURY, treasuryAmount);
    }

    function balanceOf(address account) public view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address recipient, uint256 amount) public override returns (bool) {
        _transfer(msg.sender, recipient, amount);
        return true;
    }

    function allowance(address owner, address spender) public view override returns (uint256) {
        return _allowances[owner][spender];
    }

    function approve(address spender, uint256 amount) public override returns (bool) {
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    function transferFrom(address sender, address recipient, uint256 amount) public override returns (bool) {
        uint256 currentAllowance = _allowances[sender][msg.sender];
        if (currentAllowance < amount) revert InsufficientAllowance();
        unchecked {
            _allowances[sender][msg.sender] = currentAllowance - amount;
        }
        _transfer(sender, recipient, amount);
        return true;
    }

    function _transfer(address sender, address recipient, uint256 amount) internal {
        if (recipient == address(0)) revert Unauthorized();
        uint256 senderBalance = _balances[sender];
        if (senderBalance < amount) revert InsufficientBalance();
        unchecked {
            _balances[sender] = senderBalance - amount;
            _balances[recipient] += amount;
        }
        emit Transfer(sender, recipient, amount);
    }

    /**
     * @notice Statutory burn for physical AI / Quantum compute time under Wyoming W.S. 34-29-106
     * @param amount Tokens to burn
     * @param targetHardware Hardware system identifier (e.g. "IBM_HERON_156Q", "GEMINI_ARGON")
     */
    function burnForCompute(uint256 amount, string calldata targetHardware) external {
        uint256 senderBalance = _balances[msg.sender];
        if (senderBalance < amount) revert InsufficientBalance();
        unchecked {
            _balances[msg.sender] = senderBalance - amount;
            totalSupply -= amount;
        }
        emit Transfer(msg.sender, address(0), amount);
        emit ConsumptiveBurn(msg.sender, amount, targetHardware, block.timestamp);
    }
}

/**
 * @title TriqeeBondingCurve
 * @dev Constant-Product Virtual Reserve Bonding AMM: k = (x_virt + x_real) * y
 */
contract TriqeeBondingCurve is ReentrancyGuard {
    address public constant MULTISIG_TREASURY = 0x676A66D77B4B14C2f981239f7368Ab5cc37aC666;
    uint256 public constant VIRTUAL_ETH_RESERVE = 0.5 ether;
    uint256 public constant GRADUATION_THRESHOLD_ETH = 24.0 ether;
    uint256 public constant PROTOCOL_FEE_BPS = 150; // 1.50%
    uint256 public constant BPS_DENOMINATOR = 10000;

    TriqeeConsumptiveToken public token;
    uint256 public realEthReserve;
    uint256 public kInvariant;
    bool public isGraduated;
    uint256 public totalProtocolFeesAccrued;

    event TokenPurchased(address indexed buyer, uint256 ethIn, uint256 tokensOut, uint256 feeEth);
    event TokenSold(address indexed seller, uint256 tokensIn, uint256 ethOut, uint256 feeEth);
    event CurveGraduated(uint256 totalEthPooled, uint256 timestamp);

    error AlreadyGraduated();
    error NotGraduated();
    error ZeroInput();
    error SlippageExceeded();
    error TransferFailed();

    constructor() {}

    function initializeToken(address _tokenAddress, uint256 _initialCurveTokens) external {
        require(address(token) == address(0), "Already initialized");
        token = TriqeeConsumptiveToken(_tokenAddress);
        kInvariant = VIRTUAL_ETH_RESERVE * _initialCurveTokens;
    }

    /**
     * @notice Calculate tokens out for an incoming ETH amount
     */
    function getTokensOutForEth(uint256 ethIn) public view returns (uint256 tokensOut, uint256 feeEth) {
        if (ethIn == 0) return (0, 0);
        feeEth = (ethIn * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
        uint256 netEth = ethIn - feeEth;

        uint256 currentEffectiveEth = VIRTUAL_ETH_RESERVE + realEthReserve;
        uint256 newEffectiveEth = currentEffectiveEth + netEth;
        uint256 currentTokens = token.balanceOf(address(this));
        uint256 newTokens = kInvariant / newEffectiveEth;

        if (currentTokens > newTokens) {
            tokensOut = currentTokens - newTokens;
        }
    }

    /**
     * @notice Calculate ETH out for an incoming token amount
     */
    function getEthOutForTokens(uint256 tokensIn) public view returns (uint256 ethOut, uint256 feeEth) {
        if (tokensIn == 0) return (0, 0);
        uint256 currentTokens = token.balanceOf(address(this));
        uint256 newTokens = currentTokens + tokensIn;
        uint256 currentEffectiveEth = VIRTUAL_ETH_RESERVE + realEthReserve;
        uint256 newEffectiveEth = kInvariant / newTokens;

        if (currentEffectiveEth > newEffectiveEth) {
            uint256 grossEth = currentEffectiveEth - newEffectiveEth;
            feeEth = (grossEth * PROTOCOL_FEE_BPS) / BPS_DENOMINATOR;
            ethOut = grossEth - feeEth;
        }
    }

    /**
     * @notice Buy tokens along the constant-product bonding curve
     */
    function buyTokens(uint256 minTokensOut) external payable nonReentrant {
        if (isGraduated) revert AlreadyGraduated();
        if (msg.value == 0) revert ZeroInput();

        (uint256 tokensOut, uint256 feeEth) = getTokensOutForEth(msg.value);
        if (tokensOut < minTokensOut) revert SlippageExceeded();

        uint256 netEth = msg.value - feeEth;
        realEthReserve += netEth;
        totalProtocolFeesAccrued += feeEth;

        // Forward protocol fee directly to Multi-Sig Treasury
        (bool feeSuccess, ) = MULTISIG_TREASURY.call{value: feeEth}("");
        if (!feeSuccess) revert TransferFailed();

        // Transfer tokens to buyer
        bool tokenSuccess = token.transfer(msg.sender, tokensOut);
        if (!tokenSuccess) revert TransferFailed();

        emit TokenPurchased(msg.sender, msg.value, tokensOut, feeEth);

        // Check graduation event
        if (realEthReserve >= GRADUATION_THRESHOLD_ETH) {
            isGraduated = true;
            emit CurveGraduated(realEthReserve, block.timestamp);
        }
    }

    /**
     * @notice Sell tokens back to the bonding curve for ETH
     */
    function sellTokens(uint256 tokensIn, uint256 minEthOut) external nonReentrant {
        if (isGraduated) revert AlreadyGraduated();
        if (tokensIn == 0) revert ZeroInput();

        (uint256 ethOut, uint256 feeEth) = getEthOutForTokens(tokensIn);
        if (ethOut < minEthOut) revert SlippageExceeded();
        if (ethOut > realEthReserve) revert TransferFailed();

        realEthReserve -= (ethOut + feeEth);
        totalProtocolFeesAccrued += feeEth;

        // Pull tokens from seller
        bool pullSuccess = token.transferFrom(msg.sender, address(this), tokensIn);
        if (!pullSuccess) revert TransferFailed();

        // Forward protocol fee to Multi-Sig Treasury
        (bool feeSuccess, ) = MULTISIG_TREASURY.call{value: feeEth}("");
        if (!feeSuccess) revert TransferFailed();

        // Transfer net ETH to seller
        (bool ethSuccess, ) = msg.sender.call{value: ethOut}("");
        if (!ethSuccess) revert TransferFailed();

        emit TokenSold(msg.sender, tokensIn, ethOut, feeEth);
    }
}

/**
 * @title TriqeeWyomingTokenFactory
 * @dev Permissionless deployer for Wyoming statutory utility tokens & bonding curves
 */
contract TriqeeWyomingTokenFactory {
    address public constant MULTISIG_TREASURY = 0x676A66D77B4B14C2f981239f7368Ab5cc37aC666;
    uint256 public constant INITIAL_TOKEN_SUPPLY = 1_000_000_000 ether; // 1 Billion tokens

    struct DeployedTokenInfo {
        address tokenAddress;
        address bondingCurveAddress;
        string name;
        string symbol;
        uint256 deployedTimestamp;
    }

    DeployedTokenInfo[] public allTokens;
    mapping(address => address) public tokenToCurve;

    event TokenDeployed(
        address indexed tokenAddress,
        address indexed bondingCurveAddress,
        string name,
        string symbol,
        uint256 timestamp
    );

    function totalDeployedTokens() external view returns (uint256) {
        return allTokens.length;
    }

    function createWyomingToken(string memory name, string memory symbol) external returns (address, address) {
        require(bytes(name).length > 0 && bytes(symbol).length > 0, "Invalid params");

        // 1. Deploy Bonding Curve
        TriqeeBondingCurve curve = new TriqeeBondingCurve();

        // 2. Deploy Consumptive Token with Curve as beneficiary of 80% supply
        TriqeeConsumptiveToken newToken = new TriqeeConsumptiveToken(
            name,
            symbol,
            INITIAL_TOKEN_SUPPLY,
            address(curve)
        );

        // 3. Initialize Curve Invariant
        curve.initializeToken(address(newToken), (INITIAL_TOKEN_SUPPLY * 80) / 100);

        tokenToCurve[address(newToken)] = address(curve);

        allTokens.push(DeployedTokenInfo({
            tokenAddress: address(newToken),
            bondingCurveAddress: address(curve),
            name: name,
            symbol: symbol,
            deployedTimestamp: block.timestamp
        }));

        emit TokenDeployed(address(newToken), address(curve), name, symbol, block.timestamp);

        return (address(newToken), address(curve));
    }
}

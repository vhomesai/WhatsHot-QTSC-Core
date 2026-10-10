// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title TriqeeComputeGasToken ($TQ)
 * @author WhatsHot, Inc. // Triqee Omniverse DAO LLC (Wyoming Entity: DA-000000992)
 * @notice Consumptive utility token compliant with Wyoming Utility Token Act (W.S. 34-29-106).
 * @dev Burnable on execution for multi-vendor QPU shot-time and Gemini 4 Argon reasoning tokens.
 * Permanent Research Citation: CERN Zenodo Record 23045297 (DOI: 10.5281/zenodo.23045297).
 */

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 value) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 value) external returns (bool);
    function transferFrom(address from, address to, uint256 value) external returns (bool);

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}

contract TriqeeComputeGasToken is IERC20 {
    string public constant name = "Triqee Quantum Compute Gas";
    string public constant symbol = "TQ";
    uint8 public constant decimals = 18;
    
    // Wyoming Legal & Academic Metadata
    string public constant WYOMING_ENTITY_ID = "DA-000000992";
    string public constant JURISDICTION = "Wyoming, USA (W.S. 17-31 & W.S. 34-29-106)";
    string public constant CERN_ZENODO_DOI = "10.5281/zenodo.23045297";

    uint256 private _totalSupply;
    address public daoTreasury;
    address public factoryAdmin;

    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    event ComputeGasBurned(
        address indexed caller,
        uint256 amountBurned,
        string targetHardware,
        string indexed executionTicketId,
        uint256 timestamp
    );

    modifier onlyAdmin() {
        require(msg.sender == factoryAdmin || msg.sender == daoTreasury, "UNAUTHORIZED_DAO_CALLER");
        _;
    }

    constructor(address _treasury, uint256 _initialSupply) {
        require(_treasury != address(0), "INVALID_TREASURY_ADDRESS");
        factoryAdmin = msg.sender;
        daoTreasury = _treasury;
        
        _mint(_treasury, _initialSupply * 10**decimals);
    }

    function totalSupply() public view override returns (uint256) {
        return _totalSupply;
    }

    function balanceOf(address account) public view override returns (uint256) {
        return _balances[account];
    }

    function transfer(address to, uint256 value) public override returns (bool) {
        _transfer(msg.sender, to, value);
        return true;
    }

    function allowance(address owner, address spender) public view override returns (uint256) {
        return _allowances[owner][spender];
    }

    function approve(address spender, uint256 value) public override returns (bool) {
        _approve(msg.sender, spender, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) public override returns (bool) {
        _spendAllowance(from, msg.sender, value);
        _transfer(from, to, value);
        return true;
    }

    /**
     * @notice Consumptive execution method: burns $TQ in exchange for sovereign compute authorization.
     * @param amount The quantity of $TQ tokens to burn.
     * @param targetHardware Target QPU/AI backend (e.g., "IBM_HERON_156Q", "IONQ_FORTE", "GEMINI_4_ARGON").
     * @param executionTicketId Cryptographic identifier matching Sovereign Appliance ticket.
     */
    function burnForCompute(
        uint256 amount,
        string calldata targetHardware,
        string calldata executionTicketId
    ) external {
        require(amount > 0, "BURN_AMOUNT_ZERO");
        require(_balances[msg.sender] >= amount, "INSUFFICIENT_TQ_BALANCE");

        _burn(msg.sender, amount);
        emit ComputeGasBurned(msg.sender, amount, targetHardware, executionTicketId, block.timestamp);
    }

    function mint(address to, uint256 amount) external onlyAdmin {
        _mint(to, amount);
    }

    function _transfer(address from, address to, uint256 value) internal {
        require(from != address(0), "TRANSFER_FROM_ZERO");
        require(to != address(0), "TRANSFER_TO_ZERO");
        require(_balances[from] >= value, "EXCEEDS_BALANCE");

        _balances[from] -= value;
        _balances[to] += value;
        emit Transfer(from, to, value);
    }

    function _mint(address account, uint256 value) internal {
        require(account != address(0), "MINT_TO_ZERO");
        _totalSupply += value;
        _balances[account] += value;
        emit Transfer(address(0), account, value);
    }

    function _burn(address account, uint256 value) internal {
        require(account != address(0), "BURN_FROM_ZERO");
        require(_balances[account] >= value, "BURN_EXCEEDS_BALANCE");
        _balances[account] -= value;
        _totalSupply -= value;
        emit Transfer(account, address(0), value);
    }

    function _approve(address owner, address spender, uint256 value) internal {
        require(owner != address(0), "APPROVE_FROM_ZERO");
        require(spender != address(0), "APPROVE_TO_ZERO");
        _allowances[owner][spender] = value;
        emit Approval(owner, spender, value);
    }

    function _spendAllowance(address owner, address spender, uint256 value) internal {
        uint256 currentAllowance = allowance(owner, spender);
        if (currentAllowance != type(uint256).max) {
            require(currentAllowance >= value, "INSUFFICIENT_ALLOWANCE");
            _approve(owner, spender, currentAllowance - value);
        }
    }
}

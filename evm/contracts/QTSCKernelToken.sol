// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Burnable} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

contract QTSCKernelToken is ERC20, ERC20Burnable, Ownable, Pausable {
    uint256 public constant INITIAL_SUPPLY = 100_000_000 ether;
    uint256 public constant ESCROW_BASIS_POINTS = 2_500;
    uint256 public constant BASIS_POINTS_DENOMINATOR = 10_000;

    address public escrowTreasury;
    address public operationalTreasury;

    error InvalidAddress();
    error InvalidAmount();
    error InsufficientHarvestBalance(uint256 available, uint256 requested);

    event TreasuriesUpdated(
        address indexed previousEscrowTreasury,
        address indexed newEscrowTreasury,
        address previousOperationalTreasury,
        address newOperationalTreasury
    );
    event HarvestSweepExecuted(
        uint256 amount,
        uint256 escrowShare,
        uint256 operationalShare
    );

    constructor(
        address initialOwner,
        address initialEscrowTreasury,
        address initialOperationalTreasury
    ) ERC20("QTSC Ternary Kernel Token", "QTSC") Ownable(initialOwner) {
        _validateAddress(initialEscrowTreasury);
        _validateAddress(initialOperationalTreasury);

        escrowTreasury = initialEscrowTreasury;
        operationalTreasury = initialOperationalTreasury;
        _mint(initialOwner, INITIAL_SUPPLY);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function setTreasuries(
        address newEscrowTreasury,
        address newOperationalTreasury
    ) external onlyOwner {
        _validateAddress(newEscrowTreasury);
        _validateAddress(newOperationalTreasury);

        emit TreasuriesUpdated(
            escrowTreasury,
            newEscrowTreasury,
            operationalTreasury,
            newOperationalTreasury
        );
        escrowTreasury = newEscrowTreasury;
        operationalTreasury = newOperationalTreasury;
    }

    function executeHarvestSweep(uint256 amount) external onlyOwner whenNotPaused {
        if (amount == 0) {
            revert InvalidAmount();
        }

        uint256 available = balanceOf(address(this));
        if (amount > available) {
            revert InsufficientHarvestBalance(available, amount);
        }

        uint256 escrowShare = (amount * ESCROW_BASIS_POINTS) /
            BASIS_POINTS_DENOMINATOR;
        uint256 operationalShare = amount - escrowShare;

        _transfer(address(this), escrowTreasury, escrowShare);
        _transfer(address(this), operationalTreasury, operationalShare);

        emit HarvestSweepExecuted(amount, escrowShare, operationalShare);
    }

    function _update(
        address from,
        address to,
        uint256 value
    ) internal override whenNotPaused {
        super._update(from, to, value);
    }

    function _validateAddress(address account) private pure {
        if (account == address(0)) {
            revert InvalidAddress();
        }
    }
}

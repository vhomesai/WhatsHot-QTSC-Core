// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./TriqeeComputeGasToken.sol";

/**
 * @title TriqeeAirdropMerkle
 * @author WhatsHot, Inc. // Triqee Omniverse DAO LLC (Wyoming Entity: DA-000000992)
 * @notice Gas-optimized cryptographic Merkle Distributor for the Quantum Genesis Airdrop on Base L2.
 * @dev Distributes $TQ Compute Gas tokens to verified developers, quants, and academic researchers.
 * Statutory Authority: Wyoming Utility Token Act (W.S. 34-29-106).
 * Permanent Citation: CERN Zenodo Record 23045297 (DOI: 10.5281/zenodo.23045297).
 */

contract TriqeeAirdropMerkle {
    string public constant CAMPAIGN_NAME = "Triqee Quantum Genesis Developer Airdrop (Season 1)";
    string public constant WYOMING_ENTITY_ID = "DA-000000992";
    string public constant CERN_ZENODO_DOI = "10.5281/zenodo.23045297";

    address public immutable tokenAddress;
    bytes32 public immutable merkleRoot;
    address public daoTreasury;
    uint256 public immutable airdropEndTime;

    // Mapping to prevent double claims
    mapping(address => bool) public hasClaimed;
    mapping(string => bool) public githubClaimed;

    uint256 public totalClaimedTokens;
    uint256 public totalClaimants;

    event Claimed(
        address indexed claimant,
        uint256 amount,
        string tier,
        uint256 timestamp
    );

    event UnclaimedTokensReclaimed(
        address indexed treasury,
        uint256 amount,
        uint256 timestamp
    );

    modifier onlyTreasury() {
        require(msg.sender == daoTreasury, "UNAUTHORIZED_TREASURY");
        _;
    }

    constructor(
        address _tokenAddress,
        bytes32 _merkleRoot,
        address _treasury,
        uint256 _durationDays
    ) {
        require(_tokenAddress != address(0) && _treasury != address(0), "INVALID_ADDRESSES");
        tokenAddress = _tokenAddress;
        merkleRoot = _merkleRoot;
        daoTreasury = _treasury;
        airdropEndTime = block.timestamp + (_durationDays * 1 days);
    }

    /**
     * @notice Verify and claim airdropped $TQ compute gas tokens using a Merkle proof.
     * @param claimant Address of the claiming wallet.
     * @param amount Quantity of $TQ tokens allocated.
     * @param tier Classification string (e.g. "TIER_1_DEVELOPER", "TIER_2_QUANT").
     * @param merkleProof Array of cryptographic sibling hashes.
     */
    function claim(
        address claimant,
        uint256 amount,
        string calldata tier,
        bytes32[] calldata merkleProof
    ) external {
        require(block.timestamp <= airdropEndTime, "AIRDROP_EXPIRED");
        require(!hasClaimed[claimant], "ALREADY_CLAIMED");
        require(amount > 0, "ZERO_CLAIM_AMOUNT");

        // Verify Merkle Proof
        bytes32 leaf = keccak256(bytes.concat(keccak256(abi.encode(claimant, amount, tier))));
        require(verifyProof(merkleProof, merkleRoot, leaf), "INVALID_MERKLE_PROOF");

        hasClaimed[claimant] = true;
        totalClaimedTokens += amount;
        totalClaimants += 1;

        require(IERC20(tokenAddress).transfer(claimant, amount), "TRANSFER_FAILED");

        emit Claimed(claimant, amount, tier, block.timestamp);
    }

    /**
     * @notice Reclaims any unclaimed tokens back to the DAO Treasury after airdrop expiration.
     */
    function reclaimUnclaimedTokens() external onlyTreasury {
        require(block.timestamp > airdropEndTime, "AIRDROP_STILL_ACTIVE");
        uint256 remaining = IERC20(tokenAddress).balanceOf(address(this));
        require(remaining > 0, "NO_REMAINING_TOKENS");

        require(IERC20(tokenAddress).transfer(daoTreasury, remaining), "RECLAIM_FAILED");
        emit UnclaimedTokensReclaimed(daoTreasury, remaining, block.timestamp);
    }

    /**
     * @dev Cryptographic Merkle proof verification helper (OpenZeppelin standard).
     */
    function verifyProof(
        bytes32[] memory proof,
        bytes32 root,
        bytes32 leaf
    ) internal pure returns (bool) {
        bytes32 computedHash = leaf;
        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 proofElement = proof[i];
            if (computedHash <= proofElement) {
                computedHash = keccak256(abi.encodePacked(computedHash, proofElement));
            } else {
                computedHash = keccak256(abi.encodePacked(proofElement, computedHash));
            }
        }
        return computedHash == root;
    }
}

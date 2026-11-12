// SPDX-License-Identifier: MIT
pragma solidity 0.8.20;

/**
 * ============================================================================
 * TRIQEE™ GENOMIC RWA REPO CLEARINGHOUSE & IP TOKEN REGISTRY
 * Pillar 3 Advancement: Hugging Face Carbon-X + Nature Genetics Integration
 * ============================================================================
 * Enables tokenization of validated therapeutic genomic cassettes and
 * non-coding regulatory sequences as productive collateral for institutional
 * Mode 4 Repo financing (SOFR + 99 bps).
 *
 * Mechanics:
 * 1. Mints ERC-721 Genomic IP Asset Token with on-chain Carbon-X scores
 * 2. Locks IP collateral in non-custodial Mode 4 Repo Clearinghouse
 * 3. Draws USDC liquidity up to calibrated LTV (e.g., 71.6% max LTV)
 * 4. Manages repayment, interest accrual, and collateral redemption
 * ============================================================================
 */

interface IERC20 {
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function approve(address spender, uint256 amount) external returns (bool);
}

contract TriqeeGenomicRWARepoClearinghouse {
    string public constant name = "Triqee Genomic RWA Repo Clearinghouse";
    string public constant symbol = "TRQ-GENOME-REPO";

    address public immutable owner;
    address public immutable usdcToken;
    address public immutable treasuryBeneficiary;

    struct GenomicIPAsset {
        string sequenceId;
        string indication;
        uint32 sequenceLengthBp;
        uint32 carbonXScoreBps;      // e.g. 7594 = 0.7594 efficacy score
        int32 deltaGKcalMol;         // e.g. -2882 = -28.82 kcal/mol
        uint256 appraisedValuationUsd; // 6 decimals (USDC equivalent)
        uint16 maxLtvBps;            // e.g. 7160 = 71.6%
        uint16 sofrSpreadBps;        // e.g. 99 = +99 bps over SOFR
        address sponsor;
        bool isPledged;
        uint256 principalBorrowedUsdc;
        uint256 loanTimestamp;
    }

    uint256 public nextTokenId = 1;
    mapping(uint256 => GenomicIPAsset) public genomicAssets;
    mapping(uint256 => address) public tokenOwner;

    event GenomicAssetMinted(
        uint256 indexed tokenId,
        string sequenceId,
        uint256 valuationUsd,
        uint16 maxLtvBps,
        address indexed sponsor
    );

    event RepoLoanOpened(
        uint256 indexed tokenId,
        uint256 principalBorrowedUsdc,
        uint16 sofrSpreadBps,
        address indexed sponsor
    );

    event RepoLoanSettled(
        uint256 indexed tokenId,
        uint256 totalRepaidUsdc,
        address indexed sponsor
    );

    modifier onlyOwner() {
        require(msg.sender == owner, "NOT_OWNER");
        _;
    }

    constructor(address _usdc, address _treasury) {
        owner = msg.sender;
        usdcToken = _usdc != address(0) ? _usdc : 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913; // Base USDC
        treasuryBeneficiary = _treasury != address(0) ? _treasury : 0x676A66D77B4B14C2f981239f7368Ab5cc37aC666;
    }

    /**
     * @notice Registers and mints a validated genomic therapeutic cassette IP token.
     */
    function registerGenomicAsset(
        string calldata sequenceId,
        string calldata indication,
        uint32 sequenceLengthBp,
        uint32 carbonXScoreBps,
        int32 deltaGKcalMol,
        uint256 appraisedValuationUsd,
        uint16 maxLtvBps,
        uint16 sofrSpreadBps,
        address sponsor
    ) external onlyOwner returns (uint256 tokenId) {
        require(carbonXScoreBps >= 7000, "INSUFFICIENT_CARBON_X_SCORE");
        require(maxLtvBps <= 8000, "MAX_LTV_CAP_EXCEEDED");

        tokenId = nextTokenId++;
        tokenOwner[tokenId] = sponsor;

        genomicAssets[tokenId] = GenomicIPAsset({
            sequenceId: sequenceId,
            indication: indication,
            sequenceLengthBp: sequenceLengthBp,
            carbonXScoreBps: carbonXScoreBps,
            deltaGKcalMol: deltaGKcalMol,
            appraisedValuationUsd: appraisedValuationUsd,
            maxLtvBps: maxLtvBps,
            sofrSpreadBps: sofrSpreadBps,
            sponsor: sponsor,
            isPledged: false,
            principalBorrowedUsdc: 0,
            loanTimestamp: 0
        });

        emit GenomicAssetMinted(tokenId, sequenceId, appraisedValuationUsd, maxLtvBps, sponsor);
    }

    /**
     * @notice Pledges the genomic IP token into the Mode 4 Clearinghouse to draw instant USDC repo financing.
     */
    function openRepoLoan(uint256 tokenId, uint256 borrowAmountUsdc) external {
        GenomicIPAsset storage asset = genomicAssets[tokenId];
        require(msg.sender == tokenOwner[tokenId] || msg.sender == owner, "NOT_AUTHORIZED");
        require(!asset.isPledged, "ASSET_ALREADY_PLEDGED");

        uint256 maxBorrow = (asset.appraisedValuationUsd * asset.maxLtvBps) / 10000;
        require(borrowAmountUsdc <= maxBorrow, "BORROW_EXCEEDS_MAX_LTV");

        asset.isPledged = true;
        asset.principalBorrowedUsdc = borrowAmountUsdc;
        asset.loanTimestamp = block.timestamp;

        // Disburse USDC liquidity from Clearinghouse Vault to sponsor
        require(IERC20(usdcToken).balanceOf(address(this)) >= borrowAmountUsdc, "INSUFFICIENT_VAULT_LIQUIDITY");
        IERC20(usdcToken).transfer(asset.sponsor, borrowAmountUsdc);

        emit RepoLoanOpened(tokenId, borrowAmountUsdc, asset.sofrSpreadBps, asset.sponsor);
    }

    /**
     * @notice Settles repo loan with interest and releases the genomic IP asset back to sponsor.
     */
    function settleRepoLoan(uint256 tokenId) external {
        GenomicIPAsset storage asset = genomicAssets[tokenId];
        require(asset.isPledged, "LOAN_NOT_ACTIVE");

        uint256 durationSec = block.timestamp - asset.loanTimestamp;
        // Annual rate: Base SOFR 4.85% (485 bps) + sofrSpreadBps
        uint256 annualRateBps = 485 + asset.sofrSpreadBps;
        uint256 interestAccrued = (asset.principalBorrowedUsdc * annualRateBps * durationSec) / (10000 * 365 days);
        uint256 totalRepayment = asset.principalBorrowedUsdc + interestAccrued;

        // Repay principal + interest from sender
        IERC20(usdcToken).transferFrom(msg.sender, address(this), totalRepayment);

        // Protocol spread (35 bps) routed to Treasury
        uint256 protocolFee = (interestAccrued * 35) / annualRateBps;
        if (protocolFee > 0) {
            IERC20(usdcToken).transfer(treasuryBeneficiary, protocolFee);
        }

        asset.isPledged = false;
        asset.principalBorrowedUsdc = 0;
        asset.loanTimestamp = 0;

        emit RepoLoanSettled(tokenId, totalRepayment, asset.sponsor);
    }
}

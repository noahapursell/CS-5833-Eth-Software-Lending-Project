// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

contract GameRental {
    // --- Structures ---
    struct RentalSession {
        uint256 rentalStartTimestamp;
        uint256 lastBilledTimestamp;
    }
    
    struct Owner {
        uint256 ownerRate;
        uint256 ownerPayout;
        uint256 maxRentalDuration;
        bool isRentable;
        address currentRenter;
        RentalSession session;
    }
    
    struct Game {
        uint256 price;
        uint256 devRate; // (Not used in payout splitting logic; payment goes fully to developer)
        uint256 devPayout;
        address developer;
        uint256 defaultOwnerRate;
        uint256 defaultMaxRentalDuration;
        address[] ownerList;
        // Mapping from an owner address to their owner details for this game
        mapping(address => Owner) owners;
    }
    
    struct Renter {
        uint256 balance;
        uint256[] currentRentals; // List of game IDs the renter is currently renting (for query purposes)
    }
    
    // --- State Variables ---
    // Mapping from gameId to Game details
    mapping(uint256 => Game) private games;
    // Mapping from renter address to renter details
    mapping(address => Renter) public renters;
    // Keep an array of all registered game IDs (needed for query functions)
    uint256[] public gameIds;
    
    // --- Events ---
    event GameRegistered(uint256 gameId, address developer, uint256 price);
    event GamePurchased(uint256 gameId, address owner, uint256 price);
    event RentalStarted(uint256 gameId, address owner, address renter);
    event RentalStopped(uint256 gameId, address owner, address renter);
    event RentCollected(uint256 gameId, address owner, address renter, uint256 fee);

    // --- Functions ---

    /// @notice Register a new game. Only one registration per gameId is allowed.
    /// @param gameId The unique identifier for the game.
    /// @param price The price to purchase the game (in wei).
    /// @param defaultOwnerRate The default rental rate for owners.
    /// @param defaultMaxRentalDuration The default maximum duration (in seconds) between rental billings.
    /// @param devRate A parameter reserved for future use (developer rate).
    function registerGame(
        uint256 gameId, 
        uint256 price, 
        uint256 defaultOwnerRate, 
        uint256 defaultMaxRentalDuration, 
        uint256 devRate
    ) external {
        Game storage game = games[gameId];
        require(game.price == 0, "Game already registered");
        game.price = price;
        game.devRate = devRate;
        game.developer = msg.sender;
        game.defaultOwnerRate = defaultOwnerRate;
        game.defaultMaxRentalDuration = defaultMaxRentalDuration;
        gameIds.push(gameId);
        emit GameRegistered(gameId, msg.sender, price);
    }
    
    /// @notice Purchase a game to become its owner.
    /// @dev The payment must exactly equal the game price.
    /// @param gameId The id of the game to purchase.
    function buyGame(uint256 gameId) external payable {
        Game storage game = games[gameId];
        require(game.price > 0, "Game not registered");
        require(msg.value == game.price, "Incorrect payment amount");
        // Check that the buyer is not already an owner.
        require(game.owners[msg.sender].ownerRate == 0, "Already an owner");
        
        // Create a new Owner entry using the game's default parameters.
        game.owners[msg.sender] = Owner({
            ownerRate: game.defaultOwnerRate,
            ownerPayout: 0,
            maxRentalDuration: game.defaultMaxRentalDuration,
            isRentable: true,
            currentRenter: address(0),
            session: RentalSession(0, 0)
        });
        game.ownerList.push(msg.sender);
        
        // Payment is directed to the developer's payout bucket.
        game.devPayout += msg.value;
        emit GamePurchased(gameId, msg.sender, msg.value);
    }
    
    /// @notice Rent a game from a specific owner. The renter deposits ETH that will cover rental fees.
    /// @param gameId The id of the game to rent.
    /// @param ownerAddr The address of the owner from whom the game is rented.
    function rentGame(uint256 gameId, address ownerAddr) external payable {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[ownerAddr];
        require(ownerData.ownerRate > 0, "Owner not found for this game");
        require(ownerData.isRentable, "Game is not available for rent");
        require(ownerData.currentRenter == address(0), "Game already rented by someone else");
        require(msg.value >= ownerData.ownerRate, "Insufficient deposit for rental fee");
        
        // Add the deposit to the renter's balance.
        renters[msg.sender].balance += msg.value;
        // Record the rental in the renter’s list.
        renters[msg.sender].currentRentals.push(gameId);
        
        // Start the rental session.
        ownerData.currentRenter = msg.sender;
        ownerData.session = RentalSession({
            rentalStartTimestamp: block.timestamp,
            lastBilledTimestamp: block.timestamp
        });
        emit RentalStarted(gameId, ownerAddr, msg.sender);
    }
    
    /// @notice Check on-chain if a renter is allowed to play the rented game.
    /// @param gameId The id of the game.
    /// @param ownerAddr The address of the owner.
    /// @param renterAddr The renter's address.
    /// @return A boolean indicating whether the renter currently has access.
    function canPlay(uint256 gameId, address ownerAddr, address renterAddr) external view returns (bool) {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[ownerAddr];
        return (ownerData.currentRenter == renterAddr);
    }
    
    /// @notice Stop a current rental session.
    /// @dev Can be called by either the owner or the renter.
    /// @param gameId The id of the game.
    /// @param ownerAddr The address of the owner with whom the rental was active.
    function stopRenting(uint256 gameId, address ownerAddr) external {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[ownerAddr];
        require(msg.sender == ownerAddr || msg.sender == ownerData.currentRenter, "Unauthorized: not owner or current renter");
        address renterAddr = ownerData.currentRenter;
        require(renterAddr != address(0), "No active rental to stop");
        
        // Reset the rental session.
        ownerData.currentRenter = address(0);
        ownerData.session = RentalSession(0, 0);
        emit RentalStopped(gameId, ownerAddr, renterAddr);
        // For simplicity, the gameId is not removed from the renter's currentRentals array.
    }
    
    /// @notice Allows an owner to mark their game as available or unavailable for rental.
    /// @param gameId The id of the game.
    /// @param _status True if the game should be rentable, false otherwise.
    function setRentable(uint256 gameId, bool _status) external {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[msg.sender];
        require(ownerData.ownerRate > 0, "Caller is not an owner of this game");
        ownerData.isRentable = _status;
    }
    
    /// @notice Collects rent from the renter if the rental period has elapsed.
    /// @param gameId The id of the game.
    /// @param ownerAddr The address of the owner collecting rent.
    function collectRent(uint256 gameId, address ownerAddr) external {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[ownerAddr];
        require(ownerData.currentRenter != address(0), "No active rental to bill");
        
        uint256 elapsed = block.timestamp - ownerData.session.lastBilledTimestamp;
        // For simplicity, if the elapsed time exceeds the maximum rental duration,
        // a fixed fee (ownerRate) is deducted from the renter's balance.
        if (elapsed >= ownerData.maxRentalDuration) {
            uint256 fee = ownerData.ownerRate;
            require(renters[ownerData.currentRenter].balance >= fee, "Renter has insufficient balance for billing");
            renters[ownerData.currentRenter].balance -= fee;
            ownerData.ownerPayout += fee;
            ownerData.session.lastBilledTimestamp = block.timestamp;
            emit RentCollected(gameId, ownerAddr, ownerData.currentRenter, fee);
        }
    }
    
    /// @notice Withdraw accumulated payout by an owner.
    /// @param gameId The id of the game.
    function withdrawOwnerPayout(uint256 gameId) external {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[msg.sender];
        uint256 amount = ownerData.ownerPayout;
        require(amount > 0, "No payout available for owner");
        ownerData.ownerPayout = 0;
        payable(msg.sender).transfer(amount);
    }
    
    /// @notice Withdraw accumulated payout by the developer.
    /// @param gameId The id of the game.
    function withdrawDevPayout(uint256 gameId) external {
        Game storage game = games[gameId];
        require(msg.sender == game.developer, "Only the developer can withdraw developer payout");
        uint256 amount = game.devPayout;
        require(amount > 0, "No payout available for developer");
        game.devPayout = 0;
        payable(msg.sender).transfer(amount);
    }
    
    /// @notice Allows a renter to withdraw any remaining deposit balance.
    function withdrawRenterBalance() external {
        uint256 amount = renters[msg.sender].balance;
        require(amount > 0, "No balance available to withdraw");
        renters[msg.sender].balance = 0;
        payable(msg.sender).transfer(amount);
    }
    
    /// @notice Query function to return a list of game IDs owned by a given address.
    /// @param ownerAddr The address of the owner.
    /// @return An array of game IDs.
    function getOwnedGames(address ownerAddr) external view returns (uint256[] memory) {
        uint256 count = 0;
        // Count how many games the ownerAddr owns.
        for (uint256 i = 0; i < gameIds.length; i++) {
            uint256 gameId = gameIds[i];
            Game storage game = games[gameId];
            if (game.owners[ownerAddr].ownerRate > 0) {
                count++;
            }
        }
        
        uint256[] memory owned = new uint256[](count);
        uint256 index = 0;
        for (uint256 i = 0; i < gameIds.length; i++) {
            uint256 gameId = gameIds[i];
            Game storage game = games[gameId];
            if (game.owners[ownerAddr].ownerRate > 0) {
                owned[index] = gameId;
                index++;
            }
        }
        return owned;
    }
    
    /// @notice Query function to return a list of game IDs that a renter is currently renting.
    /// @param renterAddr The address of the renter.
    /// @return An array of game IDs.
    function getCurrentRentals(address renterAddr) external view returns (uint256[] memory) {
        return renters[renterAddr].currentRentals;
    }
    
    /// @notice Query function that returns available rental options for a specific game.
    /// @param gameId The id of the game.
    /// @return A tuple containing an array of owner addresses and an array of their rental rates.
    function getAvailableRentals(uint256 gameId) external view returns (address[] memory, uint256[] memory) {
        Game storage game = games[gameId];
        uint256 count = 0;
        for (uint256 i = 0; i < game.ownerList.length; i++) {
            address ownerAddr = game.ownerList[i];
            Owner storage ownerData = game.owners[ownerAddr];
            if (ownerData.isRentable && ownerData.currentRenter == address(0)) {
                count++;
            }
        }
        
        address[] memory ownersAvailable = new address[](count);
        uint256[] memory rates = new uint256[](count);
        uint256 index = 0;
        for (uint256 i = 0; i < game.ownerList.length; i++) {
            address ownerAddr = game.ownerList[i];
            Owner storage ownerData = game.owners[ownerAddr];
            if (ownerData.isRentable && ownerData.currentRenter == address(0)) {
                ownersAvailable[index] = ownerAddr;
                rates[index] = ownerData.ownerRate;
                index++;
            }
        }
        return (ownersAvailable, rates);
    }
    
    // --- Fallback Functions ---
    fallback() external payable {}
    receive() external payable {}
}

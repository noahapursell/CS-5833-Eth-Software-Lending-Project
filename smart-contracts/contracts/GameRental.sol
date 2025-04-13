// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.28;

contract GameRental {
    // --- Structures ---
    struct RentalSession {
        uint256 rentalStartTimestamp;
        uint256 lastBilledTimestamp;
    }

    struct Owner {
        uint256 ownerRate; // Fee per minute for the owner.
        uint256 ownerPayout;
        bool isRentable;
        address currentRenter;
        RentalSession session;
    }

    struct Game {
        uint256 price;
        uint256 devRate; // Fee per minute for the developer.
        uint256 devPayout;
        address developer;
        uint256 defaultOwnerRate;
        address[] ownerList;
        // Mapping from an owner address to their owner details for this game.
        mapping(address => Owner) owners;
    }

    struct Renter {
        uint256 balance;
        uint256[] currentRentals; // List of game IDs the renter is currently renting.
    }

    // --- State Variables ---
    // Mapping from gameId to Game details.
    mapping(uint256 => Game) private games;
    // Mapping from renter address to renter details.
    mapping(address => Renter) public renters;
    // Array of all registered game IDs.
    uint256[] public gameIds;

    // --- Events ---
    event GameRegistered(uint256 gameId, address developer, uint256 price);
    event GamePurchased(uint256 gameId, address owner, uint256 price);
    event RentalStarted(uint256 gameId, address owner, address renter);
    event RentalStopped(uint256 gameId, address owner, address renter);
    event RentCollected(
        uint256 gameId,
        address owner,
        address renter,
        uint256 fee
    );

    // --- Functions ---

    /// @notice Register a new game.
    /// @param gameId The unique identifier for the game.
    /// @param price The price to purchase the game (in wei).
    /// @param defaultOwnerRate The default rental rate for owners (per minute).
    /// @param devRate The developer rate (per minute).
    function registerGame(
        uint256 gameId,
        uint256 price,
        uint256 defaultOwnerRate,
        uint256 devRate
    ) external {
        Game storage game = games[gameId];
        require(game.price == 0, "Game already registered");
        game.price = price;
        game.devRate = devRate;
        game.developer = msg.sender;
        game.defaultOwnerRate = defaultOwnerRate;
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
        require(game.owners[msg.sender].ownerRate == 0, "Already an owner");

        // Create a new Owner entry using the game's default owner rate.
        game.owners[msg.sender] = Owner({
            ownerRate: game.defaultOwnerRate,
            ownerPayout: 0,
            isRentable: true,
            currentRenter: address(0),
            session: RentalSession(0, 0)
        });
        game.ownerList.push(msg.sender);

        // The payment goes to the developer's payout bucket.
        game.devPayout += msg.value;
        emit GamePurchased(gameId, msg.sender, msg.value);
    }

    /// @notice Rent a game from a specific owner. The renter deposits ETH that covers rental fees.
    /// @param gameId The id of the game to rent.
    /// @param ownerAddr The address of the owner from whom the game is rented.
    function rentGame(uint256 gameId, address ownerAddr) external payable {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[ownerAddr];
        require(ownerData.ownerRate > 0, "Owner not found for this game");
        require(ownerData.isRentable, "Game is not available for rent");
        require(
            ownerData.currentRenter == address(0),
            "Game already rented by someone else"
        );
        require(
            msg.value >= ownerData.ownerRate,
            "Insufficient deposit for rental fee"
        );

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

    /// @notice Check if a renter is allowed to play a rented game.
    /// @param gameId The id of the game.
    /// @param ownerAddr The address of the owner.
    /// @param renterAddr The renter's address.
    /// @return A boolean indicating whether the renter has access.
    function canPlay(
        uint256 gameId,
        address ownerAddr,
        address renterAddr
    ) external view returns (bool) {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[ownerAddr];
        return (ownerData.currentRenter == renterAddr);
    }

    /**
     * @notice Stops an active rental session and collects any outstanding rent before termination.
     * @dev Can be called by the owner or the current renter. It internally calls _collectRent
     *      to ensure that any accrued rent is billed prior to stopping the rental.
     *      Also removes the game ID from the renter's currentRentals array.
     * @param gameId The identifier of the game being rented.
     * @param ownerAddr The address of the owner with whom the rental session is active.
     */
    function stopRenting(uint256 gameId, address ownerAddr) external {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[ownerAddr];
        require(
            msg.sender == ownerAddr || msg.sender == ownerData.currentRenter,
            "Unauthorized: not owner or current renter"
        );

        address renterAddr = ownerData.currentRenter;
        require(renterAddr != address(0), "No active rental to stop");

        // Collect any outstanding rent before stopping the rental session.
        _collectRent(gameId, ownerAddr);

        // Remove the gameId from the renter's currentRentals array.
        _removeRental(renterAddr, gameId);

        // Reset the rental session.
        ownerData.currentRenter = address(0);
        ownerData.session = RentalSession(0, 0);
        emit RentalStopped(gameId, ownerAddr, renterAddr);
    }

    /**
     * @notice Sets the rental availability status for the caller's game ownership.
     * @param gameId The identifier of the game.
     * @param _status True if the game should be made available for rent, false otherwise.
     */
    function setRentable(uint256 gameId, bool _status) external {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[msg.sender];
        require(ownerData.ownerRate > 0, "Caller is not an owner of this game");
        ownerData.isRentable = _status;
    }

    /**
     * @notice Internal function that collects rent based on the elapsed time since the last billing.
     * @dev This function calculates fees proportionate to the elapsed time using per-minute rates,
     *      deducts the fees from the renter's balance, updates payout buckets for owner and developer,
     *      and emits a RentCollected event.
     *      The fee calculation has been updated to round up to avoid undercharging.
     * @param gameId The identifier of the game for which rent is being collected.
     * @param ownerAddr The address of the owner associated with the rental session.
     * @return collectedFee The total fee collected (sum of owner fee and developer fee).
     */
    function _collectRent(
        uint256 gameId,
        address ownerAddr
    ) internal returns (uint256 collectedFee) {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[ownerAddr];
        uint256 elapsed = block.timestamp -
            ownerData.session.lastBilledTimestamp;

        if (elapsed > 0) {
            // Calculate the required fees using rounding up.
            uint256 requiredOwnerFee = (ownerData.ownerRate * elapsed + 59) /
                60;
            uint256 requiredDevFee = (game.devRate * elapsed + 59) / 60;
            uint256 requiredTotalFee = requiredOwnerFee + requiredDevFee;

            // Available funds from the current renter.
            uint256 availableBalance = renters[ownerData.currentRenter].balance;

            if (availableBalance >= requiredTotalFee) {
                // Full collection: deduct the full fee and update payouts.
                collectedFee = requiredTotalFee;
                renters[ownerData.currentRenter].balance =
                    availableBalance -
                    collectedFee;
                ownerData.ownerPayout += requiredOwnerFee;
                game.devPayout += requiredDevFee;
                ownerData.session.lastBilledTimestamp = block.timestamp;
                emit RentCollected(
                    gameId,
                    ownerAddr,
                    ownerData.currentRenter,
                    collectedFee
                );
            } else {
                // Partial collection: the renter doesn't have enough.
                // Collect whatever is available.
                collectedFee = availableBalance;
                // Allocate the available funds in proportion to the required fees.
                // For the owner portion:
                uint256 partialOwnerFee = (availableBalance *
                    requiredOwnerFee) / requiredTotalFee;
                // For the developer portion, the remainder:
                uint256 partialDevFee = availableBalance - partialOwnerFee;

                ownerData.ownerPayout += partialOwnerFee;
                game.devPayout += partialDevFee;
                // Set the renter's balance to zero.
                renters[ownerData.currentRenter].balance = 0;
                // Emit event for the collected (partial) rent.
                emit RentCollected(
                    gameId,
                    ownerAddr,
                    ownerData.currentRenter,
                    collectedFee
                );
                // Stop the rental session since there are insufficient funds.
                address renterAddr = ownerData.currentRenter;
                ownerData.currentRenter = address(0);
                ownerData.session = RentalSession(0, 0);
                emit RentalStopped(gameId, ownerAddr, renterAddr);
            }
        }
        return collectedFee;
    }

    /**
     * @notice External function to trigger rent collection for an active rental session.
     * @dev This function simply wraps the internal _collectRent function.
     * @param gameId The identifier of the game.
     * @param ownerAddr The address of the owner from whom rent is being collected.
     */
    function collectRent(uint256 gameId, address ownerAddr) external {
        _collectRent(gameId, ownerAddr);
    }

    /**
     * @notice Deposits additional funds into the caller's rental balance.
     * @dev This function allows the current renter (or any user) to add more ETH to their balance,
     *      which can be used for paying ongoing rental fees.
     */
    function depositFunds() external payable {
        require(msg.value > 0, "Must send ETH to deposit");
        renters[msg.sender].balance += msg.value;
    }

    /**
     * @notice Withdraw the accumulated payout for the owner.
     * @param gameId The id of the game.
     */
    function withdrawOwnerPayout(uint256 gameId) external {
        Game storage game = games[gameId];
        Owner storage ownerData = game.owners[msg.sender];
        uint256 amount = ownerData.ownerPayout;
        require(amount > 0, "No payout available for owner");
        ownerData.ownerPayout = 0;
        payable(msg.sender).transfer(amount);
    }

    /**
     * @notice Withdraw the accumulated payout for the developer.
     * @param gameId The id of the game.
     */
    function withdrawDevPayout(uint256 gameId) external {
        Game storage game = games[gameId];
        require(
            msg.sender == game.developer,
            "Only the developer can withdraw developer payout"
        );
        uint256 amount = game.devPayout;
        require(amount > 0, "No payout available for developer");
        game.devPayout = 0;
        payable(msg.sender).transfer(amount);
    }

    /**
     * @notice Allows a renter to withdraw any remaining deposit balance.
     */
    function withdrawRenterBalance() external {
        uint256 amount = renters[msg.sender].balance;
        require(amount > 0, "No balance available to withdraw");
        renters[msg.sender].balance = 0;
        payable(msg.sender).transfer(amount);
    }

    /**
     * @notice Returns a list of game IDs that the given address owns.
     * @param ownerAddr The address of the owner.
     * @return An array of game IDs.
     */
    function getOwnedGames(
        address ownerAddr
    ) external view returns (uint256[] memory) {
        uint256 count = 0;
        // Count how many games the address owns.
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

    /**
     * @notice Returns a list of game IDs that the renter is currently renting.
     * @param renterAddr The address of the renter.
     * @return An array of game IDs.
     */
    function getCurrentRentals(
        address renterAddr
    ) external view returns (uint256[] memory) {
        return renters[renterAddr].currentRentals;
    }

    /**
     * @notice Returns available rental options for a specific game.
     * @param gameId The id of the game.
     * @return A tuple containing an array of owner addresses and an array of their rental rates.
     */
    function getAvailableRentals(
        uint256 gameId
    ) external view returns (address[] memory, uint256[] memory) {
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

    /**
     * @notice Internal helper function to remove a gameId from a renter's currentRentals array.
     * @param renterAddr The renter address.
     * @param gameId The game identifier to remove.
     */
    function _removeRental(address renterAddr, uint256 gameId) internal {
        uint256 length = renters[renterAddr].currentRentals.length;
        for (uint256 i = 0; i < length; i++) {
            if (renters[renterAddr].currentRentals[i] == gameId) {
                // Swap with the last element and pop.
                renters[renterAddr].currentRentals[i] = renters[renterAddr]
                    .currentRentals[length - 1];
                renters[renterAddr].currentRentals.pop();
                break;
            }
        }
    }

    /**
     * @notice Returns details of all registered games that are available for purchase.
     * @return gameIdsArr An array of game IDs.
     * @return developers An array of developers for each game.
     * @return prices An array of purchase prices for each game.
     * @return defaultOwnerRates An array of the default owner rental rates (per minute) for each game.
     * @return devRates An array of developer rental rates (per minute) for each game.
     */
    function getBuyableGames()
        external
        view
        returns (
            uint256[] memory gameIdsArr,
            address[] memory developers,
            uint256[] memory prices,
            uint256[] memory defaultOwnerRates,
            uint256[] memory devRates
        )
    {
        uint256 len = gameIds.length;
        gameIdsArr = new uint256[](len);
        developers = new address[](len);
        prices = new uint256[](len);
        defaultOwnerRates = new uint256[](len);
        devRates = new uint256[](len);

        for (uint256 i = 0; i < len; i++) {
            uint256 id = gameIds[i];
            Game storage g = games[id];
            gameIdsArr[i] = id;
            developers[i] = g.developer;
            prices[i] = g.price;
            defaultOwnerRates[i] = g.defaultOwnerRate;
            devRates[i] = g.devRate;
        }
    }

    // --- Fallback Functions ---
    fallback() external payable {}

    receive() external payable {}
}

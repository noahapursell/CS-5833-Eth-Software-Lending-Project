import { expect } from "chai";
import { ethers } from "hardhat";
import { time } from "@nomicfoundation/hardhat-network-helpers";
import hre from "hardhat";

describe("GameRental", function () {
  // Deploys the contract and registers a game
  async function deployGameRentalFixture() {
    const [developer, owner, renter, other] = await ethers.getSigners();
    
    const GameRental = await ethers.getContractFactory("GameRental");
    const gameRental = await GameRental.deploy();
    
    // Developer registers a game with id = 1.
    // Parameters: price, defaultOwnerRate, defaultMaxRentalDuration (in seconds), devRate.
    const price = ethers.parseEther("1");
    const defaultOwnerRate = ethers.parseEther("0.1"); // Fee per rental period
    const defaultMaxRentalDuration = 60; // 60 seconds (for testing purposes)
    const devRate = 10; // Arbitrary value
    
    await gameRental.connect(developer).registerGame(1, price, defaultOwnerRate, defaultMaxRentalDuration, devRate);
    
    return { gameRental, developer, owner, renter, other, price, defaultOwnerRate, defaultMaxRentalDuration };
  }
  
  describe("Registration and Purchase", function () {
    it("Should register a game correctly", async function () {
      const { gameRental, developer, price } = await deployGameRentalFixture();
      // Check that gameIds array contains the registered gameId.
      expect(await gameRental.gameIds(0)).to.equal(1);
    });
    
    it("Should allow a user to purchase a game and become an owner", async function () {
      const { gameRental, owner, price, defaultOwnerRate } = await deployGameRentalFixture();
      
      await expect(
        gameRental.connect(owner).buyGame(1, { value: price })
      ).to.emit(gameRental, "GamePurchased");
      
      // Verify that the owner's list includes game id 1.
      const ownedGames = await gameRental.getOwnedGames(owner.address);
      expect(ownedGames.length).to.equal(1);
      expect(ownedGames[0]).to.equal(1);
    });
    
    it("Should forward funds to the developer's payout bucket on purchase", async function () {
      const { gameRental, developer, owner, price } = await deployGameRentalFixture();
      
      await gameRental.connect(owner).buyGame(1, { value: price });
      
      // Developer withdraws payout. Using Hardhat's changeEtherBalances matcher to verify balance change.
      await expect(
        gameRental.connect(developer).withdrawDevPayout(1)
      ).to.changeEtherBalances(
        [developer, gameRental],
        [price, -price]
      );
    });
  });
  
  describe("Renting", function () {
    it("Should allow renting if game is available and deposit is sufficient", async function () {
      const { gameRental, owner, renter, defaultOwnerRate, price } = await deployGameRentalFixture();
      
      // Owner purchases the game.
      await gameRental.connect(owner).buyGame(1, { value: price });
      
      // Renter rents the game from the owner.
      await expect(
        gameRental.connect(renter).rentGame(1, owner.address, { value: defaultOwnerRate })
      ).to.emit(gameRental, "RentalStarted");
      
      // Verify that canPlay returns true.
      const canPlay = await gameRental.canPlay(1, owner.address, renter.address);
      expect(canPlay).to.equal(true);
      
      // Check that renter's current rentals includes game id 1.
      const rentals = await gameRental.getCurrentRentals(renter.address);
      expect(rentals.length).to.equal(1);
      expect(rentals[0]).to.equal(1);
    });
    
    it("Should not allow renting if the owner is marked as not rentable", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate } = await deployGameRentalFixture();
      
      await gameRental.connect(owner).buyGame(1, { value: price });
      
      // Owner disables renting.
      await gameRental.connect(owner).setRentable(1, false);
      
      await expect(
        gameRental.connect(renter).rentGame(1, owner.address, { value: defaultOwnerRate })
      ).to.be.revertedWith("Game is not available for rent");
    });
    
    it("Should allow either the renter or owner to stop a rental", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate } = await deployGameRentalFixture();
      
      await gameRental.connect(owner).buyGame(1, { value: price });
      await gameRental.connect(renter).rentGame(1, owner.address, { value: defaultOwnerRate });
      
      // Renter stops the rental.
      await expect(
        gameRental.connect(renter).stopRenting(1, owner.address)
      ).to.emit(gameRental, "RentalStopped");
      
      // Start a new rental and then have the owner stop it.
      await gameRental.connect(renter).rentGame(1, owner.address, { value: defaultOwnerRate });
      await expect(
        gameRental.connect(owner).stopRenting(1, owner.address)
      ).to.emit(gameRental, "RentalStopped");
    });
  });
  
  describe("Rent Collection and Withdrawals", function () {
    it("Should collect rent after the rental period and allow owner withdrawal", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate, defaultMaxRentalDuration } = await deployGameRentalFixture();
      
      await gameRental.connect(owner).buyGame(1, { value: price });
      await gameRental.connect(renter).rentGame(1, owner.address, { value: defaultOwnerRate });
      
      // Increase time by more than the rental period.
      await time.increase(defaultMaxRentalDuration + 1);
      
      // Collect rent.
      await expect(
        gameRental.connect(owner).collectRent(1, owner.address)
      ).to.emit(gameRental, "RentCollected");
      
      // Owner withdraws payout.
      await expect(
        gameRental.connect(owner).withdrawOwnerPayout(1)
      ).to.changeEtherBalances(
        [owner, gameRental],
        [defaultOwnerRate, -defaultOwnerRate]
      );
    });
    
    it("Should allow a renter to withdraw any remaining deposit", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate } = await deployGameRentalFixture();
      
      await gameRental.connect(owner).buyGame(1, { value: price });
      await gameRental.connect(renter).rentGame(1, owner.address, { value: defaultOwnerRate });
      
      // Without any rental charge, the renter should be able to withdraw the deposit.
      await expect(
        gameRental.connect(renter).withdrawRenterBalance()
      ).to.changeEtherBalances(
        [renter, gameRental],
        [defaultOwnerRate, -defaultOwnerRate]
      );
    });
  });
  
  describe("Query Functions", function () {
    it("Should return owned games for an owner", async function () {
      const { gameRental, owner, price } = await deployGameRentalFixture();
      
      await gameRental.connect(owner).buyGame(1, { value: price });
      const owned = await gameRental.getOwnedGames(owner.address);
      expect(owned.length).to.equal(1);
      expect(owned[0]).to.equal(1);
    });
    
    it("Should return current rentals for a renter", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate } = await deployGameRentalFixture();
      
      await gameRental.connect(owner).buyGame(1, { value: price });
      await gameRental.connect(renter).rentGame(1, owner.address, { value: defaultOwnerRate });
      const rentals = await gameRental.getCurrentRentals(renter.address);
      expect(rentals.length).to.equal(1);
      expect(rentals[0]).to.equal(1);
    });
    
    it("Should return available rental options for a game", async function () {
      const { gameRental, owner, price, defaultOwnerRate } = await deployGameRentalFixture();
      
      await gameRental.connect(owner).buyGame(1, { value: price });
      // At this point, the game should be available for rent.
      const [availableOwners, rates] = await gameRental.getAvailableRentals(1);
      expect(availableOwners.length).to.equal(1);
      expect(availableOwners[0]).to.equal(owner.address);
      expect(rates[0]).to.equal(defaultOwnerRate);
    });
  });
});

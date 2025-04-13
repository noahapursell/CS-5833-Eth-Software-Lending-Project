import { expect } from "chai";
import { ethers } from "hardhat";
import { time } from "@nomicfoundation/hardhat-network-helpers";

describe("GameRental", function () {
  // Deploys the contract and registers a game
  async function deployGameRentalFixture() {
    const [developer, owner, renter, other] = await ethers.getSigners();
    const GameRental = await ethers.getContractFactory("GameRental");
    const gameRental = await GameRental.deploy();
    // Register game using four parameters:
    // gameId, price, defaultOwnerRate, devRate.
    // For testing, we use:
    // - gameId = 1
    // - price = 1 ETH
    // - defaultOwnerRate = 0.1 ETH per minute
    // - devRate = 10 (an arbitrary unit for testing)
    const gameId = 1;
    const price = ethers.parseEther("1");
    const defaultOwnerRate = ethers.parseEther("0.1");
    const devRate = 10;
    await gameRental.connect(developer).registerGame(gameId, price, defaultOwnerRate, devRate);

    return { gameRental, developer, owner, renter, other, gameId, price, defaultOwnerRate, devRate };
  }

  describe("Registration and Purchase", function () {
    it("Should register a game correctly", async function () {
      const { gameRental, gameId } = await deployGameRentalFixture();
      expect(await gameRental.gameIds(0)).to.equal(gameId);
    });

    it("Should allow a user to purchase a game and become an owner", async function () {
      const { gameRental, owner, price, defaultOwnerRate, gameId } = await deployGameRentalFixture();
      await expect(gameRental.connect(owner).buyGame(gameId, { value: price }))
        .to.emit(gameRental, "GamePurchased");

      // Verify that the owner's list includes game id 1.
      const ownedGames = await gameRental.getOwnedGames(owner.address);
      expect(ownedGames.length).to.equal(1);
      expect(ownedGames[0]).to.equal(gameId);
    });

    it("Should forward funds to the developer's payout bucket on purchase", async function () {
      const { gameRental, developer, owner, price, gameId } = await deployGameRentalFixture();
      await gameRental.connect(owner).buyGame(gameId, { value: price });

      // Developer withdraws payout.
      await expect(gameRental.connect(developer).withdrawDevPayout(gameId))
        .to.changeEtherBalances([developer, gameRental], [price, -price]);
    });
  });

  describe("Renting", function () {
    it("Should allow renting if game is available and deposit is sufficient", async function () {
      const { gameRental, owner, renter, defaultOwnerRate, price, gameId } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });

      await expect(
        gameRental.connect(renter).rentGame(gameId, owner.address, { value: defaultOwnerRate })
      ).to.emit(gameRental, "RentalStarted");

      // Verify that canPlay returns true.
      const canPlay = await gameRental.canPlay(gameId, owner.address, renter.address);
      expect(canPlay).to.equal(true);

      // Check that renter's current rentals includes game id 1.
      const rentals = await gameRental.getCurrentRentals(renter.address);
      expect(rentals.length).to.equal(1);
      expect(rentals[0]).to.equal(gameId);
    });

    it("Should not allow renting if the owner is marked as not rentable", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate, gameId } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });

      // Owner disables renting.
      await gameRental.connect(owner).setRentable(gameId, false);

      await expect(
        gameRental.connect(renter).rentGame(gameId, owner.address, { value: defaultOwnerRate })
      ).to.be.revertedWith("Game is not available for rent");
    });

    it("Should allow either the renter or owner to stop a rental and remove rental from currentRentals", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate, gameId } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });

      // Renter starts rental.
      await gameRental.connect(renter).rentGame(gameId, owner.address, { value: defaultOwnerRate });

      // Renter stops the rental.
      await expect(
        gameRental.connect(renter).stopRenting(gameId, owner.address)
      ).to.emit(gameRental, "RentalStopped");

      let rentals = await gameRental.getCurrentRentals(renter.address);
      expect(rentals.length).to.equal(0);

      // Start a new rental and then have the owner stop it.
      await gameRental.connect(renter).rentGame(gameId, owner.address, { value: defaultOwnerRate });
      await expect(
        gameRental.connect(owner).stopRenting(gameId, owner.address)
      ).to.emit(gameRental, "RentalStopped");

      rentals = await gameRental.getCurrentRentals(renter.address);
      expect(rentals.length).to.equal(0);
    });

    it("Should allow a renter to deposit additional funds to extend rental", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate, gameId } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });
      await gameRental.connect(renter).rentGame(gameId, owner.address, { value: defaultOwnerRate });

      // Check initial deposit balance.
      const initialBalance = await gameRental.renters(renter.address);

      // Deposit additional funds.
      const extraDeposit = ethers.parseEther("0.5");
      await expect(
        gameRental.connect(renter).depositFunds({ value: extraDeposit })
      ).to.changeEtherBalances(
        [renter, gameRental],
        [-extraDeposit, extraDeposit]
      );

      const updatedBalance = await gameRental.renters(renter.address);
      expect(updatedBalance).to.equal(initialBalance + extraDeposit);
    });
  });

  describe("Rent Collection and Withdrawals", function () {
    it("Should collect rent after the rental period and allow owner withdrawal", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate, gameId, devRate } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });

      // Instead of using defaultOwnerRate (0.1 ETH), we deposit more so that fees can be collected.
      const depositAmount = ethers.parseEther("0.2");
      await gameRental.connect(renter).rentGame(gameId, owner.address, { value: depositAmount });

      // Increase time by 61 seconds.
      await time.increase(61);

      // Collect rent.
      await expect(
        gameRental.connect(owner).collectRent(gameId, owner.address)
      ).to.emit(gameRental, "RentCollected");

      // Expected fee calculations:
      // Using rounding up: fee = (rate * elapsed + 59) / 60.
      const elapsed = 62;
      // defaultOwnerRate is 0.1 ETH in wei.
      const ownerFee = (BigInt(defaultOwnerRate.toString()) * BigInt(elapsed) + BigInt(59)) / BigInt(60);
      const devFee = (BigInt(devRate) * BigInt(elapsed) + BigInt(59)) / BigInt(60);
      const totalFee = ownerFee + devFee;

      // Owner withdraws payout. The owner's payout should match the owner fee portion.
      await expect(
        gameRental.connect(owner).withdrawOwnerPayout(gameId)
      ).to.changeEtherBalances(
        [owner, gameRental],
        [BigInt(ownerFee), -BigInt(ownerFee)]
      );
    });

    it("Should allow a renter to withdraw any remaining deposit", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate, gameId } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });
      await gameRental.connect(renter).rentGame(gameId, owner.address, { value: defaultOwnerRate });

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
      const { gameRental, owner, price, gameId } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });
      const owned = await gameRental.getOwnedGames(owner.address);
      expect(owned.length).to.equal(1);
      expect(owned[0]).to.equal(gameId);
    });

    it("Should return current rentals for a renter", async function () {
      const { gameRental, owner, renter, price, defaultOwnerRate, gameId } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });
      await gameRental.connect(renter).rentGame(gameId, owner.address, { value: defaultOwnerRate });
      const rentals = await gameRental.getCurrentRentals(renter.address);
      expect(rentals.length).to.equal(1);
      expect(rentals[0]).to.equal(gameId);
    });

    it("Should return available rental options for a game", async function () {
      const { gameRental, owner, price, defaultOwnerRate, gameId } = await deployGameRentalFixture();

      await gameRental.connect(owner).buyGame(gameId, { value: price });
      const [availableOwners, rates] = await gameRental.getAvailableRentals(gameId);
      expect(availableOwners.length).to.equal(1);
      expect(availableOwners[0]).to.equal(owner.address);
      expect(rates[0]).to.equal(defaultOwnerRate);
    });
  });
});

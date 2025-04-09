import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

export default buildModule("GameRentalSetup", (m) => {
    // Deploy GameRental contract
    const gameRental = m.contract("GameRental");

    // Pick accounts
    const developer = m.getAccount(0);
    const owner1 = m.getAccount(1);
    const owner2 = m.getAccount(2);
    const owner3 = m.getAccount(3);

    // Developer registers games
    const regGame1 = m.call(gameRental, "registerGame", [1, 1000000000000000000n, 1000n, 3600n, 1000n], { from: developer, id: "registerGame1" });
    const regGame2 = m.call(gameRental, "registerGame", [2, 2000000000000000000n, 1200n, 7200n, 1000n], { from: developer, id: "registerGame2" });

    // Owners buy games
    m.call(gameRental, "buyGame", [1], { from: owner1, value: 1000000000000000000n, id: "buyGame1", after: [regGame1] });
    m.call(gameRental, "buyGame", [2], { from: owner2, value: 2000000000000000000n, id: "buyGame2", after: [regGame2] });
    m.call(gameRental, "buyGame", [1], { from: owner3, value: 1000000000000000000n, id: "buyGame3", after: [regGame1] });

    return { gameRental };
});

This is the source code for my entry of "Catch the Queen" in The Long Pygame Summer Jam.

No AI was used to generate any of it; any bugs or questionable design decisions were all my own, either researched, recalled, or regurgitated.

## Dependencies

This project was built in WSL on Windows 11. It assumes Windows has python installed via the [Python Install Manager](https://www.python.org/downloads/) and that WSL has `make` installed. Yes I realize this is kind of a bastardization of a build system, but the Makefile's simple enough you can swap out some other python binary and it should still work well.

## Building

`make install run` will create a virtual environment, install the dependencies, and run the program. Once the virtual environment is created, you can just use `make run` to run.
 `make ship` needs some refining but will create a build folder containing the version playable in-browser.

## Running

Once the virtual environment is created, you can just use `make run` to run.

## About

In the early stages of the jam, I couldn't really think of any particularly satisfying game ideas fitting the theme of "Swarm" at first. Instead of making even a one-page GDD, I simply started off programming in mechanics and "let the game tell me" what it wanted to be.

So I started off with a simulation of [Boids](https://en.wikipedia.org/wiki/Boids).. or at least a reasonable approximation. I got the flocking behavior but they'd kind of end up in a sort of formation that resembled a hexagonal lattice. I wanted somethin more "swarmy" so I played around with their maximum speed until I got something satisfactory. They probably collide with each other with low chance, but eh. Consolidating some hitboxes can help make things less overwhelming.

I had told Mom what I had been working on, and she gave me the interesting idea of "What if instead of avoiding them, you tried to catch them?". So I introduced behavior to make them flee from the mouse. They had the bad habit of clustering on the edges/in the corners, so then I thought to combine the two-one boid that constantly flees, and others that constantly chase. Thus the idea of "Catch the Queen" was born.

## Credits

"Press Start 2P" font from <https://www.dafont.com/press-start-2p.font>

Great ideas: Mom
Most enthusiastic playtester: Dad
Quality Assurance: Bro
Moral support: Sis
Everything else: Me

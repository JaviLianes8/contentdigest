# contentdigest 1.0.0 certification report

The 1.0.0 certification bar applied to contentdigest. PyPI has 0.2.0, whose wheel holds
byte for byte the modules of `main` at 24f06de, so every change listed here is a change
against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (24f06de, same code as PyPI 0.2.0)
- [ ] Baseline gates on 0.2.0
- [ ] API review and 1.0.0 changes (item 1)
- [ ] Errors, typing, docstrings and doctests (items 2 to 5)
- [ ] Ground truth: specifications and registries fetched live, reference implementations and real program output (item 7)
- [ ] Contract, fuzz and author mutation round (items 6, 9, 18)
- [ ] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [ ] Packaging, e2e and upgrade from PyPI 0.2.0, every Python (items 8, 10, 13, 14)
- [ ] Gates (item 15), final run
- [ ] PR and trace guard CLEAN
- [ ] Five QA lenses (item 19)
- [ ] Independent reviewer (item 16)
- [ ] Merge and publish (item 17), left to the maintainer

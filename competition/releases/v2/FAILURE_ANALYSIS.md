# Failure analysis

No official public replay corpus was available, so ranked official failure classes cannot be computed without guessing. The user-reported hidden score 0.06 indicates runtime integration worked but the V1 policy likely suffered from weak state-action exploration, weak action discovery, and insufficient goal/mechanic inference. V2 directly targets those classes with state-action graph exploration, action-semantics posterior updates, role inference, and mechanic detectors.

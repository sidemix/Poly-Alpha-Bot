# src/strategies/base.py

class BaseStrategy:
    """
    Minimal base class for all strategies.

    We keep this intentionally tiny so it can't blow up imports.
    Concrete strategies (like BTCIntraday) will subclass this and
    implement score().
    """

    # Optional human-readable name
    name = "base-strategy"

    def filter_markets(self, markets):
        """
        Optional pre-filter hook.

        Default: return markets unchanged.
        """
        return markets

    def score(self, market, ref_price):
        """
        Main scoring interface.

        Must be implemented by subclasses.
        Should return an Opportunity object (or dict) or None.
        """
        raise NotImplementedError("score() must be implemented by subclasses")

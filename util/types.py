class FixedCost:
    def __init__(self, name, amount, yearly=False, category=None):
        self.name = name
        self._amount = float(amount)
        self.yearly = yearly
        self.category = category

    def amount(self):
        return self._amount / 12.0 if self.yearly else self._amount

    def summary(self, total):
        return f"{self.amount():.2f}€ ({100.0*self.amount()/total:.2f}%)"

class FixedCostArray:
    def __init__(self, *fixed_costs: [FixedCost]):
        self.items = fixed_costs

    def amount(self):
        return sum(map(lambda x: x.amount(), self.items))

    def summary(self, total):
        return f"{self.amount():.2f}€ ({100.0*self.amount()/total:.2f}%)"

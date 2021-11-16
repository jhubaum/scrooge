from . import config

config.load()
import plan

def print_spending_plan():
    total_spendings = sum([
        plan.MONTHLY_INVESTMENT_GOAL.amount(),
        plan.MONTHLY_SAVING_GOAL.amount(),
        plan.FIXED_COSTS.amount(),
        plan.RECURRING_SPENDINGS.amount(),
        plan.ENVELOPES.amount()
    ])

    # guideline
    # fixed costs + recurring spendings: 50-60%
    # investments: 10%
    # savings: 5-10%
    # fun/for free allocation: 20-35%
    print(f"Income:\t\t\t {plan.MONTHLY_INCOME}€")
    print(f"Fixed costs:\t\t {plan.FIXED_COSTS.summary(plan.MONTHLY_INCOME)}")
    print(f"Recurring spendings:\t {plan.RECURRING_SPENDINGS.summary(plan.MONTHLY_INCOME)}")
    print(f"Investments:\t\t {plan.MONTHLY_INVESTMENT_GOAL.summary(plan.MONTHLY_INCOME)}")
    print(f"Saving goal:\t\t {plan.MONTHLY_SAVING_GOAL.summary(plan.MONTHLY_INCOME)}")

    if plan.MONTHLY_INCOME < total_spendings:
        print(f"Error in spending plan: The spendings ({total_spendings:.2f}€) exceed the income ({plan.MONTHLY_INCOME}€)")
        return

    print(f"Unallocated money (will be kept as additional emergency fund): {plan.MONTHLY_INCOME - total_spendings:.2f}€")



    print()
    print("To automate spendings, create the following transfers:")
    for c in plan.FIXED_COSTS.items:
        print(f"{c.amount():.2f}€ for {c.name}")
    print(f"{plan.MONTHLY_INVESTMENT_GOAL.amount()}€ to investment account")
    print(f"{plan.MONTHLY_SAVING_GOAL.amount()}€ to savings account")
    print(f"{plan.ENVELOPES.amount()}€ to the spendings account")


print_spending_plan()

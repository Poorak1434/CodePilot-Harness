"""
Math utilities module containing calculation functions.
"""

def add(a: float, b: float) -> float:
    return a + b

def calculate_discount(price: float, discount_percent: float) -> float:
    """
    Calculates the discounted price given original price and percentage discount.
    Bug: Incorrect formula (divides by 1000 instead of 100).
    """
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount percent must be between 0 and 100")
    discount_amount = price * (discount_percent / 1000)  # BUG: should be / 100
    return price - discount_amount

from decimal import Decimal, ROUND_HALF_UP


def to_decimal(value):
    try:
        return Decimal(str(value)) if value else Decimal(0)
    except Exception:
        return Decimal(0)


def calculate_price(weight, rate22, making, gst, making_type="fixed", stone=0):

    weight = to_decimal(weight)
    rate22 = to_decimal(rate22)
    making = to_decimal(making)
    gst = to_decimal(gst)
    stone = to_decimal(stone)

    gold_value = weight * rate22

    if making_type == "percent":
        making_cost = gold_value * (making / Decimal(100))
    else:
        making_cost = weight * making

    subtotal = gold_value + making_cost + stone
    tax = subtotal * (gst / Decimal(100))
    total = subtotal + tax

    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_product_price(weight, rate_obj, stone=0):
    return calculate_price(
        weight=weight,
        rate22=rate_obj.rate_22k,
        making=rate_obj.making_charge_per_gram,
        gst=rate_obj.gst_percentage,
        making_type=rate_obj.making_type,
        stone=stone
    )
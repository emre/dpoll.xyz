from django import template

register = template.Library()


@register.filter
def cool_number(value, num_decimals=6):
    """
    Django template filter to convert regular numbers to a
    cool format (ie: 2K, 434.4K, 33M...)
    :param value: number
    :param num_decimals: Number of decimal digits
    """
    if not value:
        return "N/A"
    int_value = int(value)
    formatted_number = '{{:.{}f}}'.format(num_decimals)
    if int_value < 1000:
        return str(int_value)
    elif int_value < 1000000:
        return formatted_number.format(int_value/1000).split(".")[0] + 'K'
    elif int_value < 1000000000:
        return formatted_number.format(int_value/1000000).split(".")[0] + 'M'
    else:
        return formatted_number.format(int_value/1000000000).split(".")[0] + 'B'

from django.shortcuts import render
from lightsteem.client import Client
from lightsteem.helpers.amount import Amount

from .models import Sponsor


def steem_per_mvests():
    c = Client()
    info = c.get_dynamic_global_properties()
    return (float(Amount(info["total_vesting_fund_steem"]).amount) /
            (float(Amount(info["total_vesting_shares"]).amount) / 1e6))


def vests_to_sp(steem_per_mvest, vests):
    return vests / 1e6 * steem_per_mvest


def sponsors(request):
    sponsors = Sponsor.objects.order_by("-delegation_amount")
    steem_per_mvest_value = steem_per_mvests()
    sponsor_list = []
    total_sp_delegated = 0
    for sponsor in sponsors:
        sponsor.delegation_amount_in_sp = int(vests_to_sp(
            steem_per_mvest_value,
            sponsor.delegation_amount
        ))
        total_sp_delegated+= sponsor.delegation_amount_in_sp
        sponsor_list.append(sponsor)
    return render(request, "sponsors.html", {
        "sponsors": sponsor_list,
        "count": len(sponsor_list),
        "total": total_sp_delegated,
    })

from datetime import datetime, date, time
import pytz


def get_comment_body(curator):
    comment_template = f"""
Thanks for contributing to the dPoll content.

You have been upvoted from our community curation account (@dpoll.curation) in courtesy of {curator}.

Come, join our community at [dPoll discord server](https://discord.gg/ZcV8SGr).
***
<sup>If you want to support dPoll curation, you can also delegate some steem power. Quick steem connect links to delegate: 
[50SP](https://steemconnect.com/sign/delegateVestingShares?delegatee=dpoll.curation&vesting_shares=50%20SP) | [100SP](https://steemconnect.com/sign/delegateVestingShares?delegatee=dpoll.curation&vesting_shares=100%20SP) | [250SP](https://steemconnect.com/sign/delegateVestingShares?delegatee=dpoll.curation&vesting_shares=250%20SP) | [500SP](https://steemconnect.com/sign/delegateVestingShares?delegatee=dpoll.curation&vesting_shares=500%20SP)  
</sup>
"""
    return comment_template


def addTzInfo(t, timezone='UTC'):
    """Returns a datetime object with tzinfo added"""
    if t and isinstance(t, (datetime, date, time)) and t.tzinfo is None:
        utc = pytz.timezone(timezone)
        t = utc.localize(t)
    return t
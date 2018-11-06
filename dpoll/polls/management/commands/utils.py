def get_comment_body(curator):
    comment_template = f"""
Thanks for contributing to the dPoll content.

You have been upvoted from our community curation account (@dpoll.curation) in courtesy of {curator}.
***
<sup>If you want to support dPoll curation, you can also delegate some steem power. Quick steem connect links to delegate: 
[50SP](https://steemconnect.com/sign/delegateVestingShares?delegatee=dpoll.curation&vesting_shares=50%20SP) | [100SP](https://steemconnect.com/sign/delegateVestingShares?delegatee=dpoll.curation&vesting_shares=100%20SP) | [250SP](https://steemconnect.com/sign/delegateVestingShares?delegatee=dpoll.curation&vesting_shares=250%20SP) | [500SP](https://steemconnect.com/sign/delegateVestingShares?delegatee=dpoll.curation&vesting_shares=500%20SP)  
</sup>
"""
    return comment_template

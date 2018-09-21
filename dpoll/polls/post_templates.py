def get_body(question, choices, permlink):
    body = f"#### {question}\n***\n"
    for choice in choices:
        body += f" - {choice}\n***\n"
    body += f"*Answer the question at [dpoll.xyz](https://dpoll.xyz/detail/{permlink}/).*"
    return body

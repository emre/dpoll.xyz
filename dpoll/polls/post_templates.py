def get_body(question, choices, author, permlink):
    body = f"#### {question}\n***\n"
    if question.description:
        body += f"{question.description}\n***\n"
    for choice in choices:
        body += f" - {choice}\n***\n"
    body += f"*Answer the question at [dpoll.xyz](https://dpoll.xyz/detail/@{author}/{permlink}/).*"
    return body

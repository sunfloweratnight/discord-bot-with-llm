import re


def sanitize_args(args):
    arguments = ' '.join(args)
    content = arguments.replace('”', '"').replace('「', '"')
    return re.sub("<@\d+>", "", content).strip()

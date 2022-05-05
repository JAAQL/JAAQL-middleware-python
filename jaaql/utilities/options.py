from typing import List

OPTION__short_max = 2
OPTION__required = "required"
OPTION__optional = "optional"
OPTION__flag = "flag    "
OPTION__parameter = "parameter"
OPTION__short_id = "-"
OPTION__long_id = "--"

ERR__missing_required_options = "ERROR: Missing required options!"
ERR__missing_option = "ERROR: Missing option '%s'!"
ERR__option_short_too_long = "Option %d has short description longer than %d!"
ERR__expected_option = "Expected option, instead found '%s'!"
ERR__no_matching_option = "Could not find option with identifier '%s'!"
ERR__expected_argument = "Expected argument for option '%s'!"
ERR__option_already_exists = "Option '%s' supplied more than once!"
ERR__missing_argument = "Missing argument for option '%s'!"


class Option:

    def __init__(self, short: str, long: str, description: str, is_flag: bool, required=True):
        self.short = short
        self.long = long
        self.required = required
        self.description = description
        self.is_flag = is_flag


OPT_KEY__vault_key = "vault-key"
OPT_KEY__email_credentials = "email-credentials"
OPT_KEY__help = "help"

DEFAULT_OPTIONS: List[Option] = [
    Option(
        short="h",
        long=OPT_KEY__help,
        required=False,
        description="Outputs the help directory",
        is_flag=True
    ),
    Option(
        short="v",
        long=OPT_KEY__vault_key,
        required=False,
        description="Encrypts the jaaql vault which stores internal sensitive information",
        is_flag=False
    ),
    Option(
        short="e",
        long=OPT_KEY__email_credentials,
        required=False,
        description="Provides SMTP/IMAP email credentials into the JAAQL server. Base64 encoded json dict of the format"
        " { \"my_account_name\": \"my_account_password\" }",
        is_flag=False
    )
]


def parse_options(args: dict, do_print_help: bool = True, require_override: list = None, title: str = None,
                  use_options: [Option] = None):
    if use_options is None:
        use_options = DEFAULT_OPTIONS

    args = args[1:]

    if require_override is None:
        require_override = []

    if len(args) == 0 and do_print_help:
        print_help(title, use_options)
        print()
        print(ERR__missing_required_options)
        exit(0)

    found_options = {}

    cur_option = None
    for i, cur_arg in zip(range(len(args)), args):
        filled_arg = False

        if cur_option is None:
            matching = None

            if cur_arg.startswith(OPTION__long_id):
                matching = [option for option in use_options if option.long == cur_arg[len(OPTION__long_id):]]
            elif cur_arg.startswith(OPTION__short_id):
                matching = [option for option in use_options if option.short == cur_arg[len(OPTION__short_id):]]

            if matching is None:
                raise Exception(ERR__expected_option % cur_arg)
            if len(matching) == 0:
                raise Exception(ERR__no_matching_option % cur_arg)

            cur_option = matching[0]
            if cur_option.long in found_options:
                raise Exception(ERR__option_already_exists % cur_option.long)

            found_options[cur_option.long] = None
        else:
            found_options[cur_option.long] = cur_arg
            filled_arg = True

        if cur_option.is_flag or filled_arg:
            cur_option = None

    if cur_option is not None and not cur_option.is_flag:
        raise Exception(ERR__missing_argument % cur_option.long)

    if OPT_KEY__help in found_options:
        print_help(title, use_options)
        exit(0)

    missing_options = [option for option in use_options if option.required and option.long not in found_options]
    missing_options = [missing for missing in missing_options if missing not in require_override]
    if len(missing_options) != 0:
        raise Exception(ERR__missing_option % missing_options[0].long)

    return found_options


DEFAULT_TITLE = "JAAQL middleware system"


def print_help(title: str = None, use_options: [Option] = None):
    if use_options is None:
        use_options = DEFAULT_OPTIONS

    if title is None:
        title = DEFAULT_TITLE
    print("The %s, written in python" % title)
    print()
    print("OPTIONS:")

    max_long_spaces = max([len(option.long) for option in use_options])

    for option in use_options:
        if len(option.short) > OPTION__short_max:
            raise Exception(ERR__option_short_too_long % (option.short, OPTION__short_max))

        short_spaces = "".join([" "] * OPTION__short_max)[:OPTION__short_max - len(option.short)] + "\t"
        long_spaces = "".join([" "] * max_long_spaces)[:max_long_spaces - len(option.long)] + "\t"

        required = OPTION__required if option.required else OPTION__optional
        required += "\t"

        option_match = option.long + long_spaces + "-" + option.short + short_spaces
        is_flag = OPTION__flag if option.is_flag else OPTION__parameter
        is_flag += "\t"

        print("\t--" + option_match + required + is_flag + option.description)

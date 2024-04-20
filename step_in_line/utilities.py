import random
import uuid


def unique_name_from_base_uuid4(base, max_length=63):
    """Append a UUID to the provided string.

    This function is used to generate a name using UUID instead of timestamps
    for uniqueness.

    Args:
        base (str): String used as prefix to generate the unique name.
        max_length (int): Maximum length for the resulting string (default: 63).

    Returns:
        str: Input parameter with appended timestamp.
    """
    random.seed(int(uuid.uuid4()))  # using uuid to randomize
    unique = str(uuid.uuid4())
    trimmed_base = base[: max_length - len(unique) - 1]
    return "{}-{}".format(trimmed_base, unique)

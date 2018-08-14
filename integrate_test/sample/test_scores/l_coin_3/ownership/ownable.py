from iconservice import *


def only_owner(func):
    if not isfunction(func):
        raise IconScoreException(f"{func} isn't function.")

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):
        if isinstance(calling_obj, IconScoreBase):
            sender = calling_obj.tx.origin if calling_obj.tx else calling_obj.msg.sender
            if calling_obj.owner != sender:
                raise IconScoreException(f"{sender} don't have authority.")

            return func(calling_obj, *args, **kwargs)

    return __wrapper

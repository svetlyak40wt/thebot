
def force_unicode(value):
    if isinstance(value, str):
        value = value.decode('utf-8')
    return value

def force_str(value):
    if isinstance(value, unicode):
        value = value.encode('utf-8')
    return value

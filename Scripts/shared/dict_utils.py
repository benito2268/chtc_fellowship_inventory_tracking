

# prints a dictionary (in 'flat' style)
def print_dict(d):
    flat = flatten_dict(d) 
    for key, value in flat.items():
        print(key, ':', value)


    print('\n')

# flattens a dictionary with '.' as the seperator
#
# params:
#   nested - current dictionary to be flattened
#   parent_key - the (already flattened) path the leads to nested - used by the recursive call only
# returns:
#   a dictionary that maps a 'path' to each bottom level value in the original
#   ex) an entry would look like  "hardware.condo_chassis.model" : "Dell PowerEdge ..." 
def flatten_dict(nested, parent_key=''):
    # using a list means we have append() and extend()
    flat = []
    for key, value in nested.items():
        if parent_key == '':
            # we're at the top level
            newkey = key
        else:
            # we're somewhere in a nested level
            newkey = parent_key + '.' + key

        if isinstance(value, dict):
            # if value is a dictionary - recurse further in
            flat.extend(flatten_dict(value, newkey).items())
        else:
            # otherwise, we've hit the base case - append and return once
            flat.append((newkey, value))

    return dict(flat)

# unflattens (nests) a dictionary with '.' as the seperator
def unflatten_dict(flat):
    ret = dict()

    for key, value in flat.items():
        tags = key.split('.')
        sub_dict = ret

        # re-nest all of the levels - not yet worrying about values
        # the last value in the list is the 'leaf' tag - so ignore it for now
        for tag in tags[:-1]:
            if tag not in sub_dict:
                sub_dict[tag] = dict()

            sub_dict = sub_dict[tag]

        # now put the value in the new 'leaf' tag
        sub_dict[tags[-1]] = value

    return ret

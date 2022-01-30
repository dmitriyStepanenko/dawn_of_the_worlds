
def get_position_from_coord(x: int, y: int, len_row: int):
    return x + y * len_row


def get_coord_from_position(position: int, len_row: int):
    return divmod(position, len_row)

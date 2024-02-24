from django import template

register = template.Library()


@register.filter
def split_board(board):
    return [''.join(card) for card in zip(board[::2], board[1::2])]

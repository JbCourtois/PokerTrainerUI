import json


class Tree(list):
    """List with 2 or more elements.

    0: Player id (0=OOP | 1=IP | 5=Luck)
    1: Children as a dict {label: subtree}

    Plus, if node belonds to a player:
    2: Action frequencies
    3: Action EVs
    """

    def __repr__(self):
        return f'Tree(Player {self[0]}, {len(self[1])} children)'

    def get_actions(self, hole_index):
        """Return dict with actions for given hand.

        Out format: {action: [frequency, ev]}
        """
        if self[0] > 1:
            raise ValueError('Cannot be called on chance nodes')

        nb_actions = len(self[1])
        nb_holes = len(self[2]) // nb_actions

        return {
            action: [frequency, ev]
            for (action, frequency, ev) in zip(
                self[1],
                self[2][hole_index::nb_holes],
                self[3][hole_index::nb_holes],
            )
        }


class Game:
    def __init__(self):
        super().__init__()

        self.human_ids = None
        self.pot = None
        self.stack = None
        self.board = None
        self.tree = []
        self.ranges = []

    @staticmethod
    def from_file(filename):
        return TreeParser(filename).game


class TreeParser:
    def __init__(self, file):
        self.game = Game()
        self.stream = None
        self.line = None

        with open(file, encoding='utf8') as self.stream:
            self.parse_headers()
            self.game.tree = self.parse_node()

    def parse_headers(self):
        self.game.human_ids = self._read()
        self.game.pot, self.game.stack = self._read()
        self.game.board = self._read().split(',')
        self.game.ranges = [self._read() for _ in range(2)]

    def parse_node(self, level=0) -> Tree:
        if not self._peek().startswith('\t' * level):
            return None

        player_id = self._consume()
        children = {}
        node = Tree([player_id, children])

        if player_id <= 1:
            # Weights + EVs
            node.extend(self._read() for _ in range(2))

        while (child := self._peek()).startswith('\t' * level):
            if not child:
                break  # End of file

            child = self._consume()
            children[child] = self.parse_node(level=level + 1)

        return node

    def _peek(self):
        if self.line is None:
            self.line = self.stream.readline()
        return self.line

    def _consume(self):
        line = self._peek()
        self.line = None
        return json.loads(line)

    def _read(self):
        return json.loads(self.stream.readline())

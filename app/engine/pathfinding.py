import heapq

from app.utilities import utils

class Djikstra():
    __slots__ = ['open', 'closed', 'cells', 'width', 'height', 'start_pos', 
                 'start_cell', 'unit_team', 'pass_through', 'ai_fog_of_war']

    def __init__(self, start_pos: tuple, grid: list, width: int, height: int, 
                 unit_team: str, pass_through: bool, ai_fog_of_war: bool):
        self.open = []
        heapq.heapify(self.open)
        self.closed = set()
        self.cells = grid # Must keep order
        self.width, self.height = width, height
        self.reset_grid()
        self.start_pos = start_pos
        self.start_cell = self.get_cell(start_pos[0], start_pos[1])
        self.unit_team = unit_team
        self.pass_through = pass_through
        self.ai_fog_of_war = ai_fog_of_war

    def reset_grid(self):
        for cell in self.cells:
            cell.reset()

    def get_cell(self, x, y):
        return self.cells[x * self.height + y]

    def get_adjacent_cells(self, cell):
        """
        Returns adjacent cells to a cell.
        """
        cells = []
        if cell.y < self.height - 1:
            cells.append(self.get_cell(cell.x, cell.y + 1))
        if cell.x < self.width - 1:
            cells.append(self.get_cell(cell.x + 1, cell.y))
        if cell.x > 0:
            cells.append(self.get_cell(cell.x - 1, cell.y))
        if cell.y > 0:
            cells.append(self.get_cell(cell.x, cell.y - 1))
        return cells

    def update_cell(self, adj, cell):
        # g is true distance between this cell and starting position
        adj.g = cell.g + adj.cost
        adj.parent = cell

    def _can_move_through(self, game_board, adj) -> bool:
        if self.pass_through:
            return True
        unit_team = next(iter(game_board.team_grid[adj.x * self.height + adj.y]), None)
        if not unit_team or utils.compare_teams(self.unit_team, unit_team):
            return True
        if self.unit_team == 'player' or self.ai_fog_of_war:
            if not game_board.in_vision((adj.x, adj.y), self.unit_team):
                return True  # Can always move through what you can't see
        return False

    def process(self, game_board: list, movement_left: int) -> set:
        # add starting cell to open heap queue
        heapq.heappush(self.open, (self.start_cell.g, self.start_cell))
        while self.open:
            # pop cell from heap queue
            g, cell = heapq.heappop(self.open)
            # If we've traveled too far -- always g ordered, so leaving at the 
            # first sign of trouble will always work
            if g > movement_left:
                return {(cell.x, cell.y) for cell in self.closed}
            # add cell to closed set so we don't process it twice
            self.closed.add(cell)
            # get adjacent cells for cell
            adj_cells = self.get_adjacent_cells(cell)
            for adj in adj_cells:
                if adj.reachable and adj not in self.closed:
                    if self._can_move_through(game_board, adj):
                        if (adj.g, adj) in self.open:
                            # if adj cell in open list, check if current path
                            # is better than the one previously found for this adj cell
                            if adj.g > cell.g + adj.cost:
                                self.update_cell(adj, cell)
                                heapq.heappush(self.open, (adj.g, adj))
                        else:
                            self.update_cell(adj, cell)
                            heapq.heappush(self.open, (adj.g, adj))
                    else:  # Unit is in the way
                        pass
        # Sometimes gets here if unit is enclosed
        return {(cell.x, cell.y) for cell in self.closed}

class AStar():
    def __init__(self, start_pos: tuple, goal_pos: tuple, grid: list, 
                 width: int, height: int, unit_team: str, 
                 pass_through: bool = False, ai_fog_of_war: bool = False):
        self.cells = grid
        self.width = width
        self.height = height
        self.start_pos = start_pos
        self.goal_pos = goal_pos

        self.start_cell = self.get_cell(start_pos[0], start_pos[1])
        self.end_cell = self.get_cell(goal_pos[0], goal_pos[1]) if goal_pos else None
        self.adj_end = self.get_adjacent_cells(self.end_cell) if self.end_cell else None

        self.unit_team = unit_team
        self.pass_through = pass_through
        self.ai_fog_of_war = ai_fog_of_war

        self.reset()

    def reset_grid(self):
        for cell in self.cells:
            cell.reset()

    def reset(self):
        self.open = []
        heapq.heapify(self.open)
        self.closed = set()
        self.reset_grid()

    def set_goal_pos(self, goal_pos):
        self.goal_pos = goal_pos
        self.end_cell = self.get_cell(goal_pos[0], goal_pos[1])
        self.adj_end = self.get_adjacent_cells(self.end_cell) 

    def get_heuristic(self, cell) -> float:
        """
        Compute the heuristic for this cell
        h is the approximate distance between this cell and the goal cell
        """
        # Get main heuristic
        dx1 = cell.x - self.end_cell.x
        dy1 = cell.y - self.end_cell.y
        h = abs(dx1) + abs(dy1)
        # Are we going in direction of goal?
        # Slight nudge in direction that lies along path from start to end
        dx2 = self.start_cell.x - self.end_cell.x
        dy2 = self.start_cell.y - self.end_cell.y
        cross = abs(dx1 * dy2 - dx2 * dy1)
        return h + cross * .001

    def get_cell(self, x, y):
        return self.cells[x * self.height + y]

    def get_adjacent_cells(self, cell) -> list:
        cells = []
        if cell.y < self.height - 1:
            cells.append(self.get_cell(cell.x, cell.y + 1))
        if cell.x < self.width - 1:
            cells.append(self.get_cell(cell.x + 1, cell.y))
        if cell.x > 0:
            cells.append(self.get_cell(cell.x - 1, cell.y))
        if cell.y > 0:
            cells.append(self.get_cell(cell.x, cell.y - 1))
        return cells

    def update_cell(self, adj, cell):
        # h is approximate distance between this cell and the goal
        # g is true distance between this cell and the starting position
        # f is simply them added together
        adj.g = cell.g + adj.cost
        adj.h = self.get_heuristic(adj)
        adj.parent = cell
        adj.f = adj.h + adj.g

    def return_path(self, cell) -> list:
        path = []
        while cell:
            path.append((cell.x, cell.y))
            cell = cell.parent
        return path

    def _can_move_through(self, game_board, adj, ally_block) -> bool:
        if self.pass_through:
            return True
        unit_team = next(iter(game_board.team_grid[adj.x * self.height + adj.y]), None)
        if not unit_team:
            return True
        if not ally_block and utils.compare_teams(self.unit_team, unit_team):
            return True
        if self.unit_team == 'player' or self.ai_fog_of_war:
            if not game_board.in_vision((adj.x, adj.y), self.unit_team):
                return True
        return False

    def process(self, game_board, adj_good_enough: bool = False, 
                ally_block: bool = False, limit: int = None) -> list:
        # Add starting cell to open queue
        heapq.heappush(self.open, (self.start_cell.f, self.start_cell))
        while self.open:
            f, cell = heapq.heappop(self.open)
            # Make sure we don't process the cell twice
            self.closed.add(cell)
            # If this cell is past the limit, just return None
            # Uses f, not g, because g will cut off if first greedy path fails
            # f only cuts off if all cells are bad
            if limit is not None and cell.f > limit + 1:
                # limit + 1 to account for diagonal heuristic
                return []
            # if ending cell, display found path
            if cell is self.end_cell or (adj_good_enough and cell in self.adj_end):
                return self.return_path(cell)
            # get adjacent cells for cell
            adj_cells = self.get_adjacent_cells(cell)
            for adj in adj_cells:
                if adj.reachable and adj not in self.closed:
                    if self._can_move_through(game_board, adj, ally_block):
                        if (adj.f, adj) in self.open:
                            # if adj cell in open list, check if current path
                            # is better than the one previously found for this adj cell
                            if adj.g > cell.g + adj.cost:
                                self.update_cell(adj, cell)
                                heapq.heappush(self.open, (adj.f, adj))
                        else:
                            self.update_cell(adj, cell)
                            heapq.heappush(self.open, (adj.f, adj))
                    else:  # Is blocked
                        pass
        return []

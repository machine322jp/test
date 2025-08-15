import copy
import random
import sys
import pygame
from collections import deque

# 定数
CELL_SIZE = 40
COLUMNS = 6
ROWS = 14
NEXT_AREA_WIDTH = 200
SCREEN_WIDTH = CELL_SIZE * COLUMNS + NEXT_AREA_WIDTH + CELL_SIZE * COLUMNS
SCREEN_HEIGHT = CELL_SIZE * ROWS
BEST_FIELD_OFFSET_X = CELL_SIZE * COLUMNS + NEXT_AREA_WIDTH

# ぷよの色
PUYO_COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0)
]

# 盤面初期化
field = [[None for _ in range(COLUMNS)] for _ in range(ROWS)]
undo_stack = deque()

# --- ヘルパー関数 ---
def get_cell_color(cell):
    """
    cellが (color, iterationID) のタプルの場合は色部分を返す。
    もともと単一色の表現の場合もそのまま返す。
    """
    return cell[0] if isinstance(cell, tuple) else cell

def color_to_letter(cell):
    if cell is None:
        return "."
    c = get_cell_color(cell)
    mapping = {
        (255, 0, 0): "R",
        (0, 255, 0): "G",
        (0, 0, 255): "B",
        (255, 255, 0): "Y"
    }
    return mapping.get(c, "?")

def print_board(board, label):
    print(f"--- {label} ---")
    for y, row in enumerate(board):
        row_str = ""
        for x, cell in enumerate(row):
            row_str += color_to_letter(cell) + " "
        print(row_str)
    print()

# --- FieldUtils クラス（重力のみ使用） ---
class FieldUtils:
    @staticmethod
    def apply_gravity(field, columns, rows):
        """
        最上段(y=0)は固定して動かさない。
        y=1..rows-1 のみ重力適用（= 下から13段目は落下可能、最上段は落下しない）。
        """
        for x in range(columns):
            top_fixed = field[0][x]  # 最上段は保持
            stack = [field[y][x] for y in reversed(range(1, rows)) if field[y][x] is not None]
            for y in reversed(range(1, rows)):
                field[y][x] = stack.pop(0) if stack else None
            field[0][x] = top_fixed

# --- Puyo クラス ---
class Puyo:
    def __init__(self, color, x, y):
        self.color = color
        self.x = x
        self.y = y
        self.fixed = False

    def draw(self, surface, offset_x=0, offset_y=0):
        pygame.draw.rect(surface, self.color,
                         (offset_x + self.x * CELL_SIZE, offset_y + self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE))
        pygame.draw.rect(surface, (255, 255, 255),
                         (offset_x + self.x * CELL_SIZE, offset_y + self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE), 1)

# --- PuyoPair クラス ---
class PuyoPair:
    REL = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    def __init__(self, c1, c2):
        self.axis = Puyo(c1, 2, 1)
        self.rot = 2
        self.child = self._update_child(c2)

    def _update_child(self, c2):
        dx, dy = self.REL[self.rot]
        return Puyo(c2, self.axis.x + dx, self.axis.y + dy)

    def is_vertical(self):
        return self.axis.x == self.child.x

    def move_horizontal(self, dx):
        nax = self.axis.x + dx
        ncx = self.child.x + dx
        if (0 <= nax < COLUMNS and field[self.axis.y][nax] is None) and (0 <= ncx < COLUMNS and field[self.child.y][ncx] is None):
            self.axis.x = nax
            self.child.x = ncx

    def rotate(self, direction):
        if direction == 'clockwise':
            nr = (self.rot + 1) % 4
        else:
            nr = (self.rot - 1) % 4
        dx, dy = self.REL[nr]
        ncx = self.axis.x + dx
        ncy = self.axis.y + dy
        old_x, old_y = self.axis.x, self.axis.y

        if 0 <= ncx < COLUMNS and 0 <= ncy < ROWS and field[ncy][ncx] is None:
            self.rot = nr
            self.child.x = ncx
            self.child.y = ncy
        else:
            shift = 0
            if ncx < 0:
                shift = 1
            elif ncx >= COLUMNS:
                shift = -1
            if shift:
                test_ax = self.axis.x + shift
                if 0 <= test_ax < COLUMNS and field[self.axis.y][test_ax] is None:
                    self.axis.x = test_ax
                    ncx = self.axis.x + dx
                    ncy = self.axis.y + dy
                    if 0 <= ncx < COLUMNS and 0 <= ncy < ROWS and field[ncy][ncx] is None:
                        self.rot = nr
                        self.child.x = ncx
                        self.child.y = ncy
                    else:
                        self.axis.x = old_x
            else:
                upy = self.axis.y - 1
                if 0 <= upy < ROWS and field[upy][self.axis.x] is None:
                    self.axis.y = upy
                    ncx = self.axis.x + dx
                    ncy = self.axis.y + dy
                    if 0 <= ncx < COLUMNS and 0 <= ncy < ROWS and field[ncy][ncx] is None:
                        self.rot = nr
                        self.child.x = ncx
                        self.child.y = ncy
                    else:
                        self.axis.y = old_y

    def drop_once(self):
        if self.is_vertical():
            if self.axis.y > self.child.y:
                d, u = self.axis, self.child
            else:
                d, u = self.child, self.axis
            ny = d.y + 1
            if ny < ROWS and field[ny][d.x] is None:
                d.y += 1
                u.y += 1
            else:
                self._fix()
        else:
            ax, ay = self.axis.x, self.axis.y + 1
            cx, cy = self.child.x, self.child.y + 1
            can_axis_fall = (ay < ROWS and field[ay][ax] is None)
            can_child_fall = (cy < ROWS and field[cy][cx] is None)
            if can_axis_fall and can_child_fall:
                self.axis.y += 1
                self.child.y += 1
            elif can_axis_fall:
                self.axis.y += 1
            elif can_child_fall:
                self.child.y += 1
            else:
                self._fix()

    def hard_drop(self):
        while not (self.axis.fixed and self.child.fixed):
            self.drop_once()

    def _fix(self):
        # 固定時は iterationID=0（初期盤面扱い）で固定する
        if not self.axis.fixed:
            field[self.axis.y][self.axis.x] = (self.axis.color, 0)
            self.axis.fixed = True
            if self.axis.y == 0:
                field[self.axis.y][self.axis.x] = None
        if not self.child.fixed:
            field[self.child.y][self.child.x] = (self.child.color, 0)
            self.child.fixed = True
            if self.child.y == 0:
                field[self.child.y][self.child.x] = None

    def draw(self, surface):
        self.axis.draw(surface)
        self.child.draw(surface)

def create_new_puyopair():
    c1 = random.choice(PUYO_COLORS)
    c2 = random.choice(PUYO_COLORS)
    return PuyoPair(c1, c2)

def generate_hand():
    return [create_new_puyopair() for _ in range(64)]

hand = []
hand_index = 0
current_pair = None
next_pair = None
double_next_pair = None

def reset_game():
    global field, current_pair, next_pair, double_next_pair, hand, hand_index
    field[:] = [[None for _ in range(COLUMNS)] for _ in range(ROWS)]
    hand[:] = generate_hand()
    hand_index = 3
    current_pair = hand[0]
    next_pair = hand[1]
    double_next_pair = hand[2]
    undo_stack.clear()

def save_state():
    st = {
        'field': copy.deepcopy(field),
        'cpair': copy.deepcopy(current_pair),
        'n1': copy.deepcopy(next_pair),
        'n2': copy.deepcopy(double_next_pair),
        'hand_index': hand_index,
        'hand': copy.deepcopy(hand)
    }
    undo_stack.append(st)

def restore_state():
    global field, current_pair, next_pair, double_next_pair, hand_index, hand
    if undo_stack:
        st = undo_stack.pop()
        field[:] = copy.deepcopy(st['field'])
        current_pair = copy.deepcopy(st['cpair'])
        next_pair = copy.deepcopy(st['n1'])
        double_next_pair = copy.deepcopy(st['n2'])
        hand_index = st['hand_index']
        hand = copy.deepcopy(st['hand'])
    else:
        print("No undo state left.")

# --- 4つ以上の連結グループ検出 ---
def find_4plus_groups():
    visited = [[False]*COLUMNS for _ in range(ROWS)]
    result = []
    for y in range(2, ROWS):
        for x in range(COLUMNS):
            if field[y][x] is None or visited[y][x]:
                continue
            base_color = get_cell_color(field[y][x])
            q = deque([(x, y)])
            visited[y][x] = True
            group = [(x, y)]
            while q:
                cx, cy = q.popleft()
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < COLUMNS and 2 <= ny < ROWS and not visited[ny][nx] and field[ny][nx] is not None and get_cell_color(field[ny][nx]) == base_color:
                        visited[ny][nx] = True
                        q.append((nx, ny))
                        group.append((nx, ny))
            if len(group) >= 4:
                result.append(group)
    return result

def remove_puyos(groups):
    for grp in groups:
        for (x, y) in grp:
            field[y][x] = None

def apply_gravity():
    FieldUtils.apply_gravity(field, COLUMNS, ROWS)

def draw_grid(surface, offset_x=0, offset_y=0):
    for cx in range(COLUMNS + 1):
        px = offset_x + cx * CELL_SIZE
        pygame.draw.line(surface, (40, 40, 40), (px, offset_y), (px, offset_y + CELL_SIZE * ROWS), 1)
    for cy in range(ROWS + 1):
        py = offset_y + cy * CELL_SIZE
        pygame.draw.line(surface, (40, 40, 40), (offset_x, py), (offset_x + CELL_SIZE * COLUMNS, py), 1)

def draw_next(surface, n1, n2, font):
    tx = font.render("Next:", True, (255, 255, 255))
    surface.blit(tx, (COLUMNS * CELL_SIZE + 20, 20))
    if n1:
        bx = COLUMNS * CELL_SIZE + 20
        by = 60
        pygame.draw.rect(surface, n1.axis.color, (bx, by, CELL_SIZE, CELL_SIZE))
        pygame.draw.rect(surface, (255, 255, 255), (bx, by, CELL_SIZE, CELL_SIZE), 1)
        dx, dy = n1.REL[n1.rot]
        cx = bx + dx * CELL_SIZE
        cy = by + dy * CELL_SIZE
        pygame.draw.rect(surface, n1.child.color, (cx, cy, CELL_SIZE, CELL_SIZE))
        pygame.draw.rect(surface, (255, 255, 255), (cx, cy, CELL_SIZE, CELL_SIZE), 1)

    tx2 = font.render("Double:", True, (255, 255, 255))
    surface.blit(tx2, (COLUMNS * CELL_SIZE + 20, 130))
    if n2:
        bx = COLUMNS * CELL_SIZE + 20
        by = 170
        pygame.draw.rect(surface, n2.axis.color, (bx, by, CELL_SIZE, CELL_SIZE))
        pygame.draw.rect(surface, (255, 255, 255), (bx, by, CELL_SIZE, CELL_SIZE), 1)
        dx, dy = n2.REL[n2.rot]
        cx = bx + dx * CELL_SIZE
        cy = by + dy * CELL_SIZE
        pygame.draw.rect(surface, n2.child.color, (cx, cy, CELL_SIZE, CELL_SIZE))
        pygame.draw.rect(surface, (255, 255, 255), (cx, cy, CELL_SIZE, CELL_SIZE), 1)

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("ぷよぷよ(サンプル)")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)

    reset_game()

    global current_pair, next_pair, double_next_pair, hand_index

    while True:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_game()
                elif not (current_pair.axis.fixed and current_pair.child.fixed):
                    if event.key == pygame.K_LEFT:
                        current_pair.move_horizontal(-1)
                    elif event.key == pygame.K_RIGHT:
                        current_pair.move_horizontal(1)
                    elif event.key == pygame.K_z:
                        current_pair.rotate('clockwise')
                    elif event.key == pygame.K_x:
                        current_pair.rotate('counterclockwise')
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_DOWN:
                    save_state()
                    current_pair.hard_drop()
                elif event.key == pygame.K_UP:
                    restore_state()

        if current_pair.axis.fixed and current_pair.child.fixed:
            if field[1][2] is not None or field[0][2] is not None:
                print("Game Over!")
                pygame.quit()
                sys.exit()

            chain_count = 0
            groups = find_4plus_groups()
            while groups:
                chain_count += 1
                remove_puyos(groups)
                screen.fill((0, 0, 0))
                for ry in range(ROWS):
                    for rx in range(COLUMNS):
                        c = field[ry][rx]
                        if c:
                            pygame.draw.rect(screen, get_cell_color(c), (rx * CELL_SIZE, ry * CELL_SIZE, CELL_SIZE, CELL_SIZE))
                draw_grid(screen)
                pygame.display.flip()
                pygame.time.delay(300)

                apply_gravity()
                screen.fill((0, 0, 0))
                for ry in range(ROWS):
                    for rx in range(COLUMNS):
                        c = field[ry][rx]
                        if c:
                            pygame.draw.rect(screen, get_cell_color(c), (rx * CELL_SIZE, ry * CELL_SIZE, CELL_SIZE, CELL_SIZE))
                draw_grid(screen)
                pygame.display.flip()
                pygame.time.delay(300)
                groups = find_4plus_groups()

            if field[2][2] is not None:
                print("Game Over!（左から3列目の12段目が埋まっています）")
                pygame.quit()
                sys.exit()

            current_pair = next_pair
            next_pair = double_next_pair
            double_next_pair = hand[hand_index]
            hand_index = (hand_index + 1) % 64

        screen.fill((0, 0, 0))
        for ry in range(ROWS):
            for rx in range(COLUMNS):
                c = field[ry][rx]
                if c:
                    pygame.draw.rect(screen, get_cell_color(c), (rx * CELL_SIZE, ry * CELL_SIZE, CELL_SIZE, CELL_SIZE))

        draw_grid(screen, 0, 0)

        if not (current_pair.axis.fixed and current_pair.child.fixed):
            current_pair.draw(screen)

        draw_next(screen, next_pair, double_next_pair, font)

        draw_grid(screen, BEST_FIELD_OFFSET_X, 0)

        pygame.display.flip()

if __name__ == "__main__":
    main()

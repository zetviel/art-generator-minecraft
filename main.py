import tkinter as tk
from PIL import Image as IP
from PIL import ImageColor as IC
import pyperclip, json, os, math

def rgb_to_minecraft(r, g, b, colors):
    min_distance = float('inf')
    closest_color = None

    for color_name, color_value in colors.items():
        distance = ((r - color_value[0]) ** 2 +
                    (g - color_value[1]) ** 2 +
                    (b - color_value[2]) ** 2) ** 0.5

        if distance < min_distance:
            min_distance = distance
            closest_color = color_name

    return closest_color

def find_colored_areas(matrix):
    rows = len(matrix)
    visited = [[False] * len(matrix[i]) for i in range(rows)]
    result = []

    def mark_area(y, x):
        start_y, start_x = y, x
        end_y, end_x = y, x
        area_color = matrix[y][x]
        while end_y + 1 < rows and all(
                matrix[end_y + 1][j] == area_color for j in range(start_x, end_x + 1)
                if j < len(matrix[end_y + 1])
        ):
            end_y += 1
        while end_x + 1 < len(matrix[start_y]) and all(
                matrix[i][end_x + 1] == area_color for i in range(start_y, end_y + 1)
                if end_x + 1 < len(matrix[i])
        ):
            end_x += 1
        for i in range(start_y, end_y + 1):
            for j in range(start_x, end_x + 1):
                if j < len(matrix[i]):
                    visited[i][j] = True
        return (start_y, start_x, end_y, end_x, area_color)

    for y in range(rows):
        for x in range(len(matrix[y])):
            if matrix[y][x] != 'null' and not visited[y][x]:
                area = mark_area(y, x)
                if area:
                    start_y, start_x, end_y, end_x, area_color = area
                    if all(matrix[i][j] != 'null' for i in range(start_y, end_y + 1) for j in
                           range(start_x, end_x + 1) if j < len(matrix[i])):
                        area_id = [start_x, start_y, end_x, end_y, area_color]
                        result.append(area_id)

    return result

def read_json(file='settings'):
    with open(f"{file}.json", "r", encoding='utf8') as f:
        data = json.loads(f.read())
    return data

def mat_mult(A, B):
    C = [[0.0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            s = 0.0
            for k in range(4):
                s += A[i][k] * B[k][j]
            C[i][j] = s
    return C

def flatten_mat_row_major(M):
    return [M[i][j] for i in range(4) for j in range(4)]

def rotation_matrices_from_euler(x_deg, y_deg, z_deg):
    rx = math.radians(x_deg)
    ry = math.radians(y_deg)
    rz = math.radians(z_deg)
    cx = math.cos(rx); sx = math.sin(rx)
    cy = math.cos(ry); sy = math.sin(ry)
    cz = math.cos(rz); sz = math.sin(rz)
    Rx = [
        [1, 0, 0, 0],
        [0, cx, -sx, 0],
        [0, sx, cx, 0],
        [0,0,0,1]
    ]
    Ry = [
        [cy, 0, sy, 0],
        [0, 1, 0, 0],
        [-sy,0, cy, 0],
        [0,0,0,1]
    ]
    Rz = [
        [cz, -sz, 0, 0],
        [sz, cz, 0, 0],
        [0, 0, 1, 0],
        [0,0,0,1]
    ]
    R = mat_mult(Rz, mat_mult(Ry, Rx))
    return R

def translation_matrix(tx, ty, tz):
    T = [
        [1,0,0,tx],
        [0,1,0,ty],
        [0,0,1,tz],
        [0,0,0,1]
    ]
    return T

# format like 0.1488f
def format_val(v):
    if abs(v) < 1e-7:
        v = 0.0
    s = f"{v:.6f}".rstrip('0').rstrip('.')
    if s == '' or s == '-':
        s = '0'
    return s + 'f'


def app():
    settings = read_json()

    if 'rotation' in settings and isinstance(settings['rotation'], dict):
        rx = float(settings['rotation'].get('X', 0))
        ry = float(settings['rotation'].get('Y', 0))
        rz = float(settings['rotation'].get('Z', 0))
    else:
        rx = float(settings.get('X', 0))
        ry = float(settings.get('Y', 0))
        rz = float(settings.get('Z', 0))

    rotate_around_center = settings.get('rotate_around_center', True)

    Original_art = IP.open(settings['file_path'])
    if (settings['image_resize'][0] != -1) and (settings['image_resize'][1] != -1):
        Original_art = Original_art.resize((settings['image_resize'][0], settings['image_resize'][1]))
    pixels = Original_art.load()
    x1, y1 = Original_art.size
    y, z, temp, commands_counter, art, top_count = (0, 0, 0, 0, [], ['', 0])
    colors = {}

    for item, color in settings['colors'].items():
        try:
            colors[item] = IC.getcolor(color, "RGB")
        except:
            colors[item] = tuple(color)

    # image to 2D list
    for i in range(y1):
        art.append([])
    for i in range(x1):
        for j in range(y1):
            art[j].append(rgb_to_minecraft(pixels[i, j][0],pixels[i, j][1],pixels[i, j][2], colors))
    art.reverse()

    # Optimizer 1
    for item in colors.keys():
        for i in range(len(art)):
            temp += art[i].count(item)
        if temp > top_count[1]:
            top_count[0] = item
            top_count[1] = temp
        temp = 0
    for i in range(len(art)):
        art[i] = list(map(lambda x: x.replace(top_count[0], 'null'), art[i]))

    pixel_size = settings["pixel_size"]

    def build_top_matrix():
        m = [
            [1.0/pixel_size, 0.0, 0.0, 0.002],
            [0.0, float(y1)/pixel_size, 0.0, 0.0],
            [0.0, 0.0, float(x1)/pixel_size, 0.0],
            [0.0,0.0,0.0,1.0]
        ]
        return m

    art_optimized = find_colored_areas(art) # Optimizer 2

    def build_opt_matrix(opt):
        start_x, start_y, end_x, end_y = opt[0], opt[1], opt[2], opt[3]
        size_y = abs((end_y - start_y) + 1)
        size_x = abs((end_x - start_x) + 1)
        m = [
            [1.0/pixel_size, 0.0, 0.0, 0.0],
            [0.0, (1.0/pixel_size) * size_y, 0.0, float(start_y)/pixel_size],
            [0.0, 0.0, (1.0/pixel_size) * size_x, float(start_x)/pixel_size],
            [0.0,0.0,0.0,1.0]
        ]
        return m

    matrices = []
    colors_for_matrices = []

    top_m = build_top_matrix()
    matrices.append(top_m)
    colors_for_matrices.append(top_count[0])

    for opt in art_optimized:
        matrices.append(build_opt_matrix(opt))
        colors_for_matrices.append(opt[4])

    translations = []
    for M in matrices:
        tx = M[0][3]
        ty = M[1][3]
        tz = M[2][3]
        translations.append((tx,ty,tz))
    if len(translations) == 0:
        center = (0.0, 0.0, 0.0)
    else:
        cx = sum(t[0] for t in translations) / len(translations)
        cy = sum(t[1] for t in translations) / len(translations)
        cz = sum(t[2] for t in translations) / len(translations)
        center = (cx, cy, cz)

    R = rotation_matrices_from_euler(rx, ry, rz)

    if rotate_around_center:
        T_minus = translation_matrix(-center[0], -center[1], -center[2])
        T_plus = translation_matrix(center[0], center[1], center[2])
        R_temp = mat_mult(R, T_minus)
        R_total = mat_mult(T_plus, R_temp)
    else:
        R_total = R

    rotated_matrices = [mat_mult(R_total, M) for M in matrices]

    commands = []
    maxlen = settings['max_length_command']
    current_cmd = 'summon block_display ~ ~ ~ {Passengers:['
    for idx, (M, color) in enumerate(zip(rotated_matrices, colors_for_matrices)):
        flat = flatten_mat_row_major(M)
        trans_str = ",".join(format_val(v) for v in flat)
        part = '{id:"minecraft:block_display",block_state:{Name:"' + color + '",Properties:{}},transformation:[' + trans_str + ']},'
        if (maxlen != -1) and (len(current_cmd) + len(part) >= maxlen):
            current_cmd += ']}'
            commands.append(current_cmd)
            current_cmd = 'summon block_display ~ ~ ~ {Passengers:[' + part
        else:
            current_cmd += part

    current_cmd += ']}'
    commands.append(current_cmd)

    # stats
    blocks_count = {}
    for color in colors_for_matrices:
        blocks_count[color] = blocks_count.get(color, 0) + 1

    blocks_count_sorted = sorted(blocks_count.items(), key=lambda x: x[1], reverse=True)
    for item, count in blocks_count_sorted:
        print(item.replace('minecraft:', '') + ': x' + str(count))

    if settings.get("write_to_file", False):
        if not os.path.exists('output'):
            os.makedirs('output')
        files = os.listdir('output')
        for file in files:
            file_path = os.path.join('output', file)
            if os.path.isfile(file_path):
                os.remove(file_path)

        for i in range(len(commands)):
            with open(f"output/message-{i}.txt", "w", encoding='utf8') as file:
                file.write(commands[i])

    if not settings.get('disable_window', False):
        for i in range(len(commands)):
            print(f'{i+1}/{len(commands)} command. Command pasted to your clipboard.')
            pyperclip.copy(commands[i])
            output = tk.Tk()
            editor = tk.Text()
            editor.pack(fill=tk.BOTH, expand=1)
            editor.insert("1.0", "Pasted to your clipboard")
            editor.insert(tk.END, f'\n{commands[i]}')
            output.mainloop()

if __name__ == "__main__":
    app()

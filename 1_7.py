from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import time
import random

# Game state
ball_pos = [0, 0, 20]
ball_radius = 10
ball_angle = 0
score = 0
game_over = False
camera_mode = "third_person"
camera_angle_h = 0  # Horizontal angle (left-right rotation)
camera_angle_v = 20  # Vertical angle (up-down tilt)

# lvl
current_level = 1
target_score = 3
level_complete = False

# Platform
platforms = []
platform_size = 100
platform_gap = 0

# Stars
stars = []

# UI button positions and state
button_size = 30
window_width, window_height = 800, 600  # Make sure your window size matches
paused = False  # Must be declared as global

gravity_velocity = 0
gravity = 0.5
jump_strength = 8

hazards = []
walls = []

paused = False

buttons = {
    'pause': {'x': 10, 'y': 560, 'w': 50, 'h': 30},
    'reset': {'x': 70, 'y': 560, 'w': 50, 'h': 30},
    'close': {'x': 130, 'y': 560, 'w': 50, 'h': 30},
}

# Arafat
tree_positions = [(random.randint(50, 750), random.randint(50, 150)) for _ in range(6)]

start_time = time.time()
cycle_duration = 50

def draw_circle(x, y, radius, segments=100):
    glBegin(GL_TRIANGLE_FAN)
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        glVertex2f(x + radius * math.cos(angle), y + radius * math.sin(angle))
    glEnd()

def draw_tree(x, y):
    # Trunk
    glColor3f(0.55, 0.27, 0.07)
    glBegin(GL_QUADS)
    glVertex2f(x - 5, y)
    glVertex2f(x + 5, y)
    glVertex2f(x + 5, y + 20)
    glVertex2f(x - 5, y + 20)
    glEnd()

    # Leaves
    glColor3f(0.0, 0.6, 0.0)
    draw_circle(x, y + 30, 15)

def draw_random_trees():
    for x, y in tree_positions:
        draw_tree(x, y)

def draw_scene():
    glClear(GL_COLOR_BUFFER_BIT)

    elapsed = (time.time() - start_time) % (2 * cycle_duration)
    is_day = elapsed > cycle_duration

    # Background
    if is_day:
        glClearColor(0.53, 0.81, 0.98, 1.0)  # Daytime
    else:
        glClearColor(0.05, 0.05, 0.2, 1.0)  # Night

    glClear(GL_COLOR_BUFFER_BIT)

    # Ground
    glColor3f(0.2, 0.8, 0.2)
    glBegin(GL_QUADS)
    glVertex2f(-1.0, -0.3)
    glVertex2f(1.0, -0.3)
    glVertex2f(1.0, -1.0)
    glVertex2f(-1.0, -1.0)
    glEnd()

    # Trees
    for x in [-0.8, -0.4, 0.0, 0.4, 0.8]:
        draw_tree(x * window_width / 2, -150)

    # Stars (only at night)
    if not is_day:
        glColor3f(1.0, 1.0, 1.0)
        for x, y in [(-0.7, 0.8), (0.2, 0.9), (0.6, 0.7), (-0.3, 0.6)]:
            draw_circle(x * window_width / 2, y * window_height / 2, 3)

    # Moon/Sun position
    t = (elapsed % cycle_duration) / cycle_duration
    x_pos = 0  # Center of the screen
    y_pos = window_height / 2 + t * (window_height + 60)  # Start at top, drop past bottom


    if is_day:
        glColor3f(1.0, 1.0, 0.0)  # Sun - yellow
    else:
        glColor3f(1.0, 1.0, 1.0)  # Moon - white

    draw_circle(x_pos, y_pos, 30)


def generate_path():
    path = []
    x, y = 0, 0
    for i in range(200):
        path.append([x, y])
        direction = random.choice(['straight', 'left', 'right'])
        if direction == 'left':
            x -= platform_size
        elif direction == 'right':
            x += platform_size
        else:
            y += platform_size
    return path


def draw_hazards():
    for hazard in hazards:
        glPushMatrix()
        glTranslatef(hazard['x'], hazard['y'], hazard['z'])
        if hazard['type'] == 'static':
            glColor3f(1, 0, 0)
            glutSolidCone(5, 20, 10, 2)
        elif hazard['type'] == 'swinging':
            glRotatef(math.sin(hazard['angle']) * 45, 0, 0, 1)
            glColor3f(1, 0.5, 0)
            glTranslatef(15, 0, 0)
            glScalef(2, 10, 2)
            glutSolidCube(1)
        glPopMatrix()

def update_hazards():
    for h in hazards:
        h[0] += h[3] * hazard_move_speed
        if abs(h[0])>platform_width*2: h[3]*=-1
        h[1] -= ball_speed*50
        if h[1] < ball_pos[1] - platform_length:
            px,py = random.choice(platforms)
            h[:] = [px,py,hazard_elevation, random.choice([-1,1])]

def check_hazard_collision():
    global game_over
    for h in hazards:
        hx, hy, hz = h['x'], h['y'], h['z']
        dist = math.sqrt((ball_pos[0]-hx)**2 + (ball_pos[1]-hy)**2 + (ball_pos[2]-hz)**2)
        if dist < ball_radius + 5:
            game_over = True

def draw_2d_buttons():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

    margin = 10; spacing = 10
    x_term    = window_width  - margin - button_size
    x_pause   = x_term        - spacing - button_size
    x_restart = x_pause       - spacing - button_size
    y = window_height - margin - button_size

    # Terminate (Close) Button (X)
    glColor3f(1,0,0); glLineWidth(5)
    glBegin(GL_LINES)
    glVertex2f(x_term, y); glVertex2f(x_term+button_size, y+button_size)
    glVertex2f(x_term+button_size, y); glVertex2f(x_term, y+button_size)
    glEnd()

    # Pause/Resume Button (|| or ▶)
    glColor3f(1,1,1)
    if not paused:
        gap = button_size * 0.2
        w = (button_size - gap) / 2
        glBegin(GL_QUADS)
        glVertex2f(x_pause, y); glVertex2f(x_pause + w, y)
        glVertex2f(x_pause + w, y + button_size); glVertex2f(x_pause, y + button_size)
        glVertex2f(x_pause + w + gap, y); glVertex2f(x_pause + 2 * w + gap, y)
        glVertex2f(x_pause + 2 * w + gap, y + button_size); glVertex2f(x_pause + w + gap, y + button_size)
        glEnd()
    else:
        glBegin(GL_TRIANGLES)
        glVertex2f(x_pause, y); glVertex2f(x_pause, y + button_size)
        glVertex2f(x_pause + button_size, y + button_size / 2)
        glEnd()

    # Restart Button (↺)
    glColor3f(1,1,1); glLineWidth(5)
    glBegin(GL_LINES)
    glVertex2f(x_restart+button_size, y+button_size/2); glVertex2f(x_restart, y+button_size/2)
    glVertex2f(x_restart, y+button_size/2); glVertex2f(x_restart+button_size/3, y+button_size)
    glVertex2f(x_restart, y+button_size/2); glVertex2f(x_restart+button_size/3, y)
    glEnd()

    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

def mouse_click(button, state, x, y):
    global paused
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN:
        oy = window_height - y
        margin = 10; spacing = 10
        x_term = window_width - margin - button_size
        x_pause = x_term - spacing - button_size
        x_restart = x_pause - spacing - button_size
        y0 = window_height - margin - button_size

        # Close button
        if x_term <= x <= x_term + button_size and y0 <= oy <= y0 + button_size:
            os._exit(0)

        # Pause button
        if x_pause <= x <= x_pause + button_size and y0 <= oy <= y0 + button_size:
            paused = not paused
            glutPostRedisplay()

        # Reset button
        if x_restart <= x <= x_restart + button_size and y0 <= oy <= y0 + button_size:
            reset_game()
            glutPostRedisplay()

        if level_complete and 350 <= x <= 450 and (window_height - y) >= 200 and (window_height - y) <= 240:
            advance_to_next_level()

def advance_to_next_level():
    global current_level, target_score, score, level_complete
    current_level += 1
    target_score += 5
    score = 0
    level_complete = False
    reset_game()

def draw_walls():
    glColor3f(1, 0, 0)
    for wall in walls:
        glPushMatrix()
        glTranslatef(wall['x'], wall['y'], wall['z'])
        glScalef(20, 5, 40)  # Width, depth, height of the wall
        glutSolidCube(1)
        glPopMatrix()

def check_wall_collision():
    global game_over
    for wall in walls:
        wx, wy, wz = wall['x'], wall['y'], wall['z']
        dist = math.sqrt((ball_pos[0] - wx)**2 + (ball_pos[1] - wy)**2 + (ball_pos[2] - wz)**2)
        if dist < ball_radius + 10:  # Adjusted collision margin
            game_over = True

def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(1, 1, 1)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

def draw_platforms():
    for plat in platforms:
        px, py = plat
        glPushMatrix()
        glTranslatef(px, py, 0)
        glColor3f(0.4, 0.3, 0.2)
        glScalef(platform_size, platform_size, 10)
        glutSolidCube(1)
        glPopMatrix()

def draw_ball():
    glPushMatrix()
    glTranslatef(ball_pos[0], ball_pos[1], ball_pos[2])
    glColor3f(0.1, 0.6, 1.0)
    glutSolidSphere(ball_radius, 20, 20)
    glPopMatrix()

def draw_stars():
    glColor3f(1, 1, 0)
    for s in stars:
        glPushMatrix()
        glTranslatef(s[0], s[1], s[2])
        glutSolidSphere(5, 10, 10)
        glPopMatrix()

def is_on_platform():
    for plat in platforms:
        px, py = plat
        if abs(ball_pos[0] - px) < platform_size / 2 and abs(ball_pos[1] - py) < platform_size / 2:
            return True
    return False

def jump():
    global ball_pos
    if game_over:
        return
    jump_distance = platform_size + platform_gap
    ball_pos[1] += jump_distance

def check_star_collision():
    global score, stars, level_complete
    new_stars = []
    collected = False
    for s in stars:
        distance = math.sqrt((ball_pos[0] - s[0])**2 + (ball_pos[1] - s[1])**2 + (ball_pos[2] - s[2])**2)
        if distance < ball_radius + 1:
            score += 1
            collected = True
        else:
            new_stars.append(s)
    stars = new_stars
    if collected:
        new_star_x, new_star_y = random.choice(platforms)
        stars.append([new_star_x, new_star_y, 30])
    if score >= target_score:
        level_complete = True

def draw_level_complete_screen():
    draw_text(300, 300, f"Level {current_level} Complete!", GLUT_BITMAP_HELVETICA_18)
    draw_text(280, 260, "Click to go to the next episode", GLUT_BITMAP_HELVETICA_12)

    # Draw a button
    glColor3f(0, 0.5, 1)
    glBegin(GL_QUADS)
    glVertex2f(350, 200)
    glVertex2f(450, 200)
    glVertex2f(450, 240)
    glVertex2f(350, 240)
    glEnd()

    glColor3f(1, 1, 1)
    draw_text(370, 215, "Next", GLUT_BITMAP_HELVETICA_18)

def keyboardListener(key, x, y):
    global ball_pos, game_over, camera_mode
    if game_over and key == b'r':
        reset_game()
        return
    step = 5
    if key == b'a':
        ball_pos[0] -= step
    elif key == b'd':
        ball_pos[0] += step
    elif key == b'w':
        ball_pos[1] += step
    elif key == b's':
        ball_pos[1] -= step
    elif key == b' ':
        jump()
    elif key == b'c':
        camera_mode = "first_person" if camera_mode == "third_person" else "third_person"

def specialKeyboardListener(key, x, y):
    global camera_angle_h, camera_angle_v
    angle_step = 5
    if camera_mode == "third_person":
        if key == GLUT_KEY_LEFT:
            camera_angle_h -= angle_step
        elif key == GLUT_KEY_RIGHT:
            camera_angle_h += angle_step
        elif key == GLUT_KEY_UP:
            camera_angle_v = min(85, camera_angle_v + angle_step)
        elif key == GLUT_KEY_DOWN:
            camera_angle_v = max(5, camera_angle_v - angle_step)

def reshape(width, height):
    if height == 0:
        height = 1
    glViewport(0, 0, width, height)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, width / height, 1, 1000)
    glMatrixMode(GL_MODELVIEW)

def idle():
    global ball_pos, game_over
    if paused or game_over:
        glutPostRedisplay()
        return
    if not is_on_platform():
        ball_pos[2] -= 1
        if ball_pos[2] < -50:
            game_over = True
    else:
        ball_pos[2] = 20

    check_star_collision()
    check_hazard_collision()
    check_wall_collision()
    glutPostRedisplay()

def reset_game():
    global ball_pos, ball_angle, score, game_over, platforms, stars, hazards
    ball_pos = [0, 0, 20]
    ball_angle = 0
    score = 0
    game_over = False
    platforms.clear()
    platforms.extend(generate_path())
    stars.clear()
    hazards.clear()
    for _ in range(5):
        x, y = random.choice(platforms)
        stars.append([x, y, 30])
    for _ in range(15):  # Add 10 hazards
        x, y = random.choice(platforms)
        if random.random() > 0.5:
            hazards.append({'type': 'static', 'x': x, 'y': y, 'z': 30})
        else:
            angle = random.uniform(0, 360)
            hazards.append({'type': 'swinging', 'x': x, 'y': y, 'z': 50, 'angle': angle})
    walls.clear()
    for _ in range(10):  # You can adjust the number of walls
        x, y = random.choice(platforms)
        walls.append({'x': x, 'y': y, 'z': 25})

def showScreen():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    # Compute time-based day/night
    elapsed = (time.time() - start_time) % (2 * cycle_duration)
    is_day = elapsed > cycle_duration

    # Set background color
    if is_day:
        glClearColor(0.53, 0.81, 0.98, 1.0)  # Daytime
    else:
        glClearColor(0.05, 0.05, 0.2, 1.0)  # Night

    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    # Draw sun or moon using 2D overlay
    glDisable(GL_DEPTH_TEST)  # Disable depth testing for overlay
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 800, 0, 600)
    glColor3f(0.0, 0.3, 0.0)
    glBegin(GL_QUADS)
    glVertex2f(0, 0)
    glVertex2f(800, 0)
    glVertex2f(800, 300)
    glVertex2f(0, 300)
    glEnd()
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    draw_random_trees()
    t = (elapsed % cycle_duration) / cycle_duration
    y_pos = (1 - abs(2 * t - 1)) * 250 + 350
    x_pos = (2 * t - 1) * 350 + 400

    if level_complete:
        draw_level_complete_screen()

    if is_day:
        glColor3f(1.0, 1.0, 0.0)
    else:
        glColor3f(1.0, 1.0, 1.0)
    draw_circle(x_pos, y_pos, 30)

    if not is_day:
        glColor3f(1.0, 1.0, 1.0)
        for sx, sy in [(100, 500), (600, 550), (400, 480), (200, 530)]:
            draw_circle(sx, sy, 2)
    # Draw horizon line at y = 350
    glColor3f(255, 255, 255)
    glBegin(GL_LINES)
    glVertex2f(0, 300)
    glVertex2f(800, 300)
    glEnd()

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)   # Re-enable depth testing

    if camera_mode == "third_person":
        distance = 300
        rad_h = math.radians(camera_angle_h)
        rad_v = math.radians(camera_angle_v)
        cam_x = ball_pos[0] + distance * math.cos(rad_v) * math.sin(rad_h)
        cam_y = ball_pos[1] - distance * math.cos(rad_v) * math.cos(rad_h)
        cam_z = ball_pos[2] + distance * math.sin(rad_v)
        gluLookAt(cam_x, cam_y, cam_z, ball_pos[0], ball_pos[1], ball_pos[2], 0, 0, 1)

    else:
        gluLookAt(ball_pos[0], ball_pos[1] - 5, ball_pos[2] + 15,
                  ball_pos[0], ball_pos[1] + 50, ball_pos[2] + 10,
                  0, 0, 1)

    draw_platforms()
    draw_ball()
    draw_stars()
    draw_hazards()
    draw_walls()
    draw_2d_buttons()

    draw_text(10, 580, f"Score: {score}")
    if game_over:
        draw_text(300, 300, "Game Over! Press R to Restart")
        draw_text(400, 250, f"You scored: {score} in level {level_complete}.")
    glutSwapBuffers()

def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(800, 600)
    glutCreateWindow(b"3D Crystal Run game")
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.5, 0.8, 0.5, 1.0)
    glutDisplayFunc(showScreen)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyboardListener)
    glutMouseFunc(mouse_click)
    glutIdleFunc(idle)
    glutReshapeFunc(reshape)
    reset_game()
    glutMainLoop()

if __name__ == "__main__":
    main()
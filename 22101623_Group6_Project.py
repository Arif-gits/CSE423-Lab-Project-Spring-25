from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import numpy as np
import sys
import os

ball_radius = 5        # ball size
lateral_step = 5       # movement step
ball_speed = 0.0002    # forward speed
speed_increment = 0.00000005
star_speed_bonus = 0.0001
star_frequency = 30
star_move_speed = 1
platform_length = 60
platform_width = 8
platform_thickness = 1

pause_button = (0, 0, 0, 0)
reset_button = (0, 0, 0, 0)
close_button = (0, 0, 0, 0)
paused = False

hazard_frequency = 20
hazard_move_speed = 1
hazard_size = 6
static_obstacle_frequency = 15
static_obstacle_width = 8
static_obstacle_height = 10

# -- Physics --
gravity = 0.5
vertical_speed = 0.0
jump_speed = 15.0
ground_epsilon = 1.0
jump_buffer = False

CELL_SIZE = 50

ball_pos = [0.0, 0.0, 0.0]
score = 0
game_over = False
paused = False

camera_mode = "third_person"
camera_angle_h = 0
camera_angle_v = 20
camera_pos = [0.0, -30.0, 15.0]

platforms = []
stars = []
hazards = []
static_obstacles = []

grid = {}

button_size = 30
window_width, window_height = 800, 600

def aabb_collision(ax, ay, aw, ah, bx, by, bw, bh):
    return (ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by)

def grid_key(x, y):
    return (int(x // CELL_SIZE), int(y // CELL_SIZE))

def insert_entity(grid, entity, key_func):
    key = key_func(entity)
    grid.setdefault(key, []).append(entity)

def query_neighbors(grid, x, y):
    kx, ky = grid_key(x, y)
    entities = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            entities.extend(grid.get((kx+dx, ky+dy), []))
    return entities

def generate_raw_path():
    pts = [(0.0, 0.0)]
    x, y = 0.0, 0.0
    for i in range(60):
        dir = random.choices(['straight','left','right'], weights=[2,5,5])[0]
        if dir == 'left': x -= platform_width * 4
        elif dir == 'right': x += platform_width * 4
        y += platform_length * 4
        pts.append((x, y))
    return pts

def catmull_rom_spline(P0, P1, P2, P3, n_points=8):
    alpha = 0.5
    def tj(ti, Pi, Pj):
        d = math.hypot(Pj[0]-Pi[0], Pj[1]-Pi[1])
        return ti + (d**alpha if d>1e-6 else 1e-6)
    t0 = 0.0; t1 = tj(t0, P0, P1); t2 = tj(t1, P1, P2); t3 = tj(t2, P2, P3)
    t = np.linspace(t1, t2, n_points).reshape(n_points,1)
    P0_arr, P1_arr, P2_arr, P3_arr = map(np.array, (P0, P1, P2, P3))
    A1 = (t1 - t)/(t1 - t0)*P0_arr + (t - t0)/(t1 - t0)*P1_arr
    A2 = (t2 - t)/(t2 - t1)*P1_arr + (t - t1)/(t2 - t1)*P2_arr
    A3 = (t3 - t)/(t3 - t2)*P2_arr + (t - t2)/(t3 - t2)*P3_arr
    B1 = (t2 - t)/(t2 - t0)*A1 + (t - t0)/(t2 - t0)*A2
    B2 = (t3 - t)/(t3 - t1)*A2 + (t - t1)/(t3 - t1)*A3
    C  = (t2 - t)/(t2 - t1)*B1 + (t - t1)/(t2 - t1)*B2
    return [tuple(pt) for pt in C]

def generate_path():
    raw = generate_raw_path()
    pts = [raw[0]] + raw + [raw[-1]]
    smooth = []
    for i in range(len(pts) - 3):
        smooth += catmull_rom_spline(pts[i], pts[i+1], pts[i+2], pts[i+3])
    return smooth

def reset_game():
    global ball_pos, score, game_over, platforms, stars, hazards, static_obstacles, ball_speed, vertical_speed, grid, jump_buffer, paused
    ball_pos = [0.0, 0.0, ball_radius + platform_thickness/2]
    vertical_speed = 0.0; score = 0; game_over = False; ball_speed = 0.0002; jump_buffer = False; paused = False
    platforms = generate_path()

    stars = []
    for i in range(star_frequency):
        px, py = random.choice(platforms)
        stars.append({'pos':[px,py,ball_radius+platform_thickness/2], 'dir':random.choice([-1,1]), 'size':7, 'origin':[px,py]})

    hazards = []
    for _ in range(hazard_frequency):
        px, py = random.choice(platforms)
        hazards.append({'pos':[px,py,hazard_size/2+platform_thickness/2], 'dir':random.choice([-1,1]), 'size':hazard_size})

    static_obstacles = []
    for _ in range(static_obstacle_frequency):
        px, py = random.choice(platforms)
        static_obstacles.append({'pos':[px,py,platform_thickness/2+static_obstacle_height/2]})

    grid = {}
    for pt in platforms:
        insert_entity(grid, pt, lambda p: grid_key(p[0], p[1]))
    for e in stars + hazards + static_obstacles:
        insert_entity(grid, e, lambda ent: grid_key(ent['pos'][0], ent['pos'][1]))

def draw_shadows():
    glDisable(GL_LIGHTING)
    glDepthMask(False)
    glColor4f(0.0, 0.0, 0.0, 0.5)
    L = (100.0, 100.0, 200.0, 1.0)
    shadow_mat = [ L[2], 0, 0, 0,
                   0, L[2], 0, 0,
                  -L[0],-L[1],0,-L[3],
                   0, 0, 0, L[2] ]
    glPushMatrix()
    glMultMatrixf(shadow_mat)

    glPushMatrix()
    glTranslatef(*ball_pos)
    glutSolidSphere(ball_radius, 20, 20)
    glPopMatrix()

    for e in hazards:
        hx,hy,hz = e['pos']
        glPushMatrix()
        glTranslatef(hx, hy, hz)
        glutSolidCube(e['size'])
        glPopMatrix()

    glPopMatrix()
    glDepthMask(True)
    glEnable(GL_LIGHTING)


def draw_platforms():
    glColor3f(0.4,0.3,0.2)
    for px, py in platforms:
        glPushMatrix(); glTranslatef(px,py,0)
        glScalef(platform_width, platform_length, platform_thickness)
        glNormal3f(0,0,1)
        glutSolidCube(1); glPopMatrix()

def draw_connectors():
    glColor3f(0.4,0.3,0.2)
    for i in range(len(platforms)-1):
        x1,y1 = platforms[i]; x2,y2 = platforms[i+1]
        dx,dy = x2-x1, y2-y1; dist = math.hypot(dx,dy)
        if dist <= platform_length * 1.1:
            glPushMatrix(); glTranslatef((x1+x2)/2,(y1+y2)/2,0)
            glRotatef(math.degrees(math.atan2(dy,dx)),0,0,1)
            glScalef(platform_width, dist, platform_thickness)
            glNormal3f(0,0,1)
            glutSolidCube(1); glPopMatrix()

def draw_stars():
    glColor3f(1,1,0)
    for e in stars:
        sx,sy,sz = e['pos']
        glPushMatrix(); glTranslatef(sx,sy,sz)
        glRotatef(-camera_angle_h,0,0,1); glRotatef(camera_angle_v,1,0,0)
        draw_rhombus(); glPopMatrix()

def draw_hazards():
    glColor3f(1,0,0)
    for e in hazards:
        hx,hy,hz = e['pos']
        glPushMatrix(); glTranslatef(hx,hy,hz)
        glScalef(e['size'], e['size'], e['size'])
        glNormal3f(0,0,1)
        glutSolidCube(1); glPopMatrix()

def draw_static_obstacles():
    glColor3f(0,1,0)
    for e in static_obstacles:
        ox,oy,oz = e['pos']
        glPushMatrix(); glTranslatef(ox,oy,oz)
        glScalef(static_obstacle_width, static_obstacle_width, static_obstacle_height)
        glNormal3f(0,0,1)
        glutSolidCube(1); glPopMatrix()

def draw_rhombus():
    s=7; glBegin(GL_POLYGON)
    glVertex3f( s,0,0); glVertex3f(0,s,0)
    glVertex3f(-s,0,0); glVertex3f(0,-s,0)
    glEnd()

def draw_2d_buttons():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

    margin = 10; spacing = 10
    x_term    = window_width  - margin - button_size
    x_pause   = x_term        - spacing - button_size
    x_restart = x_pause       - spacing - button_size
    y = window_height - margin - button_size

    glColor3f(1,0,0); glLineWidth(5)
    glBegin(GL_LINES)
    glVertex2f(x_term, y); glVertex2f(x_term+button_size, y+button_size)
    glVertex2f(x_term+button_size, y); glVertex2f(x_term, y+button_size)
    glEnd()

    glColor3f(1,1,1)
    if not paused:
        gap = button_size*0.2; w=(button_size-gap)/2
        glBegin(GL_QUADS)
        glVertex2f(x_pause, y); glVertex2f(x_pause+w, y)
        glVertex2f(x_pause+w, y+button_size); glVertex2f(x_pause, y+button_size)
        glVertex2f(x_pause+w+gap, y); glVertex2f(x_pause+2*w+gap, y)
        glVertex2f(x_pause+2*w+gap, y+button_size); glVertex2f(x_pause+w+gap, y+button_size)
        glEnd()
    else:
        glBegin(GL_TRIANGLES)
        glVertex2f(x_pause, y); glVertex2f(x_pause, y+button_size)
        glVertex2f(x_pause+button_size, y+button_size/2)
        glEnd()

    # Restart
    glColor3f(1,1,1); glLineWidth(5)
    glBegin(GL_LINES)
    glVertex2f(x_restart+button_size, y+button_size/2); glVertex2f(x_restart, y+button_size/2)
    glVertex2f(x_restart, y+button_size/2); glVertex2f(x_restart+button_size/3, y+button_size)
    glVertex2f(x_restart, y+button_size/2); glVertex2f(x_restart+button_size/3, y)
    glEnd()

    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

def mouse_click(button, state, x, y):
    global paused
    if button==GLUT_LEFT_BUTTON and state==GLUT_DOWN:
        oy=window_height-y
        margin=10; spacing=10
        x_term=window_width-margin-button_size
        x_pause=x_term-spacing-button_size
        x_restart=x_pause-spacing-button_size
        y0=window_height-margin-button_size
        if x_term<=x<=x_term+button_size and y0<=oy<=y0+button_size: os._exit(0)
        if x_pause<=x<=x_pause+button_size and y0<=oy<=y0+button_size:
            paused=not paused; glutPostRedisplay()
        if x_restart<=x<=x_restart+button_size and y0<=oy<=y0+button_size:
            reset_game(); glutPostRedisplay()

def orig_idle():
    global game_over, ball_speed, vertical_speed
    if game_over: return
    ball_pos[1] += ball_speed; ball_speed += speed_increment
    update_stars(); update_hazards()
    vertical_speed -= gravity; ball_pos[2] += vertical_speed
    if is_on_platform() and ball_pos[2] < ball_radius+platform_thickness/2:
        ball_pos[2] = ball_radius+platform_thickness/2; vertical_speed = 0.0
    if ball_pos[2] < -50: game_over = True
    for e in static_obstacles:
        dx,dy = ball_pos[0]-e['pos'][0], ball_pos[1]-e['pos'][1]
        if abs(dx)<=static_obstacle_width/2 and abs(dy)<=static_obstacle_width/2 and ball_pos[2]<e['pos'][2]+static_obstacle_height/2:
            game_over = True
    check_star_collision(); check_hazard_collision(); glutPostRedisplay()

def idle():
    if not (game_over or paused): orig_idle()
    else: glutPostRedisplay()

def is_on_platform():
    bx, by = ball_pos[0], ball_pos[1]
    for entity in query_neighbors(grid, bx, by):
        if isinstance(entity, tuple):
            px, py = entity
            if abs(bx-px) < platform_width/2 and abs(by-py) < platform_length/2:
                return True
    return False

def update_stars():
    bounce_range = platform_width * 2
    for e in stars:
        e['pos'][0] += e['dir'] * star_move_speed
        if abs(e['pos'][0] - e['origin'][0]) > bounce_range:
            e['dir'] *= -1
        e['pos'][1] -= ball_speed * 50
        if e['pos'][1] < ball_pos[1] - platform_length:
            px, py = random.choice(platforms)
            e['origin'], e['pos'] = [px, py], [px, py, ball_radius+platform_thickness/2]

def update_hazards():
    for e in hazards:
        e['pos'][0] += e['dir'] * hazard_move_speed
        if abs(e['pos'][0]) > platform_width*2: e['dir'] *= -1
        e['pos'][1] -= ball_speed * 50
        if e['pos'][1] < ball_pos[1] - platform_length:
            px, py = random.choice(platforms)
            e['pos'] = [px,py,hazard_size/2+platform_thickness/2]

def check_star_collision():
    global score, ball_speed
    bx, by = ball_pos[0], ball_pos[1]
    for e in stars:
        sx, sy, sz = e['pos']; s = e['size']
        if aabb_collision(bx-ball_radius, by-ball_radius, 2*ball_radius, 2*ball_radius,
                          sx-s/2, sy-s/2, s, s):
            score += 1; ball_speed += star_speed_bonus
            px, py = random.choice(platforms)
            e['origin'], e['pos'] = [px, py], [px, py, ball_radius+platform_thickness/2]
            break

def check_hazard_collision():
    global game_over
    bx, by = ball_pos[0], ball_pos[1]
    for e in hazards:
        hx, hy, hz = e['pos']; h = e['size']
        if aabb_collision(bx-ball_radius, by-ball_radius, 2*ball_radius, 2*ball_radius,
                          hx-h/2, hy-h/2, h, h):
            game_over = True
            return

def set_camera():
    glLoadIdentity()
    if camera_mode=="first_person":
        target=[ball_pos[0],ball_pos[1]-30,ball_pos[2]+15]
        for i in range(3): camera_pos[i]+=0.1*(target[i]-camera_pos[i])
        gluLookAt(*camera_pos, ball_pos[0],ball_pos[1]+50,ball_pos[2],0,0,1)
    else:
        r=200
        ex=ball_pos[0]+r*math.sin(math.radians(camera_angle_h))*math.cos(math.radians(camera_angle_v))
        ey=ball_pos[1]-r*math.cos(math.radians(camera_angle_h))*math.cos(math.radians(camera_angle_v))
        ez=ball_pos[2]+r*math.sin(math.radians(camera_angle_v))
        gluLookAt(ex,ey,ez,ball_pos[0],ball_pos[1],ball_pos[2],0,0,1)

def display():
    glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
    set_camera()
    draw_shadows()
    draw_platforms(); draw_connectors(); draw_stars(); draw_hazards(); draw_static_obstacles()
    glPushMatrix()
    glTranslatef(*ball_pos)
    glColor3f(0,1,1)
    glutSolidSphere(ball_radius,20,20)
    glPopMatrix()

    glDisable(GL_LIGHTING)
    glDisable(GL_DEPTH_TEST)
    glColor3f(1.0, 1.0, 1.0)
    if game_over:
        draw_text(window_width/2 - 80, window_height/2, "Game Over. Press R to Restart")
    else:
        draw_text(10, window_height - 30, f"Score: {score}")
    glEnable(GL_LIGHTING)
    glEnable(GL_DEPTH_TEST)

    draw_2d_buttons()
    glutSwapBuffers()

def draw_text(x, y, text):
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, window_width, 0, window_height)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glColor3f(0,0,1); glRasterPos2f(x,y)
    for ch in text: glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

def reshape(w, h):
    global window_width, window_height
    window_width, window_height = w, max(h,1)
    glViewport(0,0,w,window_height)
    glMatrixMode(GL_PROJECTION); glLoadIdentity(); gluPerspective(45, w/float(window_height),1,1000)
    glMatrixMode(GL_MODELVIEW)

def keyboardListener(key, x, y):
    global game_over, camera_mode, vertical_speed, jump_buffer
    if game_over and key==b'r': reset_game(); return
    if key==b'a': ball_pos[0]-=lateral_step; clamp_within_platform()
    elif key==b'd': ball_pos[0]+=lateral_step; clamp_within_platform()
    elif key==b'w': ball_pos[1]+=lateral_step
    elif key==b's': ball_pos[1]-=lateral_step
    elif key==b' ' and is_on_platform(): vertical_speed=jump_speed
    elif key==b'c': camera_mode = "first_person" if camera_mode=="third_person" else "third_person"

def specialKeyboardListener(key, x, y):
    global camera_angle_h, camera_angle_v
    if camera_mode=="third_person":
        if key==GLUT_KEY_LEFT: camera_angle_h-=5
        elif key==GLUT_KEY_RIGHT: camera_angle_h+=5
        elif key==GLUT_KEY_UP: camera_angle_v=min(camera_angle_v+5,85)
        elif key==GLUT_KEY_DOWN: camera_angle_v=max(camera_angle_v-5,5)

def clamp_within_platform():
    for px, py in platforms:
        if abs(ball_pos[0]-px)<platform_width/2 and abs(ball_pos[1]-py)<platform_length/2:
            ball_pos[0]=max(min(ball_pos[0],px+platform_width/2),px-platform_width/2)
            return

# -- Main Entry --
def main():
    glutInit(); glutInitDisplayMode(GLUT_DOUBLE|GLUT_RGB|GLUT_DEPTH)
    glutInitWindowSize(window_width,window_height); glutCreateWindow(b"Bullet Frenzy with Lighting & Shadows")
    glClearColor(0.1,0.1,0.1,1)

    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.2,0.2,0.2,1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  (0.8,0.8,0.8,1.0))
    glLightfv(GL_LIGHT0, GL_SPECULAR, (1.0,1.0,1.0,1.0))
    glLightfv(GL_LIGHT0, GL_POSITION, (100.0,100.0,200.0,1.0))
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, (1.0,1.0,1.0,1.0))
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 50.0)

    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyboardListener)
    glutMouseFunc(mouse_click)
    glutIdleFunc(idle)

    reset_game()
    glutMainLoop()

if __name__=='__main__':
    main()

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
import random

class MagneticVehicleSimulation:
    def __init__(self):
        pygame.init()
        self.display = (800, 600)
        pygame.display.set_mode(self.display, DOUBLEBUF | OPENGL)
        pygame.display.set_caption("3D Anti-Gravity Vehicle Simulation (ZPE & Plasma)")

        # OpenGL setup
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.1, 0.1, 0.2, 1.0)
        gluPerspective(45, (self.display[0] / self.display[1]), 0.1, 5000.0)

        # Simulation parameters
        self.vehicle_mass = 1.0  # kg
        self.vehicle_pos = np.array([400.0, 50.0, 0.0])  # Initial position (x, y, z)
        self.vehicle_vel = np.array([0.0, 0.0, 0.0])  # Initial velocity
        self.gravity = 9.81  # m/s^2
        self.gravity_reduced = False
        self.dt = 0.01  # Time step
        self.magnetic_strength = 1000.0
        self.friction_coeff = 0.1
        self.ground_y = 0.0
        self.field_up_active = False
        self.field_down_active = False
        self.field_right_active = False
        self.field_left_active = False
        self.field_forward_active = False
        self.field_backward_active = False
        self.payload_active = False
        self.external_field = np.array([0.0, 0.0, 5e-3])  # 0.005 T
        self.pid_kp = 10.0
        self.plasma_pulse = 0.3  # Base plasma glow opacity
        self.energy_used = 0.0  # Total energy (J)
        self.plasma_energy = 0.0  # Plasma contribution (W)

        # Camera parameters
        self.camera_distance = 300
        self.camera_height = 150

        # Font for text overlay
        try:
            self.font = pygame.font.SysFont("arial", 16, bold=True)
        except Exception as e:
            print(f"Font loading error: {e}")
            self.font = pygame.font.Font(None, 24)  # Fallback font

        # Clock for timing
        self.clock = pygame.time.Clock()

    def format_power(self, power):
        """Format power in W, kW, or MW for readability."""
        if power < 1000:
            return f"{power:.0f} W"
        elif power < 1000000:
            return f"{power/1000:.2f} kW"
        else:
            return f"{power/1000000:.2f} MW"

    def format_energy(self, energy):
        """Format energy in J, kJ, or MJ for readability."""
        if energy < 1000:
            return f"{energy:.0f} J"
        elif energy < 1000000:
            return f"{energy/1000:.2f} kJ"
        else:
            return f"{energy/1000000:.2f} MJ"

    def reset(self):
        self.vehicle_pos = np.array([400.0, 50.0, 0.0])
        self.vehicle_vel = np.array([0.0, 0.0, 0.0])
        self.magnetic_strength = 1000.0
        self.payload_active = False
        self.gravity_reduced = False
        self.energy_used = 0.0
        self.plasma_energy = 0.0

    def draw_sphere(self, pos, radius=20):
        glPushMatrix()
        glTranslatef(pos[0], pos[1], pos[2])
        glColor3f(1.0, 0.0, 0.0)
        quad = gluNewQuadric()
        gluSphere(quad, radius, 20, 20)
        pulse = self.plasma_pulse + 0.1 * (any([self.field_up_active, self.field_down_active,
                                                self.field_right_active, self.field_left_active,
                                                self.field_forward_active, self.field_backward_active]))
        glColor4f(0.0, 0.5, 1.0, pulse + 0.05 * random.random())
        gluSphere(quad, radius + 5, 20, 20)
        gluDeleteQuadric(quad)
        glPopMatrix()

    def draw_warp_lines(self):
        if self.gravity_reduced:
            glColor4f(0.5, 0.5, 1.0, 0.2 + 0.1 * random.random())
            glLineWidth(2)
            glBegin(GL_LINES)
            for i in range(-3, 4):
                offset = i * 8
                glVertex3f(self.vehicle_pos[0] + offset, self.vehicle_pos[1], self.vehicle_pos[2] - 25)
                glVertex3f(self.vehicle_pos[0] + offset, self.vehicle_pos[1], self.vehicle_pos[2] + 25)
            glEnd()

    def draw_ground(self):
        glBegin(GL_QUADS)
        glColor3f(0.0, 0.0, 0.5)
        glVertex3f(0, self.ground_y, -1000)
        glVertex3f(800, self.ground_y, -1000)
        glVertex3f(800, self.ground_y, 1000)
        glVertex3f(0, self.ground_y, 1000)
        glEnd()
        glColor3f(0.4, 0.4, 0.4)
        glLineWidth(1)
        glBegin(GL_LINES)
        for x in range(0, 801, 50):
            glVertex3f(x, self.ground_y, -1000)
            glVertex3f(x, self.ground_y, 1000)
        for z in range(-1000, 1001, 50):
            glVertex3f(0, self.ground_y, z)
            glVertex3f(800, self.ground_y, z)
        glEnd()

    def draw_skybox(self):
        glColor3f(0.2, 0.2, 0.3)
        glLineWidth(1)
        glBegin(GL_LINES)
        glVertex3f(0, self.ground_y, -1000); glVertex3f(800, self.ground_y, -1000)
        glVertex3f(800, self.ground_y, -1000); glVertex3f(800, 600, -1000)
        glVertex3f(800, 600, -1000); glVertex3f(0, 600, -1000)
        glVertex3f(0, 600, -1000); glVertex3f(0, self.ground_y, -1000)
        glVertex3f(0, self.ground_y, 1000); glVertex3f(800, self.ground_y, 1000)
        glVertex3f(800, self.ground_y, 1000); glVertex3f(800, 600, 1000)
        glVertex3f(800, 600, 1000); glVertex3f(0, 600, 1000)
        glVertex3f(0, 600, 1000); glVertex3f(0, self.ground_y, 1000)
        glEnd()

    def draw_field_arrows(self):
        arrow_length = 30
        glLineWidth(5)
        glBegin(GL_LINES)
        if self.field_up_active:
            glColor3f(0.0, 1.0, 0.0)
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2])
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1] + arrow_length, self.vehicle_pos[2])
        if self.field_down_active:
            glColor3f(1.0, 0.5, 0.0)
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2])
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1] - arrow_length, self.vehicle_pos[2])
        if self.field_right_active:
            glColor3f(0.0, 1.0, 1.0)
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2])
            glVertex3f(self.vehicle_pos[0] + arrow_length, self.vehicle_pos[1], self.vehicle_pos[2])
        if self.field_left_active:
            glColor3f(1.0, 0.0, 1.0)
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2])
            glVertex3f(self.vehicle_pos[0] - arrow_length, self.vehicle_pos[1], self.vehicle_pos[2])
        if self.field_forward_active:
            glColor3f(0.5, 0.5, 1.0)
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2])
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2] + arrow_length)
        if self.field_backward_active:
            glColor3f(1.0, 1.0, 0.0)
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2])
            glVertex3f(self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2] - arrow_length)
        glEnd()

    def render_text(self, text, pos):
        try:
            text_surface = self.font.render(text, True, (255, 255, 255), (0, 0, 0))
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            glPushMatrix()
            glMatrixMode(GL_PROJECTION)
            glPushMatrix()
            glLoadIdentity()
            glOrtho(0, self.display[0], 0, self.display[1], -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glDisable(GL_DEPTH_TEST)
            glRasterPos2f(pos[0], pos[1])
            glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            glEnable(GL_DEPTH_TEST)
            glMatrixMode(GL_PROJECTION)
            glPopMatrix()
            glMatrixMode(GL_MODELVIEW)
            glPopMatrix()
            print(f"Rendered text: {text} at {pos}")  # Debug print
        except Exception as e:
            print(f"Text rendering error: {e}")

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    running = False
                elif event.type == KEYDOWN:
                    key = event.key
                    if key in (K_UP, K_w):
                        self.field_up_active = True
                    elif key in (K_DOWN, K_s):
                        self.field_down_active = True
                    elif key in (K_RIGHT, K_d):
                        self.field_right_active = True
                    elif key in (K_LEFT, K_a):
                        self.field_left_active = True
                    elif key == K_f:
                        self.field_forward_active = True
                    elif key == K_b:
                        self.field_backward_active = True
                    elif key == K_r:
                        self.reset()
                    elif key in (K_PLUS, K_EQUALS):
                        self.magnetic_strength = min(self.magnetic_strength + 100, 2000)
                    elif key == K_MINUS:
                        self.magnetic_strength = max(self.magnetic_strength - 100, 100)
                    elif key == K_p:
                        self.payload_active = not self.payload_active
                        self.vehicle_mass = 10.0 if self.payload_active else 1.0
                    elif key == K_g:
                        self.gravity_reduced = not self.gravity_reduced
                elif event.type == KEYUP:
                    key = event.key
                    if key in (K_UP, K_w):
                        self.field_up_active = False
                    elif key in (K_DOWN, K_s):
                        self.field_down_active = False
                    elif key in (K_RIGHT, K_d):
                        self.field_right_active = False
                    elif key in (K_LEFT, K_a):
                        self.field_left_active = False
                    elif key == K_f:
                        self.field_forward_active = False
                    elif key == K_b:
                        self.field_backward_active = False

            # Update physics
            effective_gravity = 0.1 if self.gravity_reduced else self.gravity
            force = np.array([0.0, 0.0, 0.0])
            force[1] -= self.vehicle_mass * effective_gravity

            magnetic_force_y = 0.0
            if self.field_up_active:
                distance_to_ground = self.vehicle_pos[1] - self.ground_y
                if distance_to_ground > 0:
                    target_height = 50.0
                    error = target_height - distance_to_ground
                    magnetic_force_y = self.magnetic_strength / (distance_to_ground ** 2 + 0.01) + self.pid_kp * error
                    force[1] += min(magnetic_force_y, 2000.0)
            if self.field_down_active:
                force[1] -= self.magnetic_strength * 0.1
            if self.field_right_active:
                force[0] += self.magnetic_strength * 0.1
            if self.field_left_active:
                force[0] -= self.magnetic_strength * 0.1
            if self.field_forward_active:
                force[2] += self.magnetic_strength * 0.1
            if self.field_backward_active:
                force[2] -= self.magnetic_strength * 0.1

            plasma_thrust = np.array([0.0, 0.0, 0.0])
            if any([self.field_up_active, self.field_down_active, self.field_right_active,
                    self.field_left_active, self.field_forward_active, self.field_backward_active]):
                plasma_thrust = np.array([random.uniform(-5, 5), random.uniform(-5, 5), random.uniform(-5, 5)])
                force += plasma_thrust * 0.1
                self.plasma_energy = random.uniform(100, 500)
            else:
                self.plasma_energy = 0.0

            current = 1000.0
            force += current * np.cross(self.vehicle_vel, self.external_field)

            if self.vehicle_pos[1] <= self.ground_y + 1:
                friction_force_x = -self.friction_coeff * self.vehicle_mass * effective_gravity * np.sign(self.vehicle_vel[0])
                friction_force_z = -self.friction_coeff * self.vehicle_mass * effective_gravity * np.sign(self.vehicle_vel[2])
                force[0] += friction_force_x if abs(self.vehicle_vel[0]) > 0 else 0
                force[2] += friction_force_z if abs(self.vehicle_vel[2]) > 0 else 0

            acceleration = force / self.vehicle_mass
            self.vehicle_vel += acceleration * self.dt
            self.vehicle_pos += self.vehicle_vel * self.dt

            power = sum(abs(f) * abs(v) for f, v in zip(force, self.vehicle_vel)) + self.plasma_energy
            self.energy_used += power * self.dt

            if self.vehicle_pos[1] < self.ground_y:
                self.vehicle_pos[1] = self.ground_y
                self.vehicle_vel[1] = 0
            if self.vehicle_pos[0] < 0 or self.vehicle_pos[0] > 800:
                self.vehicle_pos[0] = max(0, min(self.vehicle_pos[0], 800))
                self.vehicle_vel[0] = 0
            if self.vehicle_pos[2] < -1000 or self.vehicle_pos[2] > 1000:
                self.vehicle_pos[2] = max(-1000, min(self.vehicle_pos[2], 1000))
                self.vehicle_vel[2] = 0

            # Update camera
            glLoadIdentity()
            gluPerspective(45, (self.display[0] / self.display[1]), 0.1, 5000.0)
            gluLookAt(
                self.vehicle_pos[0], self.vehicle_pos[1] + self.camera_height, self.vehicle_pos[2] + self.camera_distance,
                self.vehicle_pos[0], self.vehicle_pos[1], self.vehicle_pos[2],
                0, 1, 0
            )

            # Render
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            self.draw_skybox()
            self.draw_ground()
            self.draw_sphere(self.vehicle_pos)
            self.draw_field_arrows()
            self.draw_warp_lines()

            # Detailed text overlay
            active_fields = []
            if self.field_up_active:
                active_fields.append("Up")
            if self.field_down_active:
                active_fields.append("Down")
            if self.field_right_active:
                active_fields.append("Right")
            if self.field_left_active:
                active_fields.append("Left")
            if self.field_forward_active:
                active_fields.append("Forward")
            if self.field_backward_active:
                active_fields.append("Backward")
            fields_text = ", ".join(active_fields) if active_fields else "None"
            text_lines = [
                f"Position: ({self.vehicle_pos[0]:.1f}, {self.vehicle_pos[1]:.1f}, {self.vehicle_pos[2]:.1f}) m",
                f"Velocity: ({self.vehicle_vel[0]:.1f}, {self.vehicle_vel[1]:.1f}, {self.vehicle_vel[2]:.1f}) m/s",
                f"Acceleration: ({acceleration[0]:.1f}, {acceleration[1]:.1f}, {acceleration[2]:.1f}) m/s²",
                f"Fields Active: {fields_text}",
                f"Mag Strength: {self.magnetic_strength:.0f} units",
                f"Mass: {self.vehicle_mass:.1f} kg",
                f"Gravity: {effective_gravity:.2f} m/s² ({'Reduced' if self.gravity_reduced else 'Normal'})",
                f"Power: {self.format_power(power)}",
                f"Total Energy: {self.format_energy(self.energy_used)}",
                f"Plasma Energy: {self.format_power(self.plasma_energy)}",
                f"Controls: W/S/A/D/F/B (move), +/- (mag), P (payload), G (gravity), R (reset)"
            ]
            for i, line in enumerate(text_lines):
                self.render_text(line, (10, self.display[1] - 20 - i * 20))

            pygame.display.flip()
            self.clock.tick(1 / self.dt)

        pygame.quit()

if __name__ == "__main__":
    sim = MagneticVehicleSimulation()
    sim.run()

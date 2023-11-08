import numpy as np

ħ = 1.05e-34
u_a = 1.68e-41
ϵ0 = 8.86e-12
c = 3e8
k_B = 1.38e-23


class MoveTweezers:
    def __init__(self, trap_distance, U0, m, w0, z_R, N_stat=1000, dx=1e-9):
        self.trap_distance = trap_distance
        self.U0 = U0
        self.m = m
        self.w0 = w0
        self.z_R = z_R
        self.N_stat = N_stat
        self.dx = dx

    def trap_frequencies(self):
        ω_x, ω_y = np.sqrt(4 * self.U0 / (self.m * self.w0**2)), np.sqrt(
            4 * self.U0 / (self.m * self.w0**2)
        )
        ω_z = np.sqrt(2 * self.U0 / (self.m * self.z_R**2))
        return np.array([ω_x, ω_y, ω_z])

    def initial_params(self, T):
        random_generator = np.random.default_rng(seed=42)
        trap_frequency = self.trap_frequencies()
        position = np.sqrt(k_B * T / (self.m * trap_frequency**2))
        position = random_generator.normal(0.0, 1.0, size=(self.N_stat, 3)) * position
        momentum = random_generator.normal(
            0.0, scale=np.sqrt(self.m * k_B * T), size=(self.N_stat, 3)
        )
        return position, momentum

    def dipole_potential(self, x):
        r = np.sqrt(x[:, :, 0] ** 2 + x[:, :, 1] ** 2)
        w_z = self.w0 * np.sqrt(1 + (x[:, :, 2] / self.z_R) ** 2)
        return -self.U0 * (self.w0 / w_z) ** 2 * np.exp(-2 * r**2 / w_z**2)

    def recapture_atoms(self, move_times, T, init_recap, **kwargs):
        N_t = len(move_times)
        p_trap = np.zeros((len(move_times), 3))
        p_trap[:, 0] = 2 * self.trap_distance / move_times * self.m
        x0, p0 = self.initial_params(T)

        positions = np.einsum("ij,k->ikj", x0, np.ones_like(move_times))

        p = np.zeros((self.N_stat, N_t, 3))
        for i in range(0, N_t):
            p[:, i] = p0 + p_trap[i]
        p_squared = np.einsum("ijk,ijk->ij", p, p)
        energies = self.dipole_potential(positions)
        for i in range(len(move_times)):
            energies[:, i] = energies[:, i] + 0.5 * p_squared[:, i] / self.m
        recaptured_fraction = energies < 0
        frac = init_recap * np.sum(recaptured_fraction, axis=0) / self.N_stat
        return frac

from Samples.Allegheny_Flu.Allegheny_Flu.Allegheny_FluModel import Allegheny_FluModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import time

model = Allegheny_FluModel(
    datacollector=DataCollector(
        model_reporters={
            "Susceptible_Low": lambda m: sum([a.flu == 's' and a.school == '450149323' for a in m.schedule.agents]),
            "Infected_Low": lambda m: sum([a.flu == 'i' and a.school == '450149323' for a in m.schedule.agents]),
            "Recovered_Low": lambda m: sum([a.flu == 'r' and a.school == '450149323' for a in m.schedule.agents]),
            "Susceptible_Med": lambda m: sum([a.flu == 's' and a.school == '450067740' for a in m.schedule.agents]),
            "Infected_Med": lambda m: sum([a.flu == 'i' and a.school == '450067740' for a in m.schedule.agents]),
            "Recovered_Med": lambda m: sum([a.flu == 'r' and a.school == '450067740' for a in m.schedule.agents])
        }
    )
)

runs = 100

t0 = time.time()
for _ in range(runs):
    model.step()
time_elapsed = time.time() - t0
print(f'Time elapsed in {runs} iterations: {time_elapsed} seconds')

frame = model.datacollector.get_model_vars_dataframe()

plt.figure('low', figsize=(8, 6))
plt.plot(frame['Susceptible_Low'], color='blue', label='Susceptible')
plt.plot(frame['Infected_Low'], color='orange', label='Infected')
plt.plot(frame['Recovered_Low'], color='green', label='Recovered')
plt.xlabel('Iteration')
plt.ylabel('Agents')
plt.title(f'Allegheny Flu SIRS Model - 88% Low-Income Students - {runs} Iterations')
plt.legend()
plt.tight_layout()
plt.savefig('Allegheny_Flu_ABM_out_low.png', dpi=300)

plt.figure('med', figsize=(8, 6))
plt.plot(frame['Susceptible_Med'], color='blue', label='Susceptible')
plt.plot(frame['Infected_Med'], color='orange', label='Infected')
plt.plot(frame['Recovered_Med'], color='green', label='Recovered')
plt.xlabel('Iteration')
plt.ylabel('Agents')
plt.title(f'Allegheny Flu SIRS Model - 7% Low-Income Students - {runs} Iterations')
plt.legend()
plt.tight_layout()
plt.savefig('Allegheny_Flu_ABM_out_med.png', dpi=300)
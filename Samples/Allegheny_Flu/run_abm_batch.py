from Samples.Allegheny_Flu.Allegheny_Flu.Allegheny_FluModel import Allegheny_FluModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import time
import random

steps = 100
runs = 10
frames = []

for run in range(runs):
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

    for step in range(steps):
        model.step()

    frames.append(model.datacollector.get_model_vars_dataframe())

plt.figure('low', figsize=(8, 6))
plt.figure('med', figsize=(8, 6))
for f in frames:
    alpha = random.uniform(0.3, 0.7)
    plt.figure('low')
    plt.plot(f['Susceptible_Low'], color='blue', alpha=alpha, label='Susceptible')
    plt.plot(f['Infected_Low'], color='orange', alpha=alpha, label='Infected')
    plt.plot(f['Recovered_Low'], color='green', alpha=alpha, label='Recovered')
    plt.figure('med')
    plt.plot(f['Susceptible_Med'], color='blue', alpha=alpha, label='Susceptible')
    plt.plot(f['Infected_Med'], color='orange', alpha=alpha, label='Infected')
    plt.plot(f['Recovered_Med'], color='green', alpha=alpha, label='Recovered')

plt.figure('low')
handles, labels = plt.gca().get_legend_handles_labels()
by_label = dict(zip(labels, handles))
for h in plt.legend(by_label.values(), by_label.keys()).legendHandles:
    h.set_alpha(1)
plt.xlabel('Iteration')
plt.ylabel('Agents')
plt.title(f'Allegheny Flu SIRS Model - 88% Low-Income Students - {steps} Iterations - {runs} Trials')
plt.tight_layout()
plt.savefig('Allegheny_Flu_ABM_batch_out_low.png', dpi=300)

plt.figure('med')
handles, labels = plt.gca().get_legend_handles_labels()
by_label = dict(zip(labels, handles))
for h in plt.legend(by_label.values(), by_label.keys()).legendHandles:
    h.set_alpha(1)
plt.xlabel('Iteration')
plt.ylabel('Agents')
plt.title(f'Allegheny Flu SIRS Model - 7% Low-Income Students - {steps} Iterations - {runs} Trials')
plt.tight_layout()
plt.savefig('Allegheny_Flu_ABM_batch_out_med.png', dpi=300)

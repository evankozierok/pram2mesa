from Samples.SIRS.SIRSModel.SIRSModelModel import SIRSModelModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import random

steps = 48
runs = 10
frames = []

for run in range(runs):
    # create model
    model = SIRSModelModel(
        datacollector=DataCollector(
            model_reporters={
                "Susceptible": lambda m: sum([a.flu == 's' for a in m.schedule.agents]),
                "Infected": lambda m: sum([a.flu == 'i' for a in m.schedule.agents]),
                "Recovered": lambda m: sum([a.flu == 'r' for a in m.schedule.agents])
            }
        )
    )

    # run model
    for step in range(steps):
        model.step()

    # grab data
    frames.append(model.datacollector.get_model_vars_dataframe())


plt.figure(figsize=(8, 6))
for f in frames:
    alpha = random.uniform(0.3, 0.7)
    plt.plot(f['Susceptible'], color='blue', alpha=alpha, label='Susceptible')
    plt.plot(f['Infected'], color='orange', alpha=alpha, label='Infected')
    plt.plot(f['Recovered'], color='green', alpha=alpha, label='Recovered')

# eliminate duplicates in legend, reset opacity
handles, labels = plt.gca().get_legend_handles_labels()
by_label = dict(zip(labels, handles))
for h in plt.legend(by_label.values(), by_label.keys()).legendHandles:
    h.set_alpha(1)

plt.xlabel('Iteration')
plt.ylabel('Agents')
plt.title(f'SIRS ABM Model - {steps} Iterations - {runs} Trials')
plt.tight_layout()
# plt.show()
plt.savefig('SIRS_ABM_batch_out.png', dpi=300)

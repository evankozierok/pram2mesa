from Samples.Migration.Migration.MigrationModel import MigrationModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import random

steps = 48
runs = 100
frames = []

for run in range(runs):
    # create model
    model = MigrationModel(
        datacollector=DataCollector(
            model_reporters={
                "Migrating": lambda m: sum([a.is_migrating for a in m.schedule.agents]),
                "Settled": lambda m: sum([hasattr(a, 'has_settled') and a.has_settled for a in m.schedule.agents]),
                "Dead": lambda m: 1000 - len(m.schedule.agents)
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
    plt.plot(f['Migrating'], color='blue', alpha=alpha, label='Migrating')
    plt.plot(f['Settled'], color='orange', alpha=alpha, label='Settled')
    plt.plot(f['Dead'], color='green', alpha=alpha, label='Dead')

# eliminate duplicates in legend
handles, labels = plt.gca().get_legend_handles_labels()
by_label = dict(zip(labels, handles))
for h in plt.legend(by_label.values(), by_label.keys()).legendHandles:
    h.set_alpha(1)

plt.xlabel('Iteration')
plt.ylabel('Agents')
plt.title(f'Migration ABM Model - {steps} Iterations - {runs} Trials')
plt.tight_layout()
# plt.show()
plt.savefig('Migration_ABM_batch_out.png', dpi=300)

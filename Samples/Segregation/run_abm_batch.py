from Samples.Segregation.SegregationModel.SegregationModelModel import SegregationModelModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import random

steps = 70
runs = 10
frames = []

for run in range(runs):
    # create model
    model = SegregationModelModel(
        datacollector=DataCollector(
            model_reporters={
                "Red @ A": lambda m: sum([a.team == 'red' for a in m.grid.get_cell_list_contents(['a'])]),
                "Blue @ A": lambda m: sum([a.team == 'blue' for a in m.grid.get_cell_list_contents(['a'])]),
                "Red @ B": lambda m: sum([a.team == 'red' for a in m.grid.get_cell_list_contents(['b'])]),
                "Blue @ B": lambda m: sum([a.team == 'blue' for a in m.grid.get_cell_list_contents(['b'])])
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
    plt.plot(f['Red @ A'], color='red', alpha=alpha, label='Red @ A')
    plt.plot(f['Blue @ A'], color='blue', alpha=alpha, label='Blue @ A')
    plt.plot(f['Red @ B'], color='firebrick', alpha=alpha, label='Red @ B')
    plt.plot(f['Blue @ B'], color='navy', alpha=alpha, label='Blue @ B')

# eliminate duplicates in legend
handles, labels = plt.gca().get_legend_handles_labels()
by_label = dict(zip(labels, handles))
plt.legend(by_label.values(), by_label.keys())

plt.xlabel('Iteration')
plt.ylabel('Agents')
plt.title('Segregation ABM Model - 48 Iterations - 10 Trials')
plt.tight_layout()
# plt.show()
plt.savefig('Segregation_ABM_batch_out.png', dpi=300)

from Samples.Segregation.SegregationModel.SegregationModelModel import SegregationModelModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import time

model = SegregationModelModel()

model.datacollector = DataCollector(
   model_reporters={
       "Red @ A": lambda m: sum([a.team == 'red' for a in m.grid.get_cell_list_contents(['a'])]),
       "Blue @ A": lambda m: sum([a.team == 'blue' for a in m.grid.get_cell_list_contents(['a'])]),
       "Red @ B": lambda m: sum([a.team == 'red' for a in m.grid.get_cell_list_contents(['b'])]),
       "Blue @ B": lambda m: sum([a.team == 'blue' for a in m.grid.get_cell_list_contents(['b'])])
    }
)

runs = 70

t0 = time.time()
for _ in range(runs):
    model.step()
time_elapsed = time.time() - t0
print(f'Time elapsed in {runs} iterations: {time_elapsed} seconds')

plot = model.datacollector.get_model_vars_dataframe().plot(
    figsize=(8, 6),
    title=f'Segregation ABM Model - {runs} iterations',
    color=['red', 'blue', 'firebrick', 'navy']
)
plot.set_xlabel('Iteration')
plot.set_ylabel('Agents')
plt.tight_layout()
plt.savefig('Segregation_ABM_out.png', dpi=300)

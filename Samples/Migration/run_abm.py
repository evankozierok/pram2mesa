from Samples.Migration.Migration.MigrationModel import MigrationModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import time

model = MigrationModel()

# the original PRAM has 1000000 agents; however, you may want to keep it smaller in the ABM (this sample has 1000)
# because of memory and time concerns!
pop_size = len(model.schedule.agents)

model.datacollector = DataCollector(
    model_reporters={
        "Migrating": lambda m: sum([a.is_migrating for a in m.schedule.agents]),
        "Settled": lambda m: sum([hasattr(a, 'has_settled') and a.has_settled for a in m.schedule.agents]),
        "Dead": lambda m: pop_size - len(m.schedule.agents)
    }
)

runs = 48

t0 = time.time()
for i in range(runs):
    model.step()
time_elapsed = time.time() - t0
print(f'Time elapsed in {runs} iterations: {time_elapsed} seconds')

plot = model.datacollector.get_model_vars_dataframe().plot(
    figsize=(8, 6),
    title=f'Migration ABM Model - {runs} iterations',
)
plot.set_xlabel('Iteration')
plot.set_ylabel('Agents')
plt.tight_layout()
plt.savefig('Migration_ABM_out.png', dpi=300)

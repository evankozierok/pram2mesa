from Samples.SIRS.SIRSModel.SIRSModelModel import SIRSModelModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import time

model = SIRSModelModel(
    datacollector=DataCollector(
        model_reporters={
            "Susceptible": lambda m: sum([a.flu == 's' for a in m.schedule.agents]),
            "Infected": lambda m: sum([a.flu == 'i' for a in m.schedule.agents]),
            "Recovered": lambda m: sum([a.flu == 'r' for a in m.schedule.agents])
        }
    )
)

runs = 48

t0 = time.time()
for _ in range(runs):
    model.step()
time_elapsed = time.time() - t0
print(f'Time elapsed in {runs} iterations: {time_elapsed} seconds')

plot = model.datacollector.get_model_vars_dataframe().plot(
    figsize=(8, 6),
    title=f'SIRS ABM Model - {runs} iterations',
)
plot.set_xlabel('Iteration')
plot.set_ylabel('Agents')
plt.tight_layout()
plt.savefig('SIRS_ABM_out.png', dpi=300)
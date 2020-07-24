from Samples.Migration.Migration.MigrationModel import MigrationModel
from mesa.datacollection import DataCollector
import matplotlib.pyplot as plt
import time
import os
import json

# normally, group size is determined strictly from the JSON file. Since we want to vary this, we temporarily change
# the name of the JSON file to maintain its original contents and create new JSON files named MigrationGroups.json
# inside the loop with varying group sizes.
os.chdir('Migration')
os.rename(r'MigrationGroups.json', r'MigrationGroups_source.json')

with open(r'MigrationGroups_source.json', 'r') as src:
    # k is our power of 10 for the size
    j_src = json.load(src)
    for k in range(5):
        pop_size = 10**k
        with open(r'MigrationGroups.json', 'w') as dest:
            # edit group size
            j = j_src
            for group in j:
                group['m'] = pop_size
            json.dump(j, dest, indent=4)

        model = MigrationModel()

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
        print(f'Time elapsed in {runs} iterations for size 10^{k}: {time_elapsed} seconds')

        plot = model.datacollector.get_model_vars_dataframe().plot(
            figsize=(8, 6),
            title=f'Migration ABM Model - {runs} iterations at mass 10^{k}',
        )
        plot.set_xlabel('Iteration')
        plot.set_ylabel('Agents')
        plt.tight_layout()
        plt.savefig(f'Migration_ABM_out_10_pow_{k}.png', dpi=300)

# delete our temp file and restore the original file
os.remove(r'MigrationGroups.json')
os.rename(r'MigrationGroups_source.json', r'MigrationGroups.json')
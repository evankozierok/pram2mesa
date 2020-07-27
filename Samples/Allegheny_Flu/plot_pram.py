import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import sqlite3

fpath_db = os.path.join(os.path.dirname(__file__), 'output', 'allegheny-flu-results.sqlite3')


# ----------------------------------------------------------------------------------------------------------------------
def plot_one_school(tbl, title, fpath):
    ''' Plot one of the schools (i.e., a low- or medium-income one). '''

    # Data:
    data = { 'i':[], 'ps':[], 'pi':[], 'pr':[] }
    with sqlite3.connect(fpath_db, check_same_thread=False) as c:
        for r in c.execute(f'SELECT i+1, ps,pi,pr FROM {tbl}').fetchall():
            data['i'].append(r[0])
            data['ps'].append(r[1])
            data['pi'].append(r[2])
            data['pr'].append(r[3])

    # Plot:
    fig = plt.figure(figsize=(8,6))
    plt.title(title)
    plt.plot(data['i'], data['ps'], lw=2)
    plt.plot(data['i'], data['pi'], lw=2)
    plt.plot(data['i'], data['pr'], lw=2)
    plt.legend(['Susceptible', 'Exposed', 'Recovered'], loc='upper right')
    plt.xlabel('Iteration')
    plt.ylabel('Probability')
    plt.grid(alpha=0.25, antialiased=True)
    fig.savefig(os.path.join(os.path.dirname(__file__), 'output', fpath), dpi=300)


plot_one_school('low_income', 'School with 88% of Low-Income Students', 'Allegheny_Flu_PRAM_out_low.png')
plot_one_school('med_income', 'School with 7% of Low-Income Students', 'Allegheny_Flu_PRAM_out_med.png')

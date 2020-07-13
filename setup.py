import setuptools

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='pram2mesa',
    version='0.1.0',
    author='Evan Kozierok',
    author_email='evan.kozierok@gmail.com',
    description="Tools for translating PyPRAM's Probabilistic Relational Agent-Based Models to Mesa's Agent-Based Models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/evankozierok/pram2mesa',
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.8"
    ],
    python_requires='~=3.8',
    install_requires=[
        'dill',
        'astor',
        'autopep8',
        'iteround',
        'mesa',
        'networkx'
        # these github links just don't work...
        # 'pypram @ git+ssh://git@github.com/momacs/pram'
    ]
)
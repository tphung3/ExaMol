"""Specification of the optimization problem"""
from pathlib import Path
import shutil
import sys

from parsl import Config, HighThroughputExecutor
from parsl.executors.taskvine import TaskVineExecutor, TaskVineManagerConfig, TaskVineFactoryConfig
from proxystore.store import Store
from proxystore.connectors.file import FileConnector

from examol.reporting.markdown import MarkdownReporter
from examol.score.rdkit import make_knn_model, RDKitScorer
from examol.simulate.ase import ASESimulator
from examol.solution import SingleFidelityActiveLearning
from examol.start.fast import RandomStarter
from examol.steer.single import SingleStepThinker
from examol.store.recipes import RedoxEnergy
from examol.select.baseline import GreedySelector
from examol.specify import ExaMolSpecification

# Parameters you may want to configure
num_random: int = 4000 # Number of randomly-selected molecules to run
num_total: int = 4000  # Total number of molecules to run
num_tasks_per_taskvine_worker: int = 8 # Number of tasks running concurrently on a worker.
num_taskvine_workers: int = 150 # Number of taskvine workers at any given time, max number of taskvine workers with the below size can go up to 208 at ND HTCondor cluster.
num_workers: int = num_taskvine_workers * num_tasks_per_taskvine_worker   # Number of chemistry tasks submitted at one time, similar to the degree of parallelism of the application
cores = 32
memory = 64000
disk = 64000
big_dataset = 'redoxmers-bebop' # This one has 100K atoms, with 20k of good atoms.
small_dataset = 'redoxmers' # This one has 1k atoms.
dataset = 'redoxmers-bebop'
compute_mode = 'taskvine-sharedfs'    # out of {taskvine-sharedfs, taskvine-task, taskvine-serverless}, taskvine-sharedfs has no context, taskvine-task shares context on disk, taskvine-serverless shares context on disk and in memory.
worker_timeout = 7200 # workers when connected to manager will wait for 7200s before asking to leave
num_wait_for_taskvine_workers = int(num_taskvine_workers*0.95)  # number of taskvine workers needed to connect before the manager starts working
port = 9130 # port the manager uses
# tarball for taskvine python task, run poncho_package_create on the environment for it
env_tarball = 'placeholder'
env_name = 'hpdc2024-examol'
# Get my path. We'll want to provide everything as absolute paths, as they are relative to this file
my_path = Path().absolute()

# Get dataset path
if dataset == big_dataset:
    dataset_path = my_path.parent / 'redoxmers-bebop'
else:
    dataset_path = my_path

# Config the compute medium of application
executor = None
factory_config=TaskVineFactoryConfig(
    min_workers=num_taskvine_workers,
    max_workers=num_taskvine_workers,
    workers_per_cycle=num_taskvine_workers,
    cores=cores,
    memory=memory,
    disk=disk,
    worker_timeout=worker_timeout,
    batch_type='condor',
    condor_requirements='has_scratch365')

if compute_mode == 'taskvine-serverless':
    executor = TaskVineExecutor(
                    worker_launch_method='factory',
                    function_exec_mode='serverless',
                    manager_config=TaskVineManagerConfig(
                        port=port,
                        project_name=env_name,
                        env_pack=env_name,
                        library_config={'num_slots': num_tasks_per_taskvine_worker, 'cores': cores, 'memory': memory, 'disk': disk},
                        shared_fs=False,
                        enable_peer_transfers=True,
                        wait_for_workers=num_wait_for_taskvine_workers),
                    factory_config=factory_config)
elif compute_mode == 'taskvine-task':
    executor = TaskVineExecutor(
                    worker_launch_method='factory',
                    function_exec_mode='regular',
                    manager_config=TaskVineManagerConfig(
                        port=9130,
                        project_name='hpdc2024-examol',
                        #env_pack='hpdc2024-examol',
                        env_pack=env_tarball,
                        shared_fs=False,
                        enable_peer_transfers=True,
                        task_resource_config={'cores': cores // num_tasks_per_taskvine_worker,
                                              'memory': memory // num_tasks_per_taskvine_worker,
                                              'disk': disk // num_tasks_per_taskvine_worker},
                        wait_for_workers=num_wait_for_taskvine_workers),
                    factory_config=factory_config)
else:
    executor = TaskVineExecutor(
                    worker_launch_method='factory',
                    function_exec_mode='regular',
                    manager_config=TaskVineManagerConfig(
                        port=9130,
                        project_name='hpdc2024-examol',
                        init_command='/scratch365/tphung/miniconda/bin/conda run -p /scratch365/tphung/miniconda/envs/hpdc2024-examol',
                        env_pack=None,
                        shared_fs=True,
                        enable_peer_transfers=False,
                        task_resource_config={'cores': cores // num_tasks_per_taskvine_worker,
                                              'memory': memory // num_tasks_per_taskvine_worker,
                                              'disk': disk // num_tasks_per_taskvine_worker},
                        wait_for_workers=num_wait_for_taskvine_workers),
                    factory_config=factory_config)
    #executor = HighThroughputExecutor(max_workers=1)

config = Config(executors=[executor],
                run_dir=str((my_path / 'parsl-logs')),
)

# Delete the old run
run_dir = my_path / f'run_{num_random}_{num_total}_{num_workers}_{dataset}_{compute_mode}'
if run_dir.is_dir():
    shutil.rmtree(run_dir)

# Make the recipe
recipe = RedoxEnergy(1, energy_config='mopac_pm7', solvent='acn')

# Make the scorer
pipeline = make_knn_model()
scorer = RDKitScorer()

# Define the tools needed to solve the problem
solution = SingleFidelityActiveLearning(
    starter=RandomStarter(),
    minimum_training_size=num_random,
    selector=GreedySelector(num_total, maximize=True),
    scorer=scorer,
    models=[[pipeline]],
    num_to_run=num_total,
)

# Mark how we report outcomes
reporter = MarkdownReporter()

# Make the parsl (compute) and proxystore (optional data fabric) configuration
is_mac = sys.platform == 'darwin'

store = Store(name='file', connector=FileConnector(store_dir=str(my_path / 'proxystore')), metrics=True)

spec = ExaMolSpecification(
    database=(run_dir / 'database.json'),
    recipes=[recipe],
    search_space=[(dataset_path / 'search_space.smi')],
    solution=solution,
    simulator=ASESimulator(scratch_dir=(run_dir / 'tmp'), clean_after_run=False),
    thinker=SingleStepThinker,
    compute_config=config,
    proxystore=store,
    reporters=[reporter],
    run_dir=run_dir,
    thinker_options={'num_workers': num_workers}
)

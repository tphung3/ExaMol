This directory contains the necessary code to run the ExaMol application. It also contains logs from collected runs.

# Create environment
Run `./create_env.sh` to create the working environment. This will create a conda environment named 'hpdc2024-examol', then builds and installs cctools and parsl. Note that cctools and parsl may be out of date at the time you are reading this. For the purpose of rerunning experiments however, they should be good.

# Run experiments
Each experiment has its configuration set in examples/redoxmers/spec.py. Each configurable option is commented there.
Once the configurations are set, run the experiment by `examol run examples/redoxmers/spec.py:spec`. This will create various run and logging directories. The most relevant logs are in `examples/redoxmers/parsl-logs/TaskVineExecutor`.

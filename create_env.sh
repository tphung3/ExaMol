base_conda_path=$(conda info --base)
env_name='hpdc2024-examol'

# base environment for examol
conda env create -n ${env_name} --file envs/environment-cpu.yml --force

# activate env
source ${base_conda_path}/bin/activate ${env_name}

# cctools deps, may generate warnings with libmamba, strict channel priority needed otherwise conda goes to anaconda for the wrong version of gcc
conda install -c conda-forge --strict-channel-priority gcc_linux-64 gxx_linux-64 make zlib swig conda-pack packaging cloudpickle -y

# build cctools
cd deps/cctools-src
./configure --with-base-dir ${CONDA_PREFIX} --prefix ${CONDA_PREFIX} --debug; make install
cd ../..

# build customized parsl
cd deps/
pip install parsl
cd ..

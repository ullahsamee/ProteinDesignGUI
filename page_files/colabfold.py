from common import *
import configparser
import shutil
import subprocess
from os.path import expandvars
from datetime import datetime
from Bio import SeqIO


state = st.session_state


@st.dialog('Continue with inputting sequences', width='large')
def try_run():
    st.write('Input chain sequences of a protein')
    table = st.data_editor(pd.DataFrame({'chain': []}, dtype=str), use_container_width=True, num_rows='dynamic', hide_index=True,
                           column_config={'chain': st.column_config.TextColumn('Chains', required=True)})
    _, col, _ = st.columns(3)
    if col.button('Submit', use_container_width=True, disabled=len(table) == 0):
        cache_dir = cache / f'{datetime.now()} boltz'
        input_dir = cache_dir / 'seqs'
        input_dir.mkdir(parents=True, exist_ok=True)
        t = cache_dir / 'config.yml'
        cfg = get_config(active)
        sync(cfg['boltz'])
        cfg['name'] = 'TestJob'
        put_config(cfg, t)
        with open(input_dir / 'test.fasta', 'w') as f:
            f.write('>Test\n')
            f.write(':\n'.join(table['chain']))
        setup_process(t)
        st.rerun()


def get_cmd(wkdir, n_recycle, n_mod, use_amber, use_template):
    cmd = f"""
    source {conda}
    conda activate {env}
    # Function to handle signals
    cleanup() {{
        echo "Signal received. Killing subprocess..."
        if [ -n "$pid" ] && ps -p $pid > /dev/null; then
            kill $pid
        fi
        echo "Cleanup complete. Exiting."
        exit 1
    }}
    cd "{wkdir}"
    trap cleanup SIGINT SIGTERM
    for fa in `ls seqs/*.fasta`; do
        trap cleanup SIGINT SIGTERM
        outdir={outdir}/`basename $fa .fasta`
        mkdir -p $outdir
        {exe} $fa $outdir --num-models {n_mod} --num-recycle {n_recycle} {'--amber' if use_amber else ''} {'--template' if use_template else ''} &
        pid=$!
        wait $pid
    done && {exe_post} {outdir} &
    pid=$!
    wait $pid
    
    """
    return cmd


def sync(config):
    config['use_amber'] = state['use_amber']
    config['use_template'] = state['use_template']
    config['n_mod'] = state['n_mod']
    config['n_recycle'] = state['n_recycle']


def save():
    sync(cfg['colabfold'])
    put_config(cfg, active)
    st.toast('Configuration saved!', icon="✅")


def setup_process(trial):
    wkdir = trial.parent
    shutil.rmtree(wkdir / outdir, ignore_errors=True)
    cfg = get_config(trial)
    cmd = get_cmd(wkdir, **cfg['colabfold'])
    nfiles = 0
    for i in wkdir.glob('seqs/*.fasta'):
        nfiles += len([*SeqIO.parse(i, 'fasta')])
    assert nfiles > 0, "Nothing to process."
    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
    state['process_args'] = cfg['colabfold']['n_mod'] * nfiles, f'Folding for {cfg["name"]}..', wkdir, wildcard, 3, trial


if __name__ == '__page__':
    trials = state['trials']
    active = state['current_trial']
    outdir = 'AF2'
    wildcard = f'{outdir}/*.pdb'

    config = configparser.ConfigParser()
    config.read('settings.conf')
    conda = f"{config['Paths']['ColabFold']}/conda/etc/profile.d/conda.sh"
    env = f"{config['Paths']['ColabFold']}/colabfold-conda"
    exe = f"{config['Paths']['ColabFold']}/colabfold-conda/bin/colabfold_batch"
    exe_post = f"python {Path(__file__).parent.parent}/tools/postprocess_colabfold.py"
    cache = Path(expandvars(config['Paths']['cache']))

    if state['auto'] is not None:
        setup_process(state['auto'])
        state['auto'] = None

    st.title('ColabFold')
    tab1, tab2 = st.tabs(['Configure', 'Visualize'])

    if active is not None:
        active = Path(active)
        with tab2:
            results = sorted(active.parent.glob(wildcard))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')

    cfg = get_config(active)
    config = cfg['colabfold']
    with tab1:
        with st.form(key='form'):
            col1, col2 = st.columns(2)
            col1.checkbox('Use amber', config['use_amber'], key='use_amber')
            col2.checkbox('Use template', config['use_template'], key='use_template')
            col1, col2 = st.columns(2)
            col1.select_slider('Number of models', [1, 2, 3, 4, 5], config['n_mod'], key='n_mod')
            col2.number_input('Number of recycle', 1, value=config['n_recycle'], key='n_recycle')
            col1, col2, col3 = st.columns(3)
            clicked1 = col1.form_submit_button('TEST', use_container_width=True)
            col2.form_submit_button('SAVE', use_container_width=True, on_click=save, disabled=active is None)
            clicked2 = col3.form_submit_button('PROCESS', use_container_width=True, type='primary', on_click=save, disabled=active is None)

    if process_ongoing() and (clicked1 or clicked2):
        st.toast('Process busy!', icon="🚨")
    elif clicked1:
        try_run()
    elif clicked2:
        setup_process(active)

    if process_ongoing():
        progress()
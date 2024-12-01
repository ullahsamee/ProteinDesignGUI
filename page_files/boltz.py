from common import *
import configparser
import subprocess
from os.path import expandvars
from datetime import datetime
import shutil
from Bio import SeqIO


state = st.session_state


@st.dialog('Try with uploading protein sequences')
def try_run():
    seqs = st.file_uploader('Input FASTAs for folding', '.fasta', True)
    if st.button('Confirm', use_container_width=True):
        assert len(seqs) > 0, 'No FASTA sequences.'
        cache_dir = cache / f'{datetime.now()} boltz'
        input_dir = cache_dir / 'seqs'
        input_dir.mkdir(parents=True, exist_ok=True)
        t = cache_dir / 'config.yml'
        cfg = get_config(active)
        sync(cfg['boltz'])
        cfg['name'] = 'TestJob'
        put_config(cfg, t)
        for i in seqs:
            with open(input_dir / i.name, 'wb') as f:
                f.write(i.getvalue())
        setup_process(t)
        st.rerun()


def get_cmd(wkdir, n_recycle, n_sampling, n_diffusion, msa_pairing_strategy):
    cmd = f"""
    cd "{wkdir}"
    rm -r {indir}
    mkdir -p {indir}
    {exe_pre} seqs {indir}
    boltz predict {indir} --recycling_steps {n_recycle} --use_msa_server --sampling_steps {n_sampling} \
        --diffusion_samples {n_diffusion} --output_format pdb --msa_pairing_strategy {msa_pairing_strategy} --out_dir ./
    mv boltz_results_{indir} {outdir}
    {exe_post} {outdir}
    """
    return cmd


def sync(config):
    config['n_diffusion'] = state['n_diffusion']
    config['n_sampling'] = state['n_sampling']
    config['n_recycle'] = state['n_recycle']
    config['msa_pairing_strategy'] = state['msa_pairing_strategy']


def save():
    sync(cfg['boltz'])
    put_config(cfg, active)
    st.toast('Configuration saved!', icon="✅")


def setup_process(trial):
    wkdir = trial.parent
    shutil.rmtree(wkdir / outdir, ignore_errors=True)
    cfg = get_config(trial)
    cmd = get_cmd(wkdir, **cfg['boltz'])
    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
    nfiles = 0
    for i in wkdir.glob('seqs/*.fasta'):
        nfiles += len([*SeqIO.parse(i, 'fasta')])
    state['process_args'] = cfg['boltz']['n_diffusion'] * nfiles, f'Folding for {cfg["name"]}..', wkdir, wildcard, 3, trial


if __name__ == '__page__':
    trials = state['trials']
    active = state['current_trial']
    indir = 'boltz_input'
    outdir = 'AF3'
    wildcard = f'{outdir}/predictions/*/*.pdb'

    config = configparser.ConfigParser()
    config.read('settings.conf')
    exe_pre = f"python {Path(__file__).parent.parent}/tools/preprocess_boltz.py"
    exe_post = f"python {Path(__file__).parent.parent}/tools/postprocess_boltz.py"
    cache = Path(expandvars(config['Paths']['cache']))

    if state['auto'] is not None:
        setup_process(state['auto'])
        state['auto'] = None

    st.title('Boltz-1')
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
    config = cfg['boltz']
    with tab1:
        with st.form(key='form'):
            col1, col2, col3 = st.columns(3)
            col1.number_input('Number of recycle', 1, value=config['n_recycle'], key='n_recycle')
            col2.number_input('Number of sampling steps', 1, value=config['n_sampling'], key='n_sampling')
            col3.number_input('Number of diffusion samples', 1, value=config['n_diffusion'], key='n_diffusion')
            ops = ['greedy', 'complete']
            st.selectbox('MSA Pairing Strategy', ops, ops.index(config['msa_pairing_strategy']), key='msa_pairing_strategy')
            col1, col2, col3 = st.columns(3)
            clicked1 = col1.form_submit_button('Try', use_container_width=True)
            col2.form_submit_button('Save', use_container_width=True, on_click=save, disabled=active is None)
            clicked2 = col3.form_submit_button('Run', use_container_width=True, type='primary', on_click=save, disabled=active is None)

    if process_ongoing() and (clicked1 or clicked2):
        st.toast('Process busy!', icon="🚨")
    elif clicked1:
        try_run()
    elif clicked2:
        setup_process(active)
    if process_ongoing():
        progress()

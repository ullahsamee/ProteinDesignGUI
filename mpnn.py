from common import *
import configparser
import shutil
import subprocess
from os.path import expandvars
from datetime import datetime


state = st.session_state


@st.dialog('Try with uploading protein structures')
def try_run():
    pdbs = st.file_uploader('Input PDBs for sequence prediction', '.pdb', True)
    if st.button('Confirm', use_container_width=True):
        assert len(pdbs) > 0, 'No PDB uploaded.'
        cache_dir = cache / str(datetime.now())
        t = cache_dir / 'config.yml'
        cfg = get_config()
        sync(cfg['mpnn'])
        put_config(cfg, t)
        for i in pdbs:
            with open(cache_dir / indir / i.name, 'wb') as f:
                f.write(i.getvalue())
        setup_process(t)
        st.rerun()


def get_cmd(wkdir, chains, n_sample, temperature, fixed, invert_fix, top_n):
    if not isinstance(fixed, pd.DataFrame):
        fixed = pd.DataFrame(fixed, dtype=str)
    to_fix = []
    for c in chains:
        temp = set()
        for ind, row in fixed[fixed['chain'] == c].iterrows():
            temp |= set([str(k) for k in range(int(row['min_len']), int(row['max_len'])+1)])
        to_fix.append(' '.join(sorted(temp)))
    to_fix = ','.join(to_fix)
    chains = ' '.join(chains)
    cmd = f"""
    cd {wkdir}
    {exe_parse} --input_path=diffusion --output_path=parsed_pdbs.jsonl
    {exe_assign} --input_path=parsed_pdbs.jsonl --output_path=assigned_pdbs.jsonl --chain_list "{chains}"
    {exe_fix} --input_path=parsed_pdbs.jsonl --output_path=fixed_pdbs.jsonl --chain_list "{chains}" --position_list "{to_fix}" {'--specify_non_fixed' if invert_fix else ''}
    {exe_main} --jsonl_path parsed_pdbs.jsonl --chain_id_jsonl assigned_pdbs.jsonl --fixed_positions_jsonl fixed_pdbs.jsonl \
        --out_folder ./ --num_seq_per_target {n_sample} --sampling_temp "{temperature}" --seed 37
    {exe_post} {wkdir}/seqs {top_n}
    """
    return cmd


def sync(config):
    config['n_sample'] = state['n_sample']
    config['top_n'] = state['top_n']
    config['temperature'] = state['temperature']
    config['invert_fix'] = state['invert_fix']
    config['fixed'] = table_update(config['fixed'], state['fixed'])


def save():
    sync(cfg['mpnn'])
    put_config(cfg, active)
    st.toast('Configuration saved!', icon="✅")


def setup_process(trial):
    state['auto'] = None
    shutil.rmtree(trial / 'seqs', ignore_errors=True)
    files = [*trial.glob(f'{indir}/*.pdb')]
    cmd = get_cmd(trial.parent, extract_chains(files[0]), **config)
    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
    state['process_args'] = len(files), f'Predicting sequences for {cfg["name"]}..', trial.parent, wildcard, 2, trial


if __name__ == '__page__':
    trials = state['trials']
    active = state['current_trial']
    indir = 'diffusion'
    wildcard='seqs/*'

    config = configparser.ConfigParser()
    config.read('settings.conf')
    exe_main = f"python {config['Paths']['ProteinMPNN']}/protein_mpnn_run.py"
    exe_parse = f"python {config['Paths']['ProteinMPNN']}/helper_scripts/parse_multiple_chains.py"
    exe_assign = f"python {config['Paths']['ProteinMPNN']}/helper_scripts/assign_fixed_chains.py"
    exe_fix = f"python {config['Paths']['ProteinMPNN']}/helper_scripts/make_fixed_positions_dict.py"
    exe_post = f"python {Path(__file__).parent}/tools/postprocess_seq.py"
    cache = Path(expandvars(config['Paths']['cache']))

    if state['auto'] is not None:
        setup_process(state['auto'])

    if active is not None:
        active = Path(active)
    cfg = get_config(active)
    config = cfg['mpnn']

    st.title('ProteinMPNN')
    tab1, = st.tabs(['Configure'])
    with tab1:
        with st.form('form'):
            st.number_input('Number of samples', 1, None, config['n_sample'], key='n_sample')
            st.number_input('Top N', 1, None, config['top_n'], key='top_n')
            st.number_input('Temperature', 0., 1., config['temperature'], key='temperature')
            st.subheader('Fixed Positions')
            table_edit(config['fixed'], None, key='fixed')
            st.checkbox('Invert fixed positions', config['invert_fix'], key='invert_fix')
            col1, col2, col3 = st.columns(3)
            clicked1 = col1.form_submit_button('Try', use_container_width=True)
            col2.form_submit_button('Save', use_container_width=True, on_click=save, disabled=active is None)
            clicked2 = col3.form_submit_button('Process', use_container_width=True, type='primary', on_click=save, disabled=active is None)

    if process_ongoing() and (clicked1 or clicked2):
        st.toast('Process busy!', icon="🚨")
    elif clicked1:
        try_run()
    elif clicked2:
        setup_process(active)

    if process_ongoing():
        progress()

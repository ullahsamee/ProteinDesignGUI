from common import *
import configparser
import shutil
import subprocess
from os.path import expandvars
from datetime import datetime
import pickle


state = st.session_state


@st.dialog('Continue with uploading protein structures', width='large')
def try_run():
    pdbs = st.file_uploader('Input PDBs for sequence prediction', '.pdb', True)
    _, col, _ = st.columns(3)
    if col.button('Confirm', use_container_width=True):
        assert len(pdbs) > 0, 'No PDB uploaded.'
        cache_dir = cache / f'{datetime.now()} mpnn'
        input_dir = cache_dir / indir
        input_dir.mkdir(parents=True, exist_ok=True)
        t = cache_dir / 'config.yml'
        cfg = get_config(active)
        sync(cfg['mpnn'])
        cfg['name'] = 'TestJob'
        put_config(cfg, t)
        for i in pdbs:
            with open(input_dir / i.name, 'wb') as f:
                f.write(i.getvalue())
        setup_process(t)
        st.rerun()


def get_cmd(wkdir, chains, n_sample, temperature, fixed, invert_fix, top_n, fix_motif):
    if not isinstance(fixed, pd.DataFrame):
        fixed = pd.DataFrame(fixed, dtype=str)
    if fix_motif:
        cmd = f"""
        cleanup() {{
        echo "Signal received. Killing subprocess..."
        if [ -n "$pid" ] && ps -p $pid > /dev/null; then
            kill $pid
        fi
        echo "Cleanup complete. Exiting."
        exit 1
        }}
        trap cleanup SIGINT SIGTERM
        cd "{wkdir}"
        for pdb in `ls {indir}/*.pdb`; do
            trap cleanup SIGINT SIGTERM
            rm -r {tdir}
            mkdir -p {tdir}
            trb="${{pdb%.pdb}}.trb"
            echo $t
            output=`{exe_pre} $trb`
            chains=`echo "$output" | sed -n '1p'`
            to_fix=`echo "$output" | sed -n '2p'`
            cp $pdb {tdir}
            {exe_parse} --input_path={tdir} --output_path={tdir}/parsed_pdbs.jsonl
            {exe_assign} --input_path={tdir}/parsed_pdbs.jsonl --output_path={tdir}/assigned_pdbs.jsonl --chain_list "$chains"
            {exe_fix} --input_path={tdir}/parsed_pdbs.jsonl --output_path={tdir}/fixed_pdbs.jsonl --chain_list "$chains" --position_list "$to_fix"
            {exe_main} --jsonl_path {tdir}/parsed_pdbs.jsonl --chain_id_jsonl {tdir}/assigned_pdbs.jsonl --fixed_positions_jsonl {tdir}/fixed_pdbs.jsonl \
                --out_folder ./ --num_seq_per_target {n_sample} --sampling_temp "{temperature}" --seed 37 &
            pid=$!
            wait $pid
        done && {exe_post} seqs {top_n} &
        pid=$!
        wait $pid
        """
    else:
        to_fix = []
        for c in chains:
            temp = set()
            for ind, row in fixed[fixed['chain'] == c].iterrows():
                temp |= set([str(k) for k in range(int(row['min_len']), int(row['max_len']) + 1)])
            to_fix.append(' '.join(sorted(temp)))
        to_fix = ','.join(to_fix)
        chains = ' '.join(chains)
        cmd = f"""
        cd "{wkdir}"
        mkdir -p {tdir}
        {exe_parse} --input_path={indir} --output_path={tdir}/parsed_pdbs.jsonl
        {exe_assign} --input_path={tdir}/parsed_pdbs.jsonl --output_path={tdir}/assigned_pdbs.jsonl --chain_list "{chains}"
        {exe_fix} --input_path={tdir}/parsed_pdbs.jsonl --output_path={tdir}/fixed_pdbs.jsonl --chain_list "{chains}" --position_list "{to_fix}" {'--specify_non_fixed' if invert_fix else ''}
        {exe_main} --jsonl_path {tdir}/parsed_pdbs.jsonl --chain_id_jsonl {tdir}/assigned_pdbs.jsonl --fixed_positions_jsonl {tdir}/fixed_pdbs.jsonl \
            --out_folder ./ --num_seq_per_target {n_sample} --sampling_temp "{temperature}" --seed 37
        {exe_post} seqs {top_n}
        """
    return cmd


def sync(config):
    config['n_sample'] = state['n_sample']
    config['fix_motif'] = state['fix_motif']
    config['top_n'] = state['top_n']
    config['temperature'] = state['temperature']
    config['invert_fix'] = state['invert_fix']
    config['fixed'] = table_update(config['fixed'], state['fixed'])


def save():
    sync(cfg['mpnn'])
    put_config(cfg, active)
    st.toast('Configuration saved!', icon="✅")


def setup_process(trial):
    p = trial.parent
    cfg = get_config(trial)
    o = p / 'seqs'
    shutil.rmtree(o, ignore_errors=True)
    files = [*(p / indir).glob(f'*.pdb')]
    cmd = get_cmd(p, extract_chains(files[0]), **cfg['mpnn'])
    assert len(files) > 0, "Nothing to process."
    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
    state['process_args'] = len(files), f'Predicting sequences for {cfg["name"]}..', o, wildcard, 2, trial


if __name__ == '__page__':
    trials = state['trials']
    active = state['current_trial']
    indir = 'diffusion'
    tdir = 'seq_input'
    wildcard = 'seqs/*'

    config = configparser.ConfigParser()
    config.read('settings.conf')
    exe_main = f"python {config['Paths']['ProteinMPNN']}/protein_mpnn_run.py"
    exe_parse = f"python {config['Paths']['ProteinMPNN']}/helper_scripts/parse_multiple_chains.py"
    exe_assign = f"python {config['Paths']['ProteinMPNN']}/helper_scripts/assign_fixed_chains.py"
    exe_fix = f"python {config['Paths']['ProteinMPNN']}/helper_scripts/make_fixed_positions_dict.py"
    exe_post = f"python {Path(__file__).parent.parent}/tools/postprocess_seq.py"
    exe_pre = f"python {Path(__file__).parent.parent}/tools/preprocess_seq.py"
    cache = Path(expandvars(config['Paths']['cache']))

    if state['auto'] is not None:
        setup_process(state['auto'])
        state['auto'] = None

    if active is not None:
        active = Path(active)
    cfg = get_config(active)
    config = cfg['mpnn']

    st.title('ProteinMPNN')
    tab1, = st.tabs(['Configure'])
    with tab1:
        with st.form('form'):
            col1, col2, col3 = st.columns(3)
            col1.number_input('Number of samples', 1, None, config['n_sample'], key='n_sample')
            col2.number_input('Top N', 1, None, config['top_n'], key='top_n')
            col3.number_input('Temperature', 0., 1., config['temperature'], key='temperature')
            st.subheader('Fixed Positions')
            col1, col2 = st.columns([2, 1])
            col1.checkbox('Automatic fixing motifs (will overwrite other options)', config['fix_motif'], key='fix_motif')
            col2.checkbox('Invert fixed positions', config['invert_fix'], key='invert_fix')
            table_edit(config['fixed'], None, key='fixed')
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

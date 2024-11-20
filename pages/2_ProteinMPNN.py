import shutil
import subprocess
from utils import *


def get_cmd(wkdir, chains, n_sample, temperature, fixed, invert_fix):
    if not isinstance(fixed, pd.DataFrame):
        fixed = pd.read_csv(wkdir / fixed, usecols=['chain', 'min_len', 'max_len'])
    to_fix = []
    for c in chains:
        temp = set()
        for ind, row in fixed[fixed['chain'] == c].iterrows():
            temp |= set([str(k) for k in range(row['min_len'], row['max_len']+1)])
        to_fix.append(' '.join(sorted(temp)))
    to_fix = ','.join(to_fix)
    chains = ' '.join(chains)
    cmd = f"""
    cd {wkdir}
    {exe_parse} --input_path=diffusion --output_path=parsed_pdbs.jsonl
    {exe_assign} --input_path=parsed_pdbs.jsonl --output_path=assigned_pdbs.jsonl --chain_list "{chains}"
    {exe_fix} --input_path=parsed_pdbs.jsonl --output_path=fixed_pdbs.jsonl --chain_list "{chains}" --position_list "{to_fix}"{' --specify_non_fixed' if invert_fix else ''}
    {exe_main} --jsonl_path parsed_pdbs.jsonl --chain_id_jsonl assigned_pdbs.jsonl --fixed_positions_jsonl fixed_pdbs.jsonl \
        --out_folder ./ --num_seq_per_target {n_sample} --sampling_temp "{temperature}" --seed 37
    """
    return cmd


if __name__ == '__main__':

    init()
    trials = st.session_state['trials']
    indir = 'diffusion/'

    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe_main = f"python {config['PATH']['ProteinMPNN']}/protein_mpnn_run.py"
        exe_parse = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/parse_multiple_chains.py"
        exe_assign = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/assign_fixed_chains.py"
        exe_fix = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/make_fixed_positions_dict.py"
    st.set_page_config('Protein Design: ProteinMPNN')
    st.title('ProteinMPNN')
    tab1, tab2 = st.tabs(['Configure', 'Batch'])

    with tab1:
        active_trial = st.selectbox("Select a trial", trials)
        if active_trial is not None:
            config = get_config(active_trial)['mpnn']
            with st.form(key='mpnn'):
                n_sample = st.number_input('Number of samples', 1, None, config['n_sample'])
                temperature = st.number_input('Temperature', 0., 1., config['temperature'])
                st.subheader('Fixed Positions')
                table_edit(get_table(active_trial, 'mpnn', 'fixed'), None, 'fixed_1')
                invert_fix = st.checkbox('Invert fixed positions', config['invert_fix'])
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary')
            if clicked1:
                config['n_sample'] = n_sample
                config['temperature'] = temperature
                config['invert_fix'] = invert_fix
                st.session_state['fixed_1'].to_csv(active_trial.parent / config['fixed'], index=False)
                c = get_config(active_trial)
                c['mpnn'] = config
                put_config(c, active_trial)
                st.success('Configuration saved!', icon="✅")
            if clicked2:
                try:
                    if st.session_state['process'] is None:
                        wkdir = active_trial.parent
                        shutil.rmtree(wkdir / 'seq', ignore_errors=True)
                        files = [*wkdir.glob(f'{indir}*.pdb')]
                        chains = extract_chains(files[0])
                        cmd = get_cmd(wkdir, chains, n_sample, temperature, st.session_state['fixed_1'], invert_fix)
                        st.session_state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                        st.session_state['process_args'] = len(files), f'Predicting sequences..', wkdir, 'seq/'
                    else:
                        st.warning('Process busy!')
                    progress()
                    for i in (wkdir / 'seqs').glob('*.fa'):
                        post_process_mpnn(i)
                    st.success('Trial running complete!', icon="✅")
                except Exception as e:
                    st.session_state['process'].terminate()
                    st.write(e)
                finally:
                    if st.session_state['process'] is not None and st.session_state['process'].poll() is not None:
                        st.session_state['process'] = None
    with tab2:
        if st.button('Batch Run', use_container_width=True, type='primary'):
            for i, path in enumerate(trials):
                try:
                    if st.session_state['process'] is None and st.session_state['batch_progress'] is None or st.session_state['batch_progress'] < i:
                        wkdir = path.parent
                        shutil.rmtree(wkdir / 'seq', ignore_errors=True)
                        cfg = get_config(path)
                        files = [*wkdir.glob(f'{indir}*.pdb')]
                        chains = extract_chains(files[0])
                        cmd = get_cmd(wkdir, chains, **cfg['mpnn'])
                        st.session_state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                        st.session_state['process_args'] = len(files), f'Predicting sequences for {cfg["name"]} ({i}/{len(trials)})', wkdir, 'seq/'
                        st.session_state['batch_progress'] = i
                    if st.session_state['batch_progress'] is not None and i == st.session_state['batch_progress']:
                        progress()
                        for j in (wkdir / 'seqs').glob('*.fa'):
                            post_process_mpnn(j)
                except Exception as e:
                    st.session_state['process'].terminate()
                    st.write(e)
                finally:
                    if st.session_state['process'] is not None and st.session_state['process'].poll() is not None:
                        st.session_state['process'] = None
            st.session_state['batch_progress'] = None
            st.success(f'Batch running complete!', icon="✅")


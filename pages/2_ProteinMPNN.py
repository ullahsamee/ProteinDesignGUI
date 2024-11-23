from common import *

state = st.session_state


def get_cmd(wkdir, chains, n_sample, temperature, fixed, invert_fix):
    if not isinstance(fixed, pd.DataFrame):
        fixed = pd.DataFrame(fixed, dtype=str)
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


def sync():
    config['n_sample'] = state['n_sample']
    config['top_n'] = state['top_n']
    config['temperature'] = state['temperature']
    config['invert_fix'] = state['invert_fix']
    config['fixed'] = state['fixed'].to_dict('list')


def save():
    sync()
    c = get_config(active_trial)
    c['mpnn'] = config
    put_config(c, active_trial)
    st.toast('Configuration saved!', icon="✅")


def run():
    sync()
    if state['batch_progress'] >= 0 or state['progress_type'] not in 'mpnn':
        st.toast('Process busy!', icon="🚨")
    else:
        try:
            state['progress_type'] = 'mpnn'
            if state['process'] is None:
                wkdir = active_trial.parent
                shutil.rmtree(wkdir / 'seq', ignore_errors=True)
                files = [*wkdir.glob(f'{indir}*.pdb')]
                cmd = get_cmd(wkdir, extract_chains(files[0]), **config)
                state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                state['process_args'] = len(files), f'Predicting sequences..', wkdir, 'seq/'
            else:
                st.toast('Process busy!', icon="🚨")
            progress(placeholder)
            for i in (state['process_args'][2] / 'seqs').glob('*.fa'):
                post_process_mpnn(i, config['top_n'])
            signify_complete(placeholder)
        except Exception as e:
            state['process'].terminate()
            st.write(e)
        finally:
            state['progress_type'] = ''
            state['process'] = None


def batch():
    if st.button('Batch Run', use_container_width=True, type='primary'):
        if process_ongoing() and state['batch_progress'] < 0 or state['progress_type'] not in 'mpnn':
            st.warning('Process busy!', icon="🚨")
        else:
            state['progress_type'] = 'mpnn'
            for i, path in enumerate(trials):
                try:
                    if process_ongoing() and state['batch_progress'] < i:
                        wkdir = path.parent
                        shutil.rmtree(wkdir / 'seq', ignore_errors=True)
                        cfg = get_config(path)
                        files = [*wkdir.glob(f'{indir}*.pdb')]
                        cmd = get_cmd(wkdir, extract_chains(files[0]), **cfg['mpnn'])
                        state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                        state['process_args'] = len(files), f'Predicting sequences for {cfg["name"]} ({i}/{len(trials)})', wkdir, 'seq/'
                        state['batch_progress'] = i
                    if i == state['batch_progress']:
                        progress(side_placeholder)
                        for j in (state['process_args'][2] / 'seqs').glob('*.fa'):
                            post_process_mpnn(j, get_config(path)['mpnn']['top_n'])
                except Exception as e:
                    state['process'].terminate()
                    st.write(e)
                finally:
                    if not process_ongoing():
                        state['process'] = None
            signify_batch_complete(side_placeholder)
            state['progress_type'] = ''
            state['batch_progress'] = -1


if __name__ == '__main__':
    st.set_page_config('Protein Design: ProteinMPNN')

    trials = state['trials']
    indir = 'diffusion/'
    state['current_batch'] = batch

    side_placeholder = init()

    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe_main = f"python {config['PATH']['ProteinMPNN']}/protein_mpnn_run.py"
        exe_parse = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/parse_multiple_chains.py"
        exe_assign = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/assign_fixed_chains.py"
        exe_fix = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/make_fixed_positions_dict.py"
    st.title('ProteinMPNN')
    tab1, = st.tabs(['Configure'])

    with tab1:
        active_trial = st.selectbox("Select a trial", trials)
        if active_trial is not None:
            config = get_config(active_trial)['mpnn']
            with st.form('mpnn_form'):
                st.number_input('Number of samples', 1, None, config['n_sample'], key='n_sample')
                st.number_input('Top N', 1, None, config['top_n'], key='top_n')
                st.number_input('Temperature', 0., 1., config['temperature'], key='temperature')
                st.subheader('Fixed Positions')
                table_edit(config['fixed'], None, key='fixed')
                st.checkbox('Invert fixed positions', config['invert_fix'], key='invert_fix')
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True, on_click=save)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary', on_click=run)
    placeholder = st.empty()
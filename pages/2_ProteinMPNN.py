from common import *
import configparser


state = st.session_state


def get_cmd(wkdir, chains, n_sample, temperature, fixed, invert_fix, **kwargs):
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
    """
    return cmd


def sync():
    config['n_sample'] = state['n_sample']
    config['top_n'] = state['top_n']
    config['temperature'] = state['temperature']
    config['invert_fix'] = state['invert_fix']
    config['fixed'] = table_update(config['fixed'], state['fixed'])


def save():
    sync()
    c = get_config(active_trial)
    c['mpnn'] = config
    put_config(c, active_trial)
    st.toast('Configuration saved!', icon="✅")


def batch():
    if process_ongoing() and not batch_ongoing():
        st.warning('Process busy!', icon="🚨")
    else:
        state['automated'] = False
        for i, path in enumerate(trials):
            try:
                if not process_ongoing() and (state['batch_progress'] < i or not batch_ongoing()):
                    wkdir = path.parent
                    shutil.rmtree(wkdir / 'seqs', ignore_errors=True)
                    cfg = get_config(path)
                    files = [*wkdir.glob(f'{indir}*.pdb')]
                    cmd = get_cmd(wkdir, extract_chains(files[0]), **cfg['mpnn'])
                    state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                    state['process_args'] = len(files), f'Predicting sequences for {cfg["name"]} ({i}/{len(trials)})', wkdir, wildcard
                    state['batch_progress'] = i
                if i == state['batch_progress']:
                    progress(side_placeholder)
                    for j in (state['process_args'][2] / 'seqs').glob('*.fa'):
                        post_process_mpnn(j, get_config(path)['mpnn']['top_n'])
            except Exception as e:
                st.write(e)
            finally:
                reset_proc()
        signify_batch_complete(side_placeholder)
        state['batch_progress'] = np.inf


if __name__ == '__main__':
    st.set_page_config('Protein Design: ProteinMPNN')
    init()

    trials = state['trials']
    indir = 'diffusion/'
    wildcard='seqs/*'
    if state['current_page'] != 2:
        abort_proc()
    state['current_page'] = 2

    side_placeholder, batch_clicked = navigation()
    post_batch = False

    config = configparser.ConfigParser()
    config.read('settings.conf')
    exe_main = f"python {config['PATH']['ProteinMPNN']}/protein_mpnn_run.py"
    exe_parse = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/parse_multiple_chains.py"
    exe_assign = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/assign_fixed_chains.py"
    exe_fix = f"python {config['PATH']['ProteinMPNN']}/helper_scripts/make_fixed_positions_dict.py"
    st.title('ProteinMPNN')
    tab1, = st.tabs(['Configure'])

    with tab1:
        ops = 0
        if trials and state['current_trial'] is not None:
            ops = trials.index(state['current_trial'])
        active_trial = state['current_trial'] = st.selectbox("Select a trial", trials, ops)
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
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary')
            if clicked1 and batch_ongoing() or batch_clicked or state['automated']:
                batch()
                post_batch = True
            elif clicked2:
                sync()
                if batch_ongoing():
                    st.toast('Process busy!', icon="🚨")
                    batch()
                    post_batch = True
                else:
                    try:
                        if not process_ongoing():
                            wkdir = active_trial.parent
                            shutil.rmtree(wkdir / 'seqs', ignore_errors=True)
                            files = [*wkdir.glob(f'{indir}*.pdb')]
                            cmd = get_cmd(wkdir, extract_chains(files[0]), **config)
                            state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                            state['process_args'] = len(files), f'Predicting sequences..', wkdir, wildcard
                        else:
                            st.toast('Process busy!', icon="🚨")
                        progress(st)
                        for i in (state['process_args'][2] / 'seqs').glob('*.fa'):
                            post_process_mpnn(i, config['top_n'])
                        signify_complete(st)
                    except Exception as e:
                        st.write(e)
                    finally:
                        reset_proc()

    if post_batch:
        if state['proceed2']:
            state['automated'] = True
            st.switch_page('pages/3_Local_ColabFold.py')

from common import *

state = st.session_state


@st.fragment
def show(pdb_list):
    st.header('Results')
    choice = st.selectbox('Select a result', pdb_list)
    if choice is not None:
        with open(choice, 'r') as f:
            pdb = f.read()
        st_molstar_content(pdb, 'pdb', height='500px')


def get_cmd(wkdir, n_recycle, n_mod, use_amber, use_template):
    cmd = f"""
    cd {wkdir}
    {exe} seqs {prefix} --num-models {n_mod} --num-recycle {n_recycle}
    """
    if use_amber:
        cmd += ' --amber'
    if use_template:
        cmd += ' --templates'
    return cmd


def sync():
    config['use_amber'] = state['use_amber']
    config['use_template'] = state['use_template']
    config['n_mod'] = state['n_mod']
    config['n_recycle'] = state['n_recycle']


def save():
    sync()
    c = get_config(active_trial)
    c['fold'] = config
    put_config(c, active_trial)
    st.toast('Configuration saved!', icon="✅")


def run():
    sync()
    if state['batch_progress'] >= 0 or state['progress_type'] not in 'fold':
        st.toast('Process busy!', icon="🚨")
    else:
        try:
            state['progress_type'] = 'fold'
            if state['process'] is None:
                wkdir = active_trial.parent
                shutil.rmtree(wkdir / prefix, ignore_errors=True)
                cmd = get_cmd(wkdir, **config)
                state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                nfiles = len([*wkdir.glob('seqs/*.fasta')])
                state['process_args'] = config['n_mod'] * nfiles, 'Running prediction for single trial..', wkdir, prefix
            else:
                st.toast('Process busy!', icon="🚨")
            progress(placeholder)
            signify_complete(placeholder)
        except Exception as e:
            state['process'].terminate()
            st.write(e)
        finally:
            state['progress_type'] = ''
            state['process'] = None


def batch():
    if st.button('Batch Run', use_container_width=True, type='primary'):
        if process_ongoing() and state['batch_progress'] < 0 or state['progress_type'] not in 'fold':
            st.toast('Process busy!', icon="🚨")
        else:
            state['progress_type'] = 'fold'
            for i, path in enumerate(trials):
                try:
                    if process_ongoing() and state['batch_progress'] < i:
                        wkdir = path.parent
                        shutil.rmtree(wkdir / prefix, ignore_errors=True)
                        cfg = get_config(path)['fold']
                        cmd = get_cmd(wkdir, **cfg)
                        nfiles = len([*wkdir.glob('seqs/*.fasta')])
                        state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                        state['process_args'] = cfg['n_mod'] * nfiles, f'Running prediction.. ({0}/{len(trials)})', wkdir, prefix
                        state['batch_progress'] = i
                    if i == state['batch_progress']:
                        progress(side_placeholder)
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
    st.set_page_config('Protein Design: Local ColabFold')

    state = state
    trials = state['trials']
    prefix = 'fold/'
    state['current_batch'] = batch

    side_placeholder = init()

    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"{config['PATH']['ColabFold']}/colabfold-conda/bin/colabfold_batch"
    st.title('Local ColabFold')
    tab1, tab2 = st.tabs(['Configure', 'Visualize'])

    with tab1:
        active_trial = st.selectbox("Select a trial", trials)
        if active_trial is not None:
            config = get_config(active_trial)['fold']
            with st.form(key='fold'):
                st.checkbox('Use amber', config['use_amber'], key='use_amber')
                st.checkbox('Use template', config['use_template'], key='use_template')
                st.selectbox('Number of models', [1, 2, 3, 4, 5], config['n_mod'] - 1, key='n_mod')
                st.number_input('Number of recycle', 1, value=config['n_recycle'], key='n_recycle')
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True, on_click=save)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary', on_click=run)
    with tab2:
        if active_trial is not None:
            results = sorted(active_trial.parent.rglob(f'{prefix}*.pdb'))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')
    placeholder = st.empty()
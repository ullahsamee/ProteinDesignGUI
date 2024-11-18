import subprocess
from utils import *
import shutil


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


if __name__ == '__main__':

    init()
    trials = st.session_state['trials']
    prefix = 'fold/'

    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"{config['PATH']['ColabFold']}/colabfold-conda/bin/colabfold_batch"
    st.set_page_config('Protein Design: Local ColabFold')
    st.title('Local ColabFold')
    tab1, tab2, tab3 = st.tabs(['Configure', 'Visualize', 'Batch'])

    with tab1:
        active_trial = st.selectbox("Select a trial", trials)
        if active_trial is not None:
            config = get_config(active_trial)['fold']
            with st.form(key='fold'):
                use_amber = st.checkbox('Use amber', config['use_amber'])
                use_template = st.checkbox('Use template', config['use_template'])
                n_mod = st.selectbox('Number of models', [1, 2, 3, 4, 5], config['n_mod'] - 1)
                n_recycle = st.number_input('Number of recycle', 1, value=config['n_recycle'])
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary')
            if clicked1:
                config['use_amber'] = use_amber
                config['use_template'] = use_template
                config['n_mod'] = n_mod
                config['n_recycle'] = n_recycle
                c = get_config(active_trial)
                c['fold'] = config
                put_config(c, active_trial)
                st.success('Configuration saved!', icon="✅")
            if clicked2:
                try:
                    if st.session_state['process'] is None:
                        wkdir = active_trial.parent
                        shutil.rmtree(wkdir / prefix, ignore_errors=True)
                        cmd = get_cmd(wkdir, n_recycle, n_mod, use_amber, use_template)
                        st.session_state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                        nfiles = len([*wkdir.glob('seqs/*.fasta')])
                        st.session_state['process_args'] = n_mod * nfiles, 'Running prediction for single trial..', wkdir, prefix
                    progress()
                    st.success('Trial running complete!', icon="✅")
                except Exception as e:
                    st.session_state['process'].terminate()
                    st.write(e)
                finally:
                    if st.session_state['process'] is not None and st.session_state['process'].poll() is not None:
                        st.session_state['process'] = None

    with tab2:
        if active_trial is not None:
            results = sorted(active_trial.parent.rglob(f'{prefix}*.pdb'))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')

    with tab3:
        if st.button('Batch Run', use_container_width=True, type='primary'):
            for i, path in enumerate(trials):
                try:
                    if st.session_state['process'] is None:
                        wkdir = path.parent
                        shutil.rmtree(wkdir / prefix, ignore_errors=True)
                        cfg = get_config(path)['fold']
                        cmd = get_cmd(wkdir, **cfg)
                        nfiles = len([*wkdir.glob('seqs/*.fasta')])
                        st.session_state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                        st.session_state['process_args'] = cfg['n_mod'] * nfiles, f'Running prediction.. ({0}/{len(trials)})', wkdir, prefix
                        st.session_state['batch_progress'] = i
                    if i == st.session_state['batch_progress']:
                        progress()
                except Exception as e:
                    st.session_state['process'].terminate()
                    st.write(e)
                finally:
                    if st.session_state['process'] is not None and st.session_state['process'].poll() is not None:
                        st.session_state['process'] = None
                    st.session_state['batch_progress'] = None
            st.success(f'Batch running complete!', icon="✅")


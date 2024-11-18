import subprocess
from utils import *


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
    {exe} seq {prefix} --num-models {n_mod} --num-recycle {n_recycle}
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

    with (tab1):
        active_trial = st.selectbox("Select a trial", trials)
        if active_trial is not None:
            config = get_config(active_trial)['fold']
            with st.form(key='fold'):
                use_amber = st.checkbox('Use amber', config['amber'])
                use_template = st.checkbox('Use template', config['template'])
                n_mod = st.selectbox('Number of models', [1, 2, 3, 4, 5], config['n_mod'] - 1)
                n_recycle = st.number_input('Number of recycle', 1, value=3)
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary')
            if clicked1:
                config['use_amber'] = use_amber
                config['use_template'] = use_template
                config['n_mod'] = n_mod
                c = get_config(active_trial)
                c['fold'] = config
                put_config(c, active_trial)
                st.success('Configuration saved!', icon="✅")
            if clicked2:
                wkdir = active_trial.parent
                cmd = get_cmd(wkdir, n_recycle, n_mod, use_amber, use_template)
                process = subprocess.Popen(['/bin/bash', '-c', cmd])
                progress(process, n_mod, 'Running prediction for single trial..',
                         wkdir.glob(f'{prefix}*.pdb'))
                st.success('Trial running complete!', icon="✅")

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
                    wkdir = path.parent
                    cfg = get_config(path)['fold']
                    cmd = get_cmd(wkdir, **cfg)
                    process = subprocess.Popen(['/bin/bash', '-c', cmd])
                    progress(process, cfg['n_mod'], f'Running prediction.. ({0}/{len(trials)})',
                             wkdir.glob(f'{prefix}*.pdb'))
                except Exception as e:
                    st.write(e)
            st.success(f'Batch running complete!', icon="✅")


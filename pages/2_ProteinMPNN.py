import subprocess
from utils import *


def get_cmd(wkdir, pdb, n_sample, temperature):
    cmd = f"""
    {exe} --pdb_path {pdb} --out_folder {wkdir} --num_seq_per_target {n_sample} --sampling_temp "{temperature}"
    """
    return cmd


if __name__ == '__main__':

    init()
    trials = st.session_state['trials']
    prefix = 'diffusion/design'

    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"python {config['PATH']['ProteinMPNN']}/protein_mpnn_run.py"
    st.set_page_config('Protein Design: ProteinMPNN')
    st.title('ProteinMPNN')
    tab1, tab2 = st.tabs(['Configure', 'Batch'])

    with tab1:
        active_trial = st.selectbox("Select a trial", trials)
        if active_trial is not None:
            config = get_config(active_trial)['mpnn']
            with st.form(key='mpnn'):
                n_sample = st.number_input('seq/chain', 1, None, config['n_sample'])
                temperature = st.number_input('temperature', 0., 1., 0.1)
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary')
            if clicked1:
                config['n_sample'] = n_sample
                config['temperature'] = temperature
                c = get_config(active_trial)
                c['mpnn'] = config
                put_config(c, active_trial)
                st.success('Configuration saved!', icon="✅")
            if clicked2:
                wkdir = active_trial.parent
                files = [*wkdir.glob(f'{prefix}*.pdb')]
                msg = f'Predicting sequence..'
                bar = st.progress(0, msg)
                for i, pdb in enumerate(files):
                    cmd = get_cmd(wkdir, pdb, n_sample, temperature)
                    subprocess.run(['/bin/bash', '-c', cmd])
                    bar.progress((i + 1) / len(files), msg)
                for i in (wkdir / 'seq').glob('*.fa'):
                    post_process_mpnn(i)
                bar.empty()
                st.success('Trial running complete!', icon="✅")

    with tab2:
        if st.button('Batch Run', use_container_width=True, type='primary'):
            for i, path in enumerate(trials):
                try:
                    wkdir = path.parent
                    cfg = get_config(path)['mpnn']
                    files = [*wkdir.glob(f'{prefix}*.pdb')]
                    msg = f'Predicting sequence.. ({i + 1}/{len(trials)})'
                    bar = st.progress(0, msg)
                    for j, pdb in enumerate(files):
                        cmd = get_cmd(wkdir, pdb, **cfg)
                        subprocess.run(['/bin/bash', '-c', cmd])
                        bar.progress((j + 1) / len(files), msg)
                    for j in (wkdir / 'seq').glob('*.fa'):
                        post_process_mpnn(j)
                    bar.empty()
                except Exception as e:
                    st.write(e)
            st.success(f'Batch running complete!', icon="✅")


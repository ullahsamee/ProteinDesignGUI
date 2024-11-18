import subprocess
import shutil
from utils import *


@st.fragment
def table_edit(data, key):
    table = st.data_editor(
        data, column_order=None, num_rows='dynamic', use_container_width=True, key=f'{key}.data',
        column_config={
            'chain': st.column_config.SelectboxColumn('Chain',
                                                      options=[*(chr(i) for i in range(ord('A'), ord('Z') + 1))],
                                                      required=False),
            'min_len': st.column_config.NumberColumn('Min', required=True, step=1, min_value=0),
            'max_len': st.column_config.NumberColumn('Max', required=True, step=1, min_value=0),
        }
    )
    st.session_state[key] = table
    st.markdown(f'The specified sequence map: `{convert_selection(st.session_state[key])}`')


def get_cmd(wkdir, contig, inpaint, n_design, n_timestamp, protein):
    if not isinstance(contig, pd.DataFrame):
        contig = pd.read_csv(wkdir / contig)
    if not isinstance(inpaint, pd.DataFrame):
        inpaint = pd.read_csv(wkdir / inpaint)
    cmd = f"""
    cd {wkdir}
    {exe} inference.output_prefix={prefix} inference.input_pdb={protein} \
    'contigmap.contigs={convert_selection(contig)}' inference.num_designs={n_design} diffuser.T={n_timestamp}"""
    temp = convert_selection(inpaint)
    if len(temp) > 2:
        cmd += f" 'contigmap.inpaint_seq={temp}'"
    return cmd


if __name__ == '__main__':

    init()
    trials = st.session_state['trials']
    outdir = 'diffusion'
    prefix = outdir + '/design'

    with open('config.yml') as f:
        config = yaml.safe_load(f)
        exe = f"python {config['PATH']['RFdiffusion']}/scripts/run_inference.py"
    st.set_page_config('Protein Design: Motif Scaffolding')
    st.title('Motif Scaffolding')
    tab1, tab2, tab3 = st.tabs(['Configure', 'Visualize', 'Batch'])

    with tab1:
        active_trial = st.selectbox("Select a trial", trials)
        if active_trial is not None:
            config = get_config(active_trial)['diffusion']
            with st.form(key='scf'):
                col1, col2 = st.columns(2)
                n_design = col1.number_input('Number of designs', 1, value=config['n_design'], step=10, format='%d')
                n_timestamp = col2.number_input('Number of timestamps', 15, value=config['n_timestamp'], step=10, format='%d')
                st.subheader('Contigs Setting')
                table_edit(get_table(active_trial, 'contig'), 'contig_1')
                st.subheader('Inpaint Setting')
                table_edit(get_table(active_trial, 'inpaint'), 'inpaint_1')
                col1, col2 = st.columns(2)
                clicked1 = col1.form_submit_button('Save', use_container_width=True)
                clicked2 = col2.form_submit_button('Run', use_container_width=True, type='primary')
            if clicked1:
                config['n_design'] = n_design
                config['n_timestamp'] = n_timestamp
                st.session_state['contig_1'].to_csv(active_trial.parent / config['contig'], index=False)
                st.session_state['inpaint_1'].to_csv(active_trial.parent / config['inpaint'], index=False)
                c = get_config(active_trial)
                c['diffusion'] = config
                put_config(c, active_trial)
                st.success('Configuration saved!', icon="✅")
            if clicked2 and st.session_state['batch_progress'] is None:
                try:
                    if st.session_state['process'] is None:
                        wkdir = active_trial.parent
                        shutil.rmtree(wkdir / outdir, ignore_errors=True)
                        cmd = get_cmd(wkdir, st.session_state['contig_1'], st.session_state['inpaint_1'],
                                      n_design, n_timestamp, config['protein'])
                        st.session_state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                        st.session_state['process_args'] = n_design, 'Running inference for single trial..', wkdir, prefix
                    else:
                        st.warning('Process busy!')
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
            results = sorted(active_trial.parent.glob(f'{prefix}*.pdb'))
            if len(results) > 0:
                visual(results)
            else:
                st.warning('No results found.')

    with tab3:
        if st.button('Batch Run', use_container_width=True, type='primary'):
            if st.session_state['process'] is not None:
                st.warning('Process busy!')
            for i, path in enumerate(trials):
                try:
                    if st.session_state['process'] is None and st.session_state['batch_progress'] is None or st.session_state['batch_progress'] < i:
                        wkdir = path.parent
                        shutil.rmtree(wkdir / outdir, ignore_errors=True)
                        cfg = get_config(path)
                        cmd = get_cmd(wkdir, **cfg['diffusion'])
                        st.session_state['process'] = subprocess.Popen(['/bin/bash', '-c', cmd])
                        st.session_state['process_args'] = cfg['diffusion']['n_design'], f'Running inference for {cfg["name"]} ({i}/{len(trials)})', wkdir, prefix
                        st.session_state['batch_progress'] = i
                    if st.session_state['batch_progress'] is not None and i == st.session_state['batch_progress']:
                        progress()
                except Exception as e:
                    st.session_state['process'].terminate()
                    st.write(e)
                finally:
                    if st.session_state['process'] is not None and st.session_state['process'].poll() is not None:
                        st.session_state['process'] = None
            st.session_state['batch_progress'] = None
            st.success(f'Batch running complete!', icon="✅")
